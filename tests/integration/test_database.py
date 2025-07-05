import pytest
from app.common.database import DB, get_db
from sqlalchemy import Column, Integer, String, Table, text


def test_pg():
    # Test the connection to the PostgreSQL database
    with get_db("postgres").get_engine().connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_sqlite():
    # Test the connection to the SQLite database
    with get_db("sqlite").get_engine().connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.fixture(scope="module", params=["sqlite", "postgres"])
def db(request) -> DB:
    return get_db(request.param)


@pytest.fixture
def test_table(db: DB):
    if "test_table" in db.metadata.tables:
        table = db.metadata.tables["test_table"]
    else:
        table = Table(
            "test_table",
            db.metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )

    # Ensure table exists in database (create if not exists)
    table.create(db._engine, checkfirst=True)
    with db._engine.begin() as conn:
        conn.execute(table.delete())
    yield table
    table.drop(db._engine)


def test_get_table(db: DB, test_table):
    reflected = db.get_table("test_table")
    assert reflected.name == "test_table"
    assert db.get_table("test_table") is reflected


def test_insert_and_select(db: DB, test_table):
    db.insert("test_table", {"id": 1, "name": "Alice"})
    rows = db.select("test_table")
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["name"] == "Alice"


def test_update(db: DB, test_table):
    db.insert("test_table", {"id": 2, "name": "Bob"})
    updated = db.update("test_table", {"id": 2}, {"name": "Robert"})
    assert updated == 1
    row = db.select("test_table", where={"id": 2})[0]
    assert row["name"] == "Robert"


def test_delete(db: DB, test_table):
    db.insert("test_table", {"id": 3, "name": "Charlie"})
    deleted = db.delete("test_table", {"id": 3})
    assert deleted == 1.0
    rows = db.select("test_table", where={"id": 3})
    assert rows == []


def test_fetch_one_and_fetch_all(db: DB, test_table):
    db.insert(
        "test_table",
        [{"id": 4, "name": "Daisy"}, {"id": 5, "name": "Eve"}],
    )
    stmt = text("SELECT * FROM test_table WHERE id=:id")
    row = db.fetch_one(stmt, {"id": 4})
    assert row["name"] == "Daisy"
    all_rows = db.fetch_all(text("SELECT * FROM test_table"))
    assert len(all_rows) == 2


def test_execute_and_raw_query(db: DB, test_table):
    db.execute(
        "INSERT INTO test_table (id, name) VALUES (:id, :name)",
        {"id": 6, "name": "Frank"},
    )
    result = db.raw_query("SELECT name FROM test_table WHERE id=:id", {"id": 6})
    assert result is not None
    assert result[0]["name"] == "Frank"


@pytest.fixture(scope="module")
def merge_tables(db: DB):
    metadata = db.metadata
    # Create target table
    target = Table(
        "merge_target",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("value", Integer),
    )
    # Create source table
    source = Table(
        "merge_source",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("value", Integer),
    )
    target.create(db._engine)
    source.create(db._engine)
    yield {"target": target, "source": source}
    source.drop(db._engine)
    target.drop(db._engine)


@pytest.mark.parametrize("db", ["sqlite", "postgres"], indirect=True)
def test_merge_insert_and_update(db: DB, merge_tables):
    # Insert initial data into target and source
    db.insert(
        "merge_target",
        [
            {"id": 1, "name": "Alice", "value": 10},
            {"id": 2, "name": "Bob", "value": 20},
        ],
    )
    db.insert(
        "merge_source",
        [
            {"id": 2, "name": "Bob", "value": 25},  # Should update value
            {"id": 3, "name": "Charlie", "value": 30},  # Should insert new row
        ],
    )

    # Perform merge on 'id' key
    db.merge(
        source_table="merge_source",
        target_table="merge_target",
    )

    rows = db.select("merge_target", order_by=[merge_tables["target"].c.id])
    assert len(rows) == 3
    assert rows[0]["id"] == 1
    assert rows[0]["name"] == "Alice"
    assert rows[0]["value"] == 10
    assert rows[1]["id"] == 2
    assert rows[1]["name"] == "Bob"
    assert rows[1]["value"] == 25
    assert rows[2]["id"] == 3
    assert rows[2]["name"] == "Charlie"
    assert rows[2]["value"] == 30


@pytest.mark.parametrize("db", ["sqlite", "postgres"], indirect=True)
def test_merge_with_custom_update_columns(db: DB, merge_tables):
    # Clean up tables before test to avoid UNIQUE constraint errors
    db.execute("DELETE FROM merge_target")
    db.execute("DELETE FROM merge_source")

    db.insert("merge_target", {"id": 1, "name": "Alice", "value": 100})
    db.insert("merge_source", {"id": 1, "name": "Alicia", "value": 200})

    # Only update 'name', not 'value'
    db.merge(
        source_table="merge_source",
        target_table="merge_target",
        update_columns=["name"],
    )

    row = db.select("merge_target", where={"id": 1})[0]
    assert row["name"] == "Alicia"
    assert row["value"] == 100  # value should remain unchanged


@pytest.mark.parametrize("db", ["sqlite", "postgres"], indirect=True)
def test_merge_with_no_update_columns(db: DB, merge_tables):
    # Clean up tables before test to avoid UNIQUE constraint errors
    db.execute("DELETE FROM merge_target")
    db.execute("DELETE FROM merge_source")

    db.insert("merge_target", {"id": 1, "name": "Alice", "value": 1})
    db.insert("merge_source", {"id": 1, "name": "Alice", "value": 2})

    # update_columns=None should update all except keys
    db.merge(
        source_table="merge_source",
        target_table="merge_target",
    )

    row = db.select("merge_target", where={"id": 1})[0]
    assert row["value"] == 2

    row = db.select("merge_target", where={"id": 1})[0]
    assert row["value"] == 2
