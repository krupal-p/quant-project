from sqlalchemy import create_engine

from qp import config

sqlserver_conn = create_engine(config.SQLSERVER_URL)
