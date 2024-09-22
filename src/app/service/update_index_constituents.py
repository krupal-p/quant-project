from app.data.db import get_db_conn, insert_into_table
from app.data.market_data import get_sp500_constituents
from app.service.utils import execute_sql_statement_from_file


class SP500IndexConstituentsUpdater:
    def __init__(self):
        self.constituents = get_sp500_constituents()

    def save_constituents(self, constituents):
        # Update the dim_index_tracker table with any new S&P 500 constituents

        insert_into_table(
            "INSERT INTO stg.dim_index_tracker (index_name, symbol, security_name, gics_sector, gics_sub_industry, date_added) VALUES (:index_name, :symbol, :security_name, :gics_sector, :gics_sub_industry, :date_added)",
            constituents,
            "stg.dim_index_tracker",
            truncate=True,
        )

        execute_sql_statement_from_file("merge_sp500_constituents", get_db_conn())

    def main(self):
        self.save_constituents(
            [constituent.model_dump() for constituent in self.constituents],
        )
