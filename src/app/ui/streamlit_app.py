import streamlit as st

from app import log


def sidebar():
    st.logo("static/streamlit.png")

    home_page = st.Page(home_page_view, title="Home", icon=":material/home:")
    black_scholes_page = st.Page(
        "reports/black_scholes.py",
        title="Black-Scholes",
        icon="📈",
    )
    pg = st.navigation(
        {
            "Home": [home_page],
            "Options": [black_scholes_page],
        },
    )
    pg.run()


def home_page_view():
    if st.session_state.get("counter") is None:
        st.session_state.counter = 0

    st.write("Counter: ", st.session_state.counter)
    if st.button("Increment counter"):
        st.session_state.counter += 1


def main():
    log.info("Starting Streamlit app")

    st.set_page_config(
        page_title="Quant App",
        layout="wide",
    )

    sidebar()


if __name__ == "__main__":
    main()
