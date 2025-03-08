from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import dlt
import pandas as pd
from app import log
from app.common.db import execute_sql_statement, generate_merge_statement
from app.common.utils import to_snake_case
from app.mkt_data.market_data import get_yfinance_price_data
from app.mkt_data.models import ItemMaster, MarketData
from app.mkt_data.quant_db import get_all_items, get_all_securities
from pandas.core.frame import DataFrame

if TYPE_CHECKING:
    from app.mkt_data.models import ItemMaster, SecMaster


def main(
    start_date: str = str(date.today() - timedelta(7)),
    end_date: str | None = None,
):
    sec_master: list[SecMaster] = get_all_securities()
    item_master: dict[Any, ItemMaster] = get_all_items()

    tickers = [sec.symbol for sec in sec_master][10:35]

    # loop through 10 tickers at a time
    for i in range(0, len(tickers), 10):
        data: dict[str, DataFrame] = get_yfinance_price_data(
            tickers[i : i + 10],
            start_date,
            end_date,
        )

        data_to_load = []
        for ticker, df in data.items():
            df.columns = [to_snake_case(col) for col in df.columns]
            df = df.dropna(axis=0, how="all")
            records = df.to_dict(orient="index")
            procssed_data = [
                MarketData(
                    symbol=ticker,
                    item_id=item_master[item_name].item_id,
                    value_date=timestamp,  # type: ignore
                    value=value,
                )
                for timestamp, price_data in records.items()
                for item_name, value in price_data.items()
            ]
            data_to_load.extend(procssed_data)
            log.info(f"Processed {ticker} data.")

        pipeline = dlt.pipeline(
            pipeline_name="price_data",
            destination="mssql",
            dataset_name="stg",
        )

        pipeline.run(
            data=data_to_load,
            table_name="price_data",
            dataset_name="stg",
            write_disposition="replace",
        )
        log.info(f"Loaded {len(data_to_load)} records to stg.price_data table.")

        execute_sql_statement(
            generate_merge_statement(
                "price_data",
                "stg",
                "fct_market_data",
                "dbo",
            ),
        )
        log.info("Market data has been updated.")


if __name__ == "__main__":
    main("2000-01-01")
