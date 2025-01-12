from app.common.db import get_db_conn, get_table, read_sql, read_sql_polar
from sqlalchemy import text


def test_sql_server_conn():
    with get_db_conn().connect() as conn:
        result = conn.execute(text("SELECT 1"))
        if data := result.fetchone():
            assert data[0] == 1


def test_read_sql():
    df = read_sql("SELECT 1")
    assert df.shape == (1, 1)
    assert df.iloc[0, 0] == 1


def test_read_sql_polar():
    df = read_sql_polar("SELECT 1")
    assert df.shape == (1, 1)


def test_get_table():
    table = get_table("dim_item_master", schema="dbo")
    assert table.name == "dim_item_master"
    assert len(table.columns) == 3
    assert "item_id" in table.columns
    assert "item_name" in table.columns
    assert "item_desc" in table.columns
    assert table.primary_key.columns.keys() == ["item_id"]
