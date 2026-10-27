from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Confluencr Banking API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/confluencr_bank"
    test_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/confluencr_bank_test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
