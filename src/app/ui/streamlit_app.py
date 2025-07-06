import streamlit as st
from streamlit.navigation.page import StreamlitPage

from app import log


def sidebar():
    log.info("Running sidebar")
    st.logo("static/streamlit.png")

    home_page: StreamlitPage = st.Page(
        home_page_view,
        title="Home",
        icon=":material/home:",
    )
    options_pages: list[StreamlitPage] = [
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
    portfolio_pages: list[StreamlitPage] = [
        st.Page(
            "../portfolio/portfolio_page.py",
            title="Portfolio Optimization",
            icon="📊",
        ),
    ]
    pg: StreamlitPage = st.navigation(
        # [home_page, options_pages[0]],
        {
            "Home": [home_page],
            "Options": options_pages,
            "Portfolio Optimization": portfolio_pages,
        },
    )
    log.info(pg.url_path)

    pg.run()


def home_page_view():
    st.set_page_config(
        page_title="Quant App",
        layout="wide",
    )
    log.info("Running home page view")
    if st.session_state.get("counter") is None:
        st.session_state.counter = 0

    st.write("Counter: ", st.session_state.counter)
    if st.button("Increment counter"):
        st.session_state.counter += 1


def main():
    sidebar()


if __name__ == "__main__":
    main()
