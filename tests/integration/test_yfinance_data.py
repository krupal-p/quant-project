from app.data.yfinance_data import get_sp500_constituents
from app.models.models import SP500Constituent


def test_get_sp500_constituents():
    sp500_constituents: list[SP500Constituent] = get_sp500_constituents()
    assert sp500_constituents is not None
