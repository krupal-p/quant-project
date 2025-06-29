import streamlit as st

from app import log
from app.ui.resources import get_executor


def run_complextask(num: int):
    return num * 2


def sidebar():
    log.info("Running sidebar")
    st.logo("static/streamlit.png")

    home_page = st.Page(home_page_view, title="Home", icon=":material/home:")
    options_pages = [
        st.Page(
            "../options/black_scholes_page.py",
            title="Black-Scholes",
            icon="📈",
        ),
        st.Page(
            "../options/options_page.py",
            title="Options",
            icon="📈",
        ),
    ]
    pg = st.navigation(
        {
            "Home": [home_page],
            "Options": options_pages,
        },
    )
    log.info(pg.url_path)
    pg.run()


def home_page_view():
    st.set_page_config(
        page_title="Quant App",
        layout="wide",
    )
    log.info("Starting Streamlit app")
    if st.session_state.get("counter") is None:
        st.session_state.counter = 0

    st.write("Counter: ", st.session_state.counter)
    if st.button("Increment counter"):
        st.session_state.counter += 1

    futures = [get_executor().submit(run_complextask, num) for num in range(10)]

    for future in futures:
        st.write("Result: ", future.result())


def main():
    sidebar()


if __name__ == "__main__":
    main()
