"""Импорт всех моделей: так они регистрируются в Base.metadata (нужно Alembic и тестам)."""

from app.models.campaign import Campaign

__all__ = ["Campaign"]
