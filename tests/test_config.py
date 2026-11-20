from app.core.config import Settings


def test_settings_read_keitaro_access_from_env(monkeypatch):
    monkeypatch.setenv("KEITARO_URL", "https://kt.example")
    monkeypatch.setenv("KEITARO_ADMIN_TOKEN", "secret-token")

    settings = Settings(_env_file=None)

    assert settings.keitaro_url == "https://kt.example"
    assert settings.keitaro_admin_token.get_secret_value() == "secret-token"


def test_admin_token_is_hidden_in_repr(monkeypatch):
    monkeypatch.setenv("KEITARO_URL", "https://kt.example")
    monkeypatch.setenv("KEITARO_ADMIN_TOKEN", "secret-token")

    settings = Settings(_env_file=None)

    assert "secret-token" not in repr(settings)


def test_database_url_defaults_to_local_sqlite(monkeypatch):
    monkeypatch.setenv("KEITARO_URL", "https://kt.example")
    monkeypatch.setenv("KEITARO_ADMIN_TOKEN", "secret-token")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite+aiosqlite:///./app.db"
