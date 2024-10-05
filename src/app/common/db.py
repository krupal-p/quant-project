import threading

import pandas as pd
import polars as pl
from app import config, log
from sqlalchemy import Engine, create_engine, text


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
    insert_statement: str,
    data,
    table_name_with_schema: str,
    *,
    truncate: bool,
) -> None:
    with get_db_conn().begin() as conn:
        if truncate:
            conn.execute(text(f"TRUNCATE TABLE {table_name_with_schema}"))
        conn.execute(text(insert_statement), data)
