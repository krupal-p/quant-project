from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str
    SQLSERVER_URL: str


config = Settings(
    _env_file=Path(__file__).parent / ".env",
    _env_file_encoding="utf-8",
)  # type: ignore


if __name__ == "__main__":
    print(config)
