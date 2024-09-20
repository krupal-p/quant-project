from app.data.db_engine import get_db_conn, read_sql, read_sql_polar
from sqlalchemy import text


def test_sql_server_conn():
    with get_db_conn().connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1


def test_read_sql():
    df = read_sql("SELECT 1")
    assert df.shape == (1, 1)
    assert df.iloc[0, 0] == 1


def test_read_sql_polar():
    df = read_sql_polar("SELECT 1")
    assert df.shape == (1, 1)
