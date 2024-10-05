from typing import TYPE_CHECKING

from app.mkt_data.market_data import get_sp500_constituents

if TYPE_CHECKING:
    from app.mkt_data.models import SP500Constituent


def test_get_sp500_constituents():
    sp500_constituents: list[SP500Constituent] = get_sp500_constituents()
    assert sp500_constituents is not None
