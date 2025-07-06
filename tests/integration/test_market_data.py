from typing import TYPE_CHECKING

from app import log
from app.mkt_data.market_data import (
    get_sp500_constituents,
    get_yfinance_data,
    get_yfinance_security_data,
)

if TYPE_CHECKING:
    from app.common.models import Security, SP500Constituent


def test_get_sp500_constituents():
    sp500_constituents: list[SP500Constituent] = get_sp500_constituents()
    assert sp500_constituents is not None


def test_get_yfinance_data():
    data = get_yfinance_data("AAPL")
    assert data is not None

    assert len(data) > 0


def test_get_yfinance_security_data():
    data: Security = get_yfinance_security_data("AAPL")
    assert data is not None

    log.info("data: %s", data)
    assert data.symbol == "AAPL"
    assert data.quote_type == "EQUITY"
