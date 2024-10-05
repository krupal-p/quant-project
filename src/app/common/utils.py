import re
from pathlib import Path

from sqlalchemy import Engine, text


def execute_sql_statement_from_file(file_name: str, engine: Engine) -> None:
    """
    Execute a SQL statement from a file in the sql directory without the sql extension.
    """
    file_path = Path(__file__).parent.parent / "sql" / (file_name + ".sql")

    with Path(file_path).open() as file:
        sql_statement = file.read()
        with engine.begin() as conn:
            conn.execute(text(sql_statement))


def to_snake_case(s):
    # Replace spaces and hyphens with underscores
    s = s.replace(" ", "_").replace("-", "_")
    # Convert CamelCase or PascalCase to snake_case
    s = re.sub(r"(?<!^)(?=[A-Z][a-z])", "_", s)
    # Handle numbers and mixed characters
    s = re.sub(r"(?<=[a-zA-Z])(?=\d)", "_", s)
    s = re.sub(r"(?<=\d)(?=[a-zA-Z])", "_", s)
    # Handle consecutive underscores
    s = re.sub(r"__+", "_", s)
    # Remove special characters
    s = re.sub(r"[^\w\s]", "", s)
    # Convert to lowercase
    return s.lower()
