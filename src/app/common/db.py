import threading
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
from app import config, log
from sqlalchemy import Engine, MetaData, Table, create_engine, text


class DBEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
                log.info("Creating DBEngine instance")
                cls.conn: Engine = create_engine(config.SQLSERVER_URL)
                cls.metadata = MetaData()
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
        DBEngine().metadata,
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


def execute_sql_statement(sql_statement: str) -> None:
    with get_db_conn().begin() as conn:
        conn.execute(text(sql_statement))


def get_table(table_name: str, schema: str) -> Table:
    return Table(
        table_name,
        DBEngine().metadata,
        schema=schema,
        autoload_with=get_db_conn(),
    )


def generate_merge_statement(
    src_table_name: str,
    src_schema: str,
    tgt_table_name: str,
    tgt_schema: str,
) -> str:
    tgt_table = get_table(tgt_table_name, tgt_schema)

    columns = [col.name for col in tgt_table.columns]
    primary_keys = [col.name for col in tgt_table.primary_key.columns]

    if not primary_keys:
        msg = f"Table {tgt_schema}.{tgt_table_name} does not have a primary key."
        raise ValueError(
            msg,
        )

    source_alias = "src"
    target_alias = "tgt"

    merge_statement = f"MERGE INTO {tgt_schema}.{tgt_table_name} AS {target_alias}\n"
    merge_statement += f"USING (SELECT {', '.join(columns)} FROM {src_schema}.{src_table_name}) AS {source_alias} ({', '.join(columns)})\n"
    merge_statement += f"ON {' AND '.join([f'{target_alias}.{pk} = {source_alias}.{pk}' for pk in primary_keys])}\n"
    merge_statement += "WHEN MATCHED THEN\n"
    merge_statement += f"UPDATE SET {', '.join([f'{col} = {source_alias}.{col}' for col in columns if col not in primary_keys])}\n"
    merge_statement += "WHEN NOT MATCHED THEN\n"
    merge_statement += f"INSERT ({', '.join(columns)})\n"
    merge_statement += (
        f"VALUES ({', '.join([f'{source_alias}.{col}' for col in columns])});"
    )

    return merge_statement
