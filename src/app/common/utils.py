import re
import time
import unicodedata
from functools import wraps

from app import log


def to_snake_case(value: str) -> str:
    if not value:
        return ""
    value = "".join(c if unicodedata.category(c)[0] in "LN" else " " for c in value)
    value = unicodedata.normalize("NFKD", value.replace("Ł", "L").replace("ł", "l")).encode("ascii", "ignore").decode()
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


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
