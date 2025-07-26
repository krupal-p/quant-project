from prefect import Flow, Task
from prefect.client.schemas.objects import FlowRun, State, TaskRun

from app.common.email_sender import email_send_message


def task_state_hook(task: Task, task_run: TaskRun, state: State) -> None:
    email_send_message(
        subject=f"Task {task.name} run {task_run.id} completed",
        msg=f"Task {task.name} run {task_run.id} has completed with state: {state}",
        email_from="test",
        email_to="recipient@example.com",
    )


def flow_state_hook(flow: Flow, flow_run: FlowRun, state: State) -> None:
    email_send_message(
        subject=f"Flow {flow.name} run {flow_run.id} completed",
        msg=f"Flow {flow.name} run {flow_run.id} has completed with state: {state.data}",
        email_from="test",
        email_to="recipient@example.com",
    )
