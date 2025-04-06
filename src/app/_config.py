import threading
from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, DirectoryPath, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file"""

    LOG_LEVEL: str = Field(
        ...,
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    SQLSERVER_URL: str = Field(..., description="SQL Server connection URL")
    LOG_DIR: DirectoryPath = Field(
        default=Path(__file__).parent,
        description="Directory for log files",
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that LOG_LEVEL is a valid logging level"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            msg = f"LOG_LEVEL must be one of {valid_levels}"
            raise ValueError(msg)
        return v.upper()

    model_config = ConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        frozen=True,
    )  # type: ignore


class Config:
    """Thread-safe singleton configuration manager"""

    _instance: Optional["Config"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False
    settings: Settings

    def __new__(cls) -> "Config":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._load_settings()
                    self._initialized = True

    def _load_settings(self) -> None:
        """Load settings from environment variables and .env file"""
        try:
            self.settings = Settings()  # type: ignore
        except Exception as e:
            msg = f"Failed to load configuration: {e!s}"
            raise RuntimeError(msg) from e

    @property
    def config(self) -> Settings:
        """Get the application settings"""
        return self.settings


# Global configuration instance
config = Config().config

if __name__ == "__main__":
    print(config)
