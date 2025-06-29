from concurrent.futures import ProcessPoolExecutor

import streamlit as st

from app import log


@st.cache_resource
def get_executor() -> ProcessPoolExecutor:
    log.info("Initializing executor")
    return ProcessPoolExecutor(max_workers=4, max_tasks_per_child=100)
