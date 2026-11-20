from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OfferStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


class KeitaroChange(StrEnum):
    """Что изменилось в Keitaro с прошлого Fetch/Push (пометка для пользователя)."""

    ADDED = "added"
    REMOVED = "removed"
    SHARE_CHANGED = "share_changed"


def _enum_column(enum_cls: type[StrEnum]) -> Enum:
    """Храним значение ('active'), а не имя элемента ('ACTIVE'); без нативного ENUM в БД."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=16,
        values_callable=lambda enum: [member.value for member in enum],
    )


class Stream(Base):
    """Поток кампании Keitaro, загруженный в редактор (Fetch streams from KT)."""

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(unique=True, index=True)
    campaign_id: Mapped[int] = mapped_column(index=True, comment="id кампании в Keitaro")
    name: Mapped[str]
    position: Mapped[int | None]
    type: Mapped[str]
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    offers: Mapped[list["StreamOffer"]] = relationship(
        back_populates="stream",
        order_by="StreamOffer.sort_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def has_draft(self) -> bool:
        """Есть неопубликованные изменения (в интерфейсе — «жёлтый» поток)."""
        return any(offer.is_changed for offer in self.offers)

    @property
    def has_conflicts(self) -> bool:
        """Есть офферы, изменённые и у нас, и в Keitaro: Push заблокирован до решения."""
        return any(offer.conflict for offer in self.offers)


class StreamOffer(Base):
    """Привязка оффера к потоку: текущее (черновик) и опубликованное в Keitaro состояние.

    Черновик не хранится флагом: привязка изменена, если status/share отличаются от published_*,
    или она ещё ни разу не публиковалась (published_status = None). Пин — только наша настройка.
    """

    __tablename__ = "stream_offers"
    __table_args__ = (UniqueConstraint("stream_id", "offer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"))
    offer_id: Mapped[int] = mapped_column(comment="id оффера в Keitaro")
    offer_name: Mapped[str]
    status: Mapped[OfferStatus] = mapped_column(
        _enum_column(OfferStatus), default=OfferStatus.ACTIVE
    )
    share: Mapped[int]
    pinned: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int]
    published_status: Mapped[OfferStatus | None] = mapped_column(_enum_column(OfferStatus))
    published_share: Mapped[int | None]
    # Пометки после Fetch (DISPUTED.md №8): что изменилось в Keitaro, прежняя доля,
    # конфликт с нашим черновиком.
    keitaro_change: Mapped[KeitaroChange | None] = mapped_column(_enum_column(KeitaroChange))
    keitaro_share_before: Mapped[int | None]
    conflict: Mapped[bool] = mapped_column(default=False, server_default=false())

    stream: Mapped[Stream] = relationship(back_populates="offers")

    @property
    def is_changed(self) -> bool:
        return self.status != self.published_status or self.share != self.published_share
