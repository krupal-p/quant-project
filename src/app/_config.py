from pydantic import ConfigDict, DirectoryPath, Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application config loaded from environment variables and .env file"""

    LOG_LEVEL: str = Field(
        ...,
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    POSTGRES_URL: str = Field(..., description="PostgreSQL connection URL")
    LOG_DIR: DirectoryPath = Field(
        description="Directory for log files",
    )
    DBT_PROFILES_DIR: DirectoryPath
    DBT_PROJECT_DIR: DirectoryPath
    model_config = ConfigDict(
        frozen=True,
    )  # type: ignore


config = Config()  # type: ignore

if __name__ == "__main__":
    print(config)
