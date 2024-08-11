from qp.data import db_engine
from sqlalchemy import text


def test_db_conn():
    with db_engine.pg_conn.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1
