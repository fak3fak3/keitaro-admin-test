"""Импорт всех моделей: так они регистрируются в Base.metadata (нужно Alembic и тестам)."""

from app.models.campaign import Campaign
from app.models.stream import OfferStatus, Stream, StreamOffer

__all__ = ["Campaign", "OfferStatus", "Stream", "StreamOffer"]
