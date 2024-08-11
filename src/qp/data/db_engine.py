from sqlalchemy import create_engine

from qp import config

pg_conn = create_engine(config.POSTGRES_URL)
