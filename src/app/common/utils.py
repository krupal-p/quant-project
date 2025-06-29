import re
import time
import unicodedata
from functools import wraps

from app import log


def to_snake_case(value: str) -> str:
    # Normalize unicode to ASCII
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )

    # Replace all non-alphanumeric characters with space
    value = re.sub(r"[^\w]", " ", value)

    # Handle acronym followed by normal word (e.g., 'XMLHttp' -> 'XML Http')
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)

    # Handle lowercase/digit followed by uppercase (e.g., 'fooBar' -> 'foo Bar')
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)

    # Handle letter followed by digit or digit followed by letter (e.g., 'foo123Bar' -> 'foo 123 Bar')
    value = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", value)
    value = re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", value)

    # Replace underscores with space for normalization
    value = re.sub(r"_+", " ", value)

    # Normalize multiple spaces
    value = re.sub(r"\s+", " ", value).strip()

    # Split and lowercase
    parts = value.lower().split()

    return "_".join(parts)


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
