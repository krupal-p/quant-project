import threading
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
from app import config, log
from sqlalchemy import Engine, MetaData, Table, create_engine, text

metadata_obj = MetaData()


class DBEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
                log.info("Creating DBEngine instance")
                cls.conn: Engine = create_engine(config.SQLSERVER_URL)
        return cls._instance


def get_db_conn() -> Engine:
    return DBEngine().conn


def read_sql(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_db_conn(), dtype_backend="pyarrow")


def read_sql_polar(query: str) -> pl.DataFrame:
    return pl.read_database(query, get_db_conn())


def insert_into_table(
    data: list[dict[str, Any]],
    table_name: str,
    schema: str,
    *,
    truncate: bool,
):
    table = Table(
        table_name,
        metadata_obj,
        schema=schema,
        autoload_with=get_db_conn(),
    )
    with get_db_conn().begin() as conn:
        if truncate:
            conn.execute(text(f"TRUNCATE TABLE {schema}.{table_name}"))
        conn.execute(table.insert(), data)


def execute_sql_statement_from_file(file_name: str) -> None:
    """
    Execute a SQL statement from a file in the sql directory without the sql extension.
    """
    file_path = Path(__file__).parent.parent / "sql" / (file_name + ".sql")

    with Path(file_path).open() as file:
        sql_statement = file.read()
        with get_db_conn().begin() as conn:
            conn.execute(text(sql_statement))
