from sqlalchemy import Engine, create_engine

from app import config


def get_db_conn(url: str) -> Engine:
    return create_engine(url)


sqlserver_conn: Engine = get_db_conn(config.SQLSERVER_URL)
