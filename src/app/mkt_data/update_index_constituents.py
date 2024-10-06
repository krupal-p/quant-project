from typing import TYPE_CHECKING

from app.common.db import (
    execute_sql_statement_from_file,
    get_db_conn,
    insert_into_table,
)
from app.mkt_data.market_data import get_sp500_constituents

if TYPE_CHECKING:
    from app.mkt_data.models import SP500Constituent


class SP500IndexConstituentsUpdater:
    def __init__(self):
        self.constituents: list[SP500Constituent] = get_sp500_constituents()

    def save_constituents(self, constituents):
        # Update the dim_index_tracker table with any new S&P 500 constituents
        insert_into_table(constituents, "dim_index_tracker", "stg", truncate=True)

        execute_sql_statement_from_file("merge_sp500_constituents")

    def main(self):
        self.save_constituents(
            [constituent.model_dump() for constituent in self.constituents],
        )
