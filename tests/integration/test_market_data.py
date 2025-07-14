import pytest


@pytest.fixture(scope="module")
def market_data():
    from app.mkt_data import market_data

    return market_data


def test_get_sp500_constituents(market_data):
    sp500_constituents = market_data.get_sp500_constituents()
    assert sp500_constituents is not None


def test_get_yfinance_data(market_data):
    data = market_data.get_yfinance_data("AAPL")
    assert data is not None

    assert len(data) > 0


def test_get_yfinance_security_data(market_data):
    data = market_data.get_yfinance_security_data("AAPL")
    assert data is not None

    assert data.symbol == "AAPL"
    assert data.quote_type == "EQUITY"
