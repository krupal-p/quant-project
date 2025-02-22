from app.mkt_data.models import SecMaster
from app.mkt_data.quant_db import get_all_securities


def test_get_all_securities():
    securties: list[SecMaster] = get_all_securities()

    assert securties is not None
