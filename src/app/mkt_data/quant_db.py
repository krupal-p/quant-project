from typing import Any

from app.common.db import get_db_conn
from app.mkt_data.models import ItemMaster, SecMaster
from sqlalchemy import text


def get_all_securities():
    engine = get_db_conn()

    with engine.begin() as conn:
        results = (
            conn.execute(text("SELECT * FROM dbo.dim_sec_master")).mappings().fetchall()
        )
        return [SecMaster(**result) for result in results]


def get_all_items() -> dict[Any, ItemMaster]:
    engine = get_db_conn()

    with engine.begin() as conn:
        results = (
            conn.execute(text("SELECT * FROM dbo.dim_item_master"))
            .mappings()
            .fetchall()
        )
        return {result.item_name: ItemMaster(**result) for result in results}
