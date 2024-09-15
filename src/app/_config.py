from pathlib import Path

from pydantic import DirectoryPath
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str
    SQLSERVER_URL: str
    LOG_DIR: DirectoryPath = Path(__file__).parent


config = Settings(
    _env_file=Path(__file__).parent / ".env",  # type: ignore
    _env_file_encoding="utf-8",  # type: ignore
)  # type: ignore


if __name__ == "__main__":
    print(config)
