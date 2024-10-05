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
