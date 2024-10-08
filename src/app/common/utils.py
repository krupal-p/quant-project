import re
import time
from functools import wraps

from app import log


def to_snake_case(string: str) -> str:
    # Replace spaces and hyphens with underscores
    string = string.replace(" ", "_").replace("-", "_")
    # Convert CamelCase or PascalCase to snake_case
    string = re.sub(r"(?<!^)(?=[A-Z][a-z])", "_", string)
    # Handle numbers and mixed characters
    string = re.sub(r"(?<=[a-zA-Z])(?=\d)", "_", string)
    string = re.sub(r"(?<=\d)(?=[a-zA-Z])", "_", string)
    # Handle consecutive underscores
    string = re.sub(r"__+", "_", string)
    # Remove special characters
    string = re.sub(r"[^\w\s]", "", string)
    # Convert to lowercase
    return string.lower()


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        log.info(
            f"Function {func.__name__}{args} {kwargs} Took {total_time:.8f} seconds",
        )
        return result

    return timeit_wrapper
