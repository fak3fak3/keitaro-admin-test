from datetime import datetime

from sqlalchemy import JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Campaign(Base):
    """Кампания, созданная через нашу обёртку (реестр; источник правды — Keitaro)."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    alias: Mapped[str]
    geo: Mapped[list[str]] = mapped_column(JSON)
    offer_id: Mapped[int]
    geo_stream_id: Mapped[int]
    offer_stream_id: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
