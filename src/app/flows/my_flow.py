import os
from datetime import datetime

from prefect import flow

from app import log
from app.flows.flow_utils import flow_state_hook


@flow(on_completion=[flow_state_hook], on_failure=[flow_state_hook])
def my_flow(current_time: datetime | None = None):
    if current_time is None:
        current_time = datetime.now()
    exec_env = os.getenv("EXECUTION_ENVIRONMENT")
    log.info(f"Execution environment: {exec_env}")
    log.info(f"{log.handlers} {log.level} {log.name}")
    log.info(f"Current time: {current_time}")
    log.info("app logger info message")
    log.debug("app logger debug message")
    log.warning("app logger warning message")
    log.error("app logger error message")

    return current_time


@flow(on_completion=[flow_state_hook], on_failure=[flow_state_hook])
def my_flow_2():
    log.info("This is flow_2, which runs after my_flow.")
    return "Flow 2 executed successfully."


if __name__ == "__main__":
    my_flow()
