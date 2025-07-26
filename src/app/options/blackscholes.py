from collections.abc import Iterable

import numpy as np
from scipy import stats

from app.common.utils import timeit


@timeit
def black_scholes_vectorized(
    spot_prices: Iterable,
    strike_prices: Iterable,
    time_to_expiry: Iterable,
    risk_free_rate: Iterable,
    sigma: Iterable,
    option_type: str = "call",
) -> np.ndarray:
    """
    Vectorized version to calculate multiple option prices simultaneously
    All inputs can be arrays (numpy arrays recommended)
    """
    # Convert inputs to numpy arrays for vectorized operations
    spot_prices = np.asarray(spot_prices)
    strike_prices = np.asarray(strike_prices)
    time_to_expiry = np.asarray(time_to_expiry)
    risk_free_rate = np.asarray(risk_free_rate)
    sigma = np.asarray(sigma)

    # Calculate d1 and d2 parameters
    d1 = (
        np.log(spot_prices / strike_prices)
        + (risk_free_rate + 0.5 * sigma**2) * time_to_expiry
    ) / (sigma * np.sqrt(time_to_expiry))
    d2 = d1 - sigma * np.sqrt(time_to_expiry)

    # Calculate call or put price based on option_type
    if option_type.lower() == "call":
        option_price = spot_prices * stats.norm.cdf(d1) - strike_prices * np.exp(
            -risk_free_rate * time_to_expiry,
        ) * stats.norm.cdf(d2)
    elif option_type.lower() == "put":
        option_price = strike_prices * np.exp(
            -risk_free_rate * time_to_expiry,
        ) * stats.norm.cdf(
            -d2,
        ) - spot_prices * stats.norm.cdf(
            -d1,
        )
    else:
        msg = "Option type must be 'call' or 'put'"
        raise ValueError(msg)

    return option_price
