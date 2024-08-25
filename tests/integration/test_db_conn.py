from app.data import db_engine
from sqlalchemy import text


def test_sql_server_conn():
    with db_engine.sqlserver_conn.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1
