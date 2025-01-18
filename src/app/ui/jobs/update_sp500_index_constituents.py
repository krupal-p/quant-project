import dlt
from app import log
from app.common.db import execute_sql_statement, generate_merge_statement
from app.mkt_data.market_data import get_sp500_constituents


def main():
    # get the S&P 500 index constituents
    sp500_constituents = get_sp500_constituents()

    # save the S&P 500 index constituents to the database
    pipeline = dlt.pipeline(
        pipeline_name="sp500_index_constituents",
        destination="mssql",
        dataset_name="stg",
    )

    pipeline.run(
        sp500_constituents,
        table_name="sp500_index_constituents",
        dataset_name="stg",
        write_disposition="replace",
    )

    execute_sql_statement(
        generate_merge_statement(
            "sp500_index_constituents",
            "stg",
            "dim_index_tracker",
            "dbo",
        ),
    )
    log.info("S&P 500 index constituents have been updated.")


if __name__ == "__main__":
    main()
