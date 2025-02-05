import json
from pathlib import Path

import pandas as pd
import yfinance as yf
from app.mkt_data.models import Security, SP500Constituent


def get_yfinance_price_data(
    tickers: list[str],
    start_date: str,
    end_date: str | None = None,
) -> dict[str, pd.DataFrame]:
    data = yf.download(tickers, start=start_date, end=end_date)

    # Convert to dictionary
    return {
        ticker: data.xs(ticker, axis=1, level="Ticker")
        for ticker in data.columns.get_level_values(1).unique()
    }


def get_yfinance_security_data(symbol: str):
    ticker_data = yf.Ticker(symbol)
    symbol_data = yf.Ticker(symbol).info
    isin = ticker_data.isin

    if isin is None or isin == "-":
        isin = ""
    return Security(**symbol_data, isin=isin)


def get_ticker_list() -> list[str]:
    file_path = Path(__file__).parent / "yfinance_symbols.json"
    # read the file contents and convert the json to a list of str
    with file_path.open() as file:
        return json.load(file)


def get_sp500_constituents() -> list[SP500Constituent]:
    tickers = pd.read_html(
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
