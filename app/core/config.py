from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Настройки БД отдельно: Alembic не должен требовать доступ к Keitaro."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./app.db"


class Settings(DatabaseSettings):
    keitaro_url: str
    keitaro_admin_token: SecretStr
