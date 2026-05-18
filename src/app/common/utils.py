import re
import time
import unicodedata
from functools import wraps

from app import log


def to_snake_case(s: str) -> str:
    """Convert any string to snake_case."""
    if not s:
        return ""
    # Normalize unicode to ASCII where possible
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    # Put underscore between lower->Upper (e.g., "fooBar" -> "foo_Bar")
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    # Replace any non-alphanumeric characters with underscores
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s)
    # Collapse multiple underscores, strip edges, lowercase
    s = re.sub(r"_+", "_", s).strip("_").lower()
    return s


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
