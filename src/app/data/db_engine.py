import threading

import pandas as pd
import polars as pl
from sqlalchemy import Engine, create_engine

from app import get_config, get_logger


class DBEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
                cls.log = get_logger()
                cls.log.info("Creating DBEngine instance")
                cls.conn: Engine = create_engine(get_config().SQLSERVER_URL)
        return cls._instance


def get_db_conn() -> Engine:
    return DBEngine().conn


def read_sql(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_db_conn(), dtype_backend="pyarrow")


def read_sql_polar(query: str) -> pl.DataFrame:
    return pl.read_database(query, get_db_conn())
