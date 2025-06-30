import logging
import threading
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from typing import Any, Protocol

from app import config
from sqlalchemy import (
    Engine,
    Executable,
    MappingResult,
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
        stmt: str | Executable,
        params: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    ) -> MappingResult:
        """
        Execute a raw SQL statement.
        """
        if isinstance(stmt, str):
            stmt = text(stmt)
        try:
            with self._engine.begin() as conn:
                return conn.execute(
                    stmt,
                    params,
                ).mappings()
        except SQLAlchemyError:
            logger.exception("Error executing statement: %s", stmt)
            raise

    def fetch_one(
        self,
        stmt: str | Executable,
        params: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    ) -> Any:
        """
        Execute and fetch one row.
        """
        result = self.execute(stmt, params)
        return result.fetchone()

    def fetch_all(
        self,
        stmt: str | Executable,
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
            with self._engine.begin() as conn:
                return conn.execute(stmt, values)
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
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
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
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
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
        sql: str | Executable,
        params: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    ) -> list[Any] | None:
        """
        Shortcut for fetch_all on raw SQL.
        """
        if isinstance(sql, str):
            sql = text(sql)
        with self._engine.begin() as conn:
            result = conn.execute(sql, params or {})
            # Only fetch rows if the statement returns rows
            if result.returns_rows:
                return [dict(row) for row in result.mappings().fetchall()]
            return None

    def merge(
        self,
        source_table: str,
        target_table: str,
        keys: list[str],
        update_columns: list[str] | None = None,
        schema: str | None = None,
    ) -> None:
        """
        Merge all rows from source_table into target_table.

        Uses SQL MERGE (e.g., PostgreSQL 15+, SQL Server).

        :param source_table: name of the staging/source table
        :param target_table: name of the destination table
        :param keys: list of key columns to match on
        :param update_columns: list of columns to update (defaults to all except keys)
        :param schema: optional schema name
        """
        tgt = self.get_table(target_table, schema)

        all_cols = [c.name for c in tgt.columns]
        upd_cols = update_columns or [c for c in all_cols if c not in keys]

        src_full = f"{(schema + '.') if schema else ''}{source_table}"
        tgt_full = f"{(schema + '.') if schema else ''}{target_table}"

        on_clause = " AND ".join([f"t.{k} = s.{k}" for k in keys])
        insert_cols = ", ".join(all_cols)
        insert_vals = ", ".join([f"s.{c}" for c in all_cols])
        update_set = ", ".join([f"{c} = s.{c}" for c in upd_cols])

        if self._engine.name == "postgresql":
            merge_sql = f"""
                MERGE INTO {tgt_full} AS t
                USING {src_full} AS s
                ON {on_clause}
                WHEN MATCHED THEN
                UPDATE SET {update_set}
                WHEN NOT MATCHED THEN
                INSERT ({insert_cols}) VALUES ({insert_vals});
                """
            self.raw_query(merge_sql)
        elif self._engine.name == "sqlite":
            # SQLite: emulate merge using INSERT ... ON CONFLICT DO UPDATE
            # Assumes source_table contains the rows to merge
            source_rows = self.select(source_table)
            for row in source_rows:
                insert_dict = {col: row[col] for col in insert_cols.split(", ")}
                if update_columns is None:
                    update_cols = [col for col in insert_dict if col not in keys]
                else:
                    update_cols = update_columns
                update_assignments = ", ".join(
                    [f"{col}=excluded.{col}" for col in update_cols],
                )
                columns_str = ", ".join(insert_dict.keys())
                placeholders = ", ".join([f":{col}" for col in insert_dict])
                sql = (
                    f"INSERT INTO {target_table} ({columns_str}) VALUES ({placeholders}) "
                    f"ON CONFLICT({', '.join(keys)}) DO UPDATE SET {update_assignments}"
                )
                self.execute(sql, insert_dict)
        else:
            raise NotImplementedError(
                "Merge is only implemented for PostgreSQL and SQLite",
            )
