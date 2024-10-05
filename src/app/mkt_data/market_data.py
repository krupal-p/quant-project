import pandas as pd
import yfinance as yf
from app.mkt_data.models import SP500Constituent

# data = yf.Ticker("MSFT").history(period="1y")
# print(data.head())
# df = yf.download("MSFT", start="2022-01-01", end="2024-05-29")


# fiflter data for date > 2022-01-01
# df = data[data.index > "2022-01-01"]
# print(df.head())


def get_sp500_constituents() -> list[SP500Constituent]:
    tickers = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    )[0]

    tickers.columns = [
        "symbol",
        "security",
        "gics_sector",
        "gics_sub_industry",
        "headquarters_location",
        "date_added",
        "cik",
        "founded",
    ]

    return [SP500Constituent(**ticker) for ticker in tickers.to_dict(orient="records")]
