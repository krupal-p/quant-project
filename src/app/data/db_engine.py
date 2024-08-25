from sqlalchemy import create_engine

from app import config

sqlserver_conn = create_engine(config.SQLSERVER_URL)
