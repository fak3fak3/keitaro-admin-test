from datetime import datetime

from sqlalchemy import JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Campaign(Base):
    """Кампания, подключённая в наш сервис; источник правды о кампании — Keitaro."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    alias: Mapped[str]
    geo: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    offer_id: Mapped[int | None] = mapped_column(nullable=True)
    geo_stream_id: Mapped[int | None] = mapped_column(nullable=True)
    offer_stream_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
