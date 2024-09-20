import threading
from pathlib import Path

from pydantic import DirectoryPath
from pydantic_settings import BaseSettings


class Config:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
                cls.config = Settings(
                    _env_file=Path(__file__).parent / ".env",  # type: ignore
                    _env_file_encoding="utf-8",  # type: ignore
                )
                print("New instance created")
        return cls._instance


class Settings(BaseSettings):
    LOG_LEVEL: str
    SQLSERVER_URL: str
    LOG_DIR: DirectoryPath = Path(__file__).parent


def get_config() -> Settings:
    return Config().config


config = get_config()

if __name__ == "__main__":
    print(get_config())
