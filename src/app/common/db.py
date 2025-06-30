import logging
import threading
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from typing import Any, Protocol

from app import config
from sqlalchemy import (
    Engine,
    MetaData,
    Table,
    create_engine,
    delete,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection, Result
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DBEngine(Protocol):
    def get_engine(self) -> Engine: ...

    def get_metadata(self) -> MetaData: ...


class SQLiteEngine:
    # Singleton instance of the SQLiteEngine
    _instance = None
    _sqlite: Engine
    _metadata: MetaData
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            # Ensure thread safety when creating the singleton instance
            with cls._lock:
                # Check again in case another thread created the instance
                if cls._instance is None:
                    # Create the singleton instance and the SQLAlchemy engine
                    cls._instance = super().__new__(cls)
                    cls._sqlite: Engine = create_engine("sqlite:///:memory:")
                    cls._metadata = MetaData()
        return cls._instance

    def get_engine(self) -> Engine:
        return self._sqlite

    def get_metadata(self) -> MetaData:
        return self._metadata


class PgEngine:
    # Singleton instance of the PgEngine
    _instance = None
    _pg: Engine
    _metadata: MetaData
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            # Ensure thread safety when creating the singleton instance
            with cls._lock:
                # Check again in case another thread created the instance
                if cls._instance is None:
                    # Create the singleton instance and the SQLAlchemy engine
                    cls._instance = super().__new__(cls)
                    cls._pg: Engine = create_engine(
                        config.POSTGRES_URL,
                    )
                    cls._metadata = MetaData()
        return cls._instance

    def get_engine(self) -> Engine:
        """
        Returns the SQLAlchemy engine for PostgreSQL.

        This method provides access to the SQLAlchemy engine used for database operations.

        Returns:
            Engine: The SQLAlchemy engine for PostgreSQL.
        """
        return self._pg

    def get_metadata(self) -> MetaData:
        """
        Returns the metadata object associated with the PostgresEngine.

        This metadata object is used to reflect database schema and manage table definitions.

        Returns:
            MetaData: The SQLAlchemy metadata object.
        """
        return self._metadata


def get_db_engine(db_type: str) -> Engine:
    if db_type == "postgres":
        return PgEngine().get_engine()
    if db_type == "sqlite":
        return SQLiteEngine().get_engine()
    msg = f"{db_type} is not a valid database type. Supported types are: 'postgres', 'sqlite'."
    raise ValueError(msg)


def get_metadata(db_type: str) -> MetaData:
    if db_type == "postgres":
        return PgEngine().get_metadata()
    if db_type == "sqlite":
        return SQLiteEngine().get_metadata()
    msg = f"{db_type} is not a valid database type. Supported types are: 'postgres', 'sqlite'."
    raise ValueError(msg)


class DB:
    def __init__(self, db_engine: DBEngine):
        self._engine: Engine = db_engine.get_engine()
        self.metadata: MetaData = db_engine.get_metadata()
        self._tables: dict[str, Table] = {}

    def reflect_table(self, table_name: str, schema: str | None = None) -> Table:
        """
        Reflect and cache a table.
        """
        key = f"{schema}.{table_name}" if schema else table_name
        if key not in self._tables:
            table = Table(
                table_name,
                self.metadata,
                autoload_with=self._engine,
                schema=schema,
            )
            self._tables[key] = table
        return self._tables[key]

    def get_table(self, table_name: str, schema: str | None = None) -> Table:
        return self.reflect_table(table_name, schema)

    def execute(
        self,
        stmt: str,
        params: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    ) -> Result:
        """
        Execute a raw SQL statement.
        """
        try:
            with self._engine.begin() as conn:
                return conn.execute(
                    text(stmt),
                    params,
                )
        except SQLAlchemyError:
            logger.exception("Error executing statement: %s", stmt)
            raise

    def fetch_one(
        self,
        stmt: Any,
        params: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    ) -> Any:
        """
        Execute and fetch one row.
        """
        result = self.execute(stmt, params)
        return result.fetchone()

    def fetch_all(
        self,
        stmt: Any,
        params: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    ) -> list[Any]:
        """
        Execute and fetch all rows.
        """
        result = self.execute(stmt, params)
        return list(result.fetchall())

    def select(
        self,
        table_name: str,
        where: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        order_by: list[Any] | None = None,
        limit: int | None = None,
        schema: str | None = None,
    ) -> list[Any]:
        """
        Perform a SELECT query.
        """
        table = self.get_table(table_name, schema)
        cols = [table.c[col] for col in columns] if columns else [table]
        stmt = select(*cols)
        if where:
            for col, val in where.items():
                stmt = stmt.where(table.c[col] == val)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if limit:
            stmt = stmt.limit(limit)
        return self.fetch_all(stmt)

    def insert(
        self,
        table_name: str,
        values: dict[str, Any] | list[dict[str, Any]],
        schema: str | None = None,
    ) -> Result:
        """
        Perform an INSERT.
        """
        table = self.get_table(table_name, schema)
        stmt = insert(table)
        try:
            with self._engine.connect() as conn:
                result = conn.execute(stmt, values)
                conn.commit()
                return result
        except SQLAlchemyError:
            logger.exception("Error inserting into %s", table_name)
            raise

    def update(
        self,
        table_name: str,
        where: dict[str, Any],
        values: dict[str, Any],
        schema: str | None = None,
    ) -> int:
        """
        Perform an UPDATE, returns number of rows updated.
        """
        table = self.get_table(table_name, schema)
        stmt = (
            update(table)
            .where(*[table.c[col] == val for col, val in where.items()])
            .values(**values)
        )
        with self._engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            return result.rowcount

    def delete(
        self,
        table_name: str,
        where: dict[str, Any],
        schema: str | None = None,
    ) -> int:
        """
        Perform a DELETE, returns number of rows deleted.
        """
        table = self.get_table(table_name, schema)
        stmt = delete(table).where(
            *[table.c[col] == val for col, val in where.items()],
        )
        with self._engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            return result.rowcount

    @contextmanager
    def transaction(self) -> Generator[Connection, None, None]:
        """
        Provide a transactional connection.
        Usage:
            with db.transaction() as conn:
                conn.execute(...)
        """
        conn = self._engine.connect()
        trans = conn.begin()
        try:
            yield conn
            trans.commit()
        except:
            trans.rollback()
            raise
        finally:
            conn.close()

    def raw_query(
        self,
        sql: str,
        params: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    ) -> list[Any]:
        """
        Shortcut for fetch_all on raw SQL.
        """
        return self.fetch_all(text(sql), params)
