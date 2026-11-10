"""Конфигурация приложения, читается из переменных окружения и файла .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Значения по умолчанию подходят для локальной разработки."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AutoParts Catalog API"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # По умолчанию используется SQLite, в Docker — PostgreSQL через asyncpg
    database_url: str = "sqlite+aiosqlite:///./autoparts.db"

    jwt_secret_key: str = "dev-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


settings = Settings()
