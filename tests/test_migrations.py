import sqlite3

from alembic import command
from alembic.config import Config


def test_migrations_upgrade_clean_database_to_head(tmp_path, monkeypatch):
    # Миграции гоняем на файловой SQLite: in-memory база живёт только в одном соединении,
    # а Alembic открывает своё.
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")

    command.upgrade(Config("alembic.ini"), "head")

    with sqlite3.connect(db_file) as conn:
        tables = {row[0] for row in conn.execute("select name from sqlite_master")}
    assert "alembic_version" in tables
