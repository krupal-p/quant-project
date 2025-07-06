import uuid

import pytest
from app.common.database import DB, get_db
from sqlalchemy import Column, Integer, String, Table, text


@pytest.fixture(scope="module", params=["sqlite", "postgres"])
def db(request) -> DB:
    return get_db(request.param)


def test_pg():
    with get_db("postgres").get_engine().connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_sqlite():
    with get_db("sqlite").get_engine().connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_adbc_conn():
    """Test the ADBC connection for PostgreSQL."""
    db = get_db("postgres")
    assert db is not None
    conn = db.get_adbc_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
        assert result is not None
        assert result[0] == 1
    conn.close()


@pytest.fixture
def test_table(db: DB):
    """Create a unique test table for each test."""
    table_name = f"test_table_{uuid.uuid4().hex[:8]}"
    table = Table(
        table_name,
        db.metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
    )
    table.create(db._engine)
    yield table
    table.drop(db._engine, checkfirst=True)


def test_get_table(db: DB, test_table):
    """Test table reflection."""
    reflected = db.get_table(test_table.name)
    assert reflected.name == test_table.name
    assert db.get_table(test_table.name) is reflected


def test_insert_and_select(db: DB, test_table):
    """Test insert and select operations."""
    db.insert(test_table.name, {"id": 1, "name": "Alice"})
    rows = db.select(test_table.name)
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["name"] == "Alice"


def test_update(db: DB, test_table):
    """Test update operation."""


def test_delete(db: DB, test_table):
    db.insert(test_table.name, {"id": 3, "name": "Charlie"})
    deleted = db.delete(test_table.name, {"id": 3})
    assert deleted == 1.0
    rows = db.select(test_table.name, where={"id": 3})
    assert rows == []


def test_fetch_one_and_fetch_all(db: DB, test_table):
    db.insert(
        test_table.name,
        [{"id": 4, "name": "Daisy"}, {"id": 5, "name": "Eve"}],
    )
    stmt = text(f"SELECT * FROM {test_table.name} WHERE id=:id")
    row = db.fetch_one(stmt, {"id": 4})
    assert row is not None
    assert row["name"] == "Daisy"
    all_rows = db.fetch_all(text(f"SELECT * FROM {test_table.name}"))
    assert len(all_rows) == 2


def test_execute_and_raw_query(db: DB, test_table):
    db.execute(
        f"INSERT INTO {test_table.name} (id, name) VALUES (:id, :name)",
        {"id": 6, "name": "Frank"},
    )
    result = db.raw_query(
        f"SELECT name FROM {test_table.name} WHERE id=:id",
        {"id": 6},
    )
    assert result is not None
    assert result[0]["name"] == "Frank"


@pytest.fixture(scope="module")
def merge_tables(db: DB):
    metadata = db.metadata

    target = Table(
        f"merge_target_{uuid.uuid4().hex[:8]}",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("value", Integer),
    )
    source = Table(
        f"merge_source_{uuid.uuid4().hex[:8]}",
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
        merge_tables["target"].name,
        [
            {"id": 1, "name": "Alice", "value": 10},
            {"id": 2, "name": "Bob", "value": 20},
        ],
    )
    db.insert(
        merge_tables["source"].name,
        [
            {"id": 2, "name": "Bob", "value": 25},  # Should update value
            {"id": 3, "name": "Charlie", "value": 30},  # Should insert new row
        ],
    )

    # Perform merge on 'id' key
    db.merge(
        source_table=merge_tables["source"].name,
        target_table=merge_tables["target"].name,
    )

    rows = db.select(
        merge_tables["target"].name,
        order_by=[merge_tables["target"].c.id],
    )
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
    db.execute(f"DELETE FROM {merge_tables['target'].name}")
    db.execute(f"DELETE FROM {merge_tables['source'].name}")

    db.insert(merge_tables["target"].name, {"id": 1, "name": "Alice", "value": 100})
    db.insert(merge_tables["source"].name, {"id": 1, "name": "Alicia", "value": 200})

    # Only update 'name', not 'value'
    db.merge(
        source_table=merge_tables["source"].name,
        target_table=merge_tables["target"].name,
        update_columns=["name"],
    )

    row = db.select(merge_tables["target"].name, where={"id": 1})[0]
    assert row["name"] == "Alicia"
    assert row["value"] == 100  # value should remain unchanged


@pytest.mark.parametrize("db", ["sqlite", "postgres"], indirect=True)
def test_merge_with_no_update_columns(db: DB, merge_tables):
    # Clean up tables before test to avoid UNIQUE constraint errors
    db.execute(f"DELETE FROM {merge_tables['target'].name}")
    db.execute(f"DELETE FROM {merge_tables['source'].name}")

    db.insert(merge_tables["target"].name, {"id": 1, "name": "Alice", "value": 1})
    db.insert(merge_tables["source"].name, {"id": 1, "name": "Alice", "value": 2})

    # update_columns=None should update all except keys
    db.merge(
        source_table=merge_tables["source"].name,
        target_table=merge_tables["target"].name,
    )

    row = db.select(merge_tables["target"].name, where={"id": 1})[0]
    assert row["value"] == 2


def test_bulk_insert(db: DB, test_table):
    """Test bulk insert using PyArrow table."""
    import pyarrow as pa

    data = pa.table(
        {
            "id": pa.array([10, 20], type=pa.int32()),
            "name": pa.array(["Xavier", "Yara"], type=pa.string()),
        },
    )
    if db.dialect == "sqlite":
        pytest.raises(
            NotImplementedError,
            db.bulk_insert,
            test_table.name,
            data,
            mode="create_append",
        )
        return
    if db.dialect == "postgresql":
        db.bulk_insert(test_table.name, data, mode="append")
    rows = db.select(test_table.name, order_by=["id"])
    assert len(rows) == 2
    assert rows[0]["id"] == 10
    assert rows[0]["name"] == "Xavier"
    assert rows[1]["id"] == 20
    assert rows[1]["name"] == "Yara"
