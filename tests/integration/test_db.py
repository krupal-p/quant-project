import pytest
from app.common.db import DB, PgEngine, SQLiteEngine, get_db_engine
from sqlalchemy import Column, Integer, MetaData, String, Table, text


def test_pg():
    # Test the connection to the PostgreSQL database
    with get_db_engine("postgres").connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_sqlite():
    # Test the connection to the SQLite database
    with get_db_engine("sqlite").connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.fixture(params=["sqlite", "postgres"], scope="module")
def db_engine(request):
    if request.param == "sqlite":
        return SQLiteEngine()
    if request.param == "postgres":
        return PgEngine()
    msg = "Unsupported db type"
    raise ValueError(msg)


@pytest.fixture(scope="module")
def db(db_engine):
    return DB(db_engine)


@pytest.fixture(scope="module")
def test_table(db):
    metadata = db.metadata
    table = Table(
        "test_table",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
    )
    table.create(db._engine)
    yield table
    table.drop(db._engine)


def test_reflect_and_get_table(db, test_table):
    reflected = db.reflect_table("test_table")
    assert reflected.name == "test_table"
    assert db.get_table("test_table") is reflected


def test_insert_and_select(db, test_table):
    db.insert("test_table", {"id": 1, "name": "Alice"})
    rows = db.select("test_table")
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["name"] == "Alice"


def test_update(db, test_table):
    db.insert("test_table", {"id": 2, "name": "Bob"})
    updated = db.update("test_table", {"id": 2}, {"name": "Robert"})
    assert updated == 1
    row = db.select("test_table", where={"id": 2})[0]
    assert row["name"] == "Robert"


def test_delete(db, test_table):
    db.insert("test_table", {"id": 3, "name": "Charlie"})
    deleted = db.delete("test_table", {"id": 3})
    assert deleted == 1
    rows = db.select("test_table", where={"id": 3})
    assert rows == []


@pytest.mark.dependency(depends=["test_insert_and_select", "test_update"])
def test_fetch_one_and_fetch_all(db, test_table):
    db.insert(
        "test_table",
        [{"id": 4, "name": "Daisy"}, {"id": 5, "name": "Eve"}],
    )
    stmt = text("SELECT * FROM test_table WHERE id=:id")
    row = db.fetch_one(stmt, {"id": 4})
    assert row["name"] == "Daisy"
    all_rows = db.fetch_all(text("SELECT * FROM test_table"))
    assert len(all_rows) == 4


def test_execute_and_raw_query(db, test_table):
    db.execute(
        "INSERT INTO test_table (id, name) VALUES (:id, :name)",
        {"id": 6, "name": "Frank"},
    )
    result = db.raw_query("SELECT name FROM test_table WHERE id=:id", {"id": 6})
    assert result[0]["name"] == "Frank"


def test_transaction_commit_and_rollback(db, test_table):
    # Commit
    with db.transaction() as conn:
        conn.execute(
            text("INSERT INTO test_table (id, name) VALUES (:id, :name)"),
            {"id": 7, "name": "Grace"},
        )
    rows = db.select("test_table", where={"id": 7})
    assert rows
    assert rows[0]["name"] == "Grace"

    # Rollback
    try:
        with db.transaction() as conn:
            conn.execute(
                text("INSERT INTO test_table (id, name) VALUES (:id, :name)"),
                {"id": 8, "name": "Heidi"},
            )
            msg = "force rollback"
            raise RuntimeError(msg)
    except RuntimeError:
        pass
    rows = db.select("test_table", where={"id": 8})
    assert rows == []
