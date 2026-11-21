from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Настройки БД отдельно: Alembic не должен требовать доступ к Keitaro."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./app.db"


class Settings(DatabaseSettings):
    keitaro_url: str
    keitaro_admin_token: SecretStr
    # С какими доменом, группой и источником создаются кампании (ищутся в Keitaro по имени).
    keitaro_domain: str = "kylovoa.com"
    keitaro_group: str = "FORTESTS"
    keitaro_traffic_source: str = "FORTESTS"
    # Как часто опрашивать Keitaro, пока открыт редактор (секунды; DECISIONS.md №37)
    keitaro_poll_interval: float = 1.0


class WebSettings(BaseSettings):
    """Настройки HTTP-слоя; не требуют доступа к Keitaro."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:5173"  # адреса фронта через запятую (Vite dev-сервер)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
