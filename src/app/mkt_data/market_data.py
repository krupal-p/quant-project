from functools import lru_cache
from typing import Literal

import pandas as pd
import yfinance as yf
from app import log
from app.common.models import Security, SP500Constituent


def get_yfinance_data(
    tickers: str,
    start_date: str | None = None,
    end_date: str | None = None,
    market_data_type: Literal["close", "open", "high", "low", "volume"] = "close",
) -> pd.Series:
    data = yf.download(tickers, start_date, end_date, multi_level_index=False)
    if data is None:
        msg = "No data returned from yfinance for the specified tickers and date range"
        raise ValueError(
            msg,
        )
    data.columns = [col.lower() for col in data.columns]
    return data[market_data_type]


@lru_cache
def get_yfinance_security_data(symbol: str):
    ticker_data = yf.Ticker(symbol)
    symbol_data = yf.Ticker(symbol).info
    isin = ticker_data.isin

    if isin is None or isin == "-":
        isin = ""
    return Security(**symbol_data, isin=isin)


@lru_cache
def get_yfinance_ticker_data(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


@lru_cache
def get_sp500_constituents() -> list[SP500Constituent]:
    tickers: pd.DataFrame = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    )[0]

    tickers.columns = [
        "symbol",
        "security_name",
        "gics_sector",
        "gics_sub_industry",
        "headquarters_location",
        "date_added",
        "cik",
        "founded",
    ]

    return [SP500Constituent(**ticker) for ticker in tickers.to_dict(orient="records")]  # type: ignore
