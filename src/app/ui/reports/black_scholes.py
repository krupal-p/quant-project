import streamlit as st

from app import log
from app.options.blackscholes import black_scholes_vectorized


def main():
    st.write(
        """
        # Black-Scholes Option Pricing Model
        """,
    )
    col1, col2, col3 = st.columns(3)

    with col1:
        option_type = st.selectbox("Option Type", ["Call", "Put"])

    with col2:
        spot_prices = st.slider("Spot Price", 0.0, 100.0, 50.0, 0.1)
        strike_prices = st.slider("Strike Price", 0.0, 100.0, 50.0, 0.1)
        time_to_expiry = st.slider("Time to Expiry (years)", 0.0, 1.0, 0.5, 0.01)

    with col3:
        risk_free_rate = st.slider("Risk-Free Rate", 0.0, 1.0, 0.05, 0.01)
        sigma = st.slider("Volatility", 0.0, 1.0, 0.2, 0.01)


if __name__ == "__main__":
    main()
