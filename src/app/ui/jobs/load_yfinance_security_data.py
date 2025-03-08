from typing import TYPE_CHECKING

import dlt
from app import log
from app.common.db import execute_sql_statement, generate_merge_statement
from app.mkt_data.market_data import get_ticker_list, get_yfinance_security_data

if TYPE_CHECKING:
    from app.mkt_data.models import Security


def main():
    data: list[Security] = []
    tickers: list[str] = get_ticker_list()
    for ticker in tickers:
        try:
            data.append(get_yfinance_security_data(ticker))
            log.info("Data for %s has been retrieved.", ticker)
        except Exception as e:
            log.error("Error getting data for %s: %s", ticker)
            log.error(e)

    # save the S&P 500 index constituents to the database
    pipeline = dlt.pipeline(
        pipeline_name="security_data",
        destination="mssql",
        dataset_name="stg",
    )

    pipeline.run(
        data,
        table_name="security_data",
        dataset_name="stg",
        write_disposition="replace",
    )
    execute_sql_statement(
        generate_merge_statement(
            "security_data",
            "stg",
            "dim_sec_master",
            "dbo",
        ),
    )
    log.info("Security data has been updated.")


if __name__ == "__main__":
    main()
