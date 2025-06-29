import threading

from app import config
from sqlalchemy import Engine, create_engine


class PostgresEngine:
    # Singleton instance of the PostgresEngine
    _instance = None
    _pg: Engine

    def __new__(cls):
        if cls._instance is None:
            # Ensure thread safety when creating the singleton instance
            with threading.Lock():
                # Check again in case another thread created the instance
                if cls._instance is None:
                    # Create the singleton instance and the SQLAlchemy engine
                    cls._instance = super().__new__(cls)
                    cls._pg: Engine = create_engine(
                        config.POSTGRES_URL,
                    )
        return cls._instance


def get_pg_engine() -> Engine:
    """
    Returns the singleton instance of the PostgresEngine.

    This function ensures that only one instance of the PostgresEngine is created,
    providing a consistent database connection throughout the application.

    Returns:
        Engine: The SQLAlchemy engine for PostgreSQL.
    """
    return PostgresEngine()._pg
