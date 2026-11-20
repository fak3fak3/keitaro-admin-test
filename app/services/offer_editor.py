"""Часть 2 ТЗ: редактор офферов в потоках кампании (поведение — PLAN.md, «Поведение редактора»)."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from app.clients.keitaro import KeitaroClient
from app.clients.keitaro.schemas import Stream as KeitaroStream
from app.clients.keitaro.schemas import StreamOffer as StreamOfferPayload
from app.models.stream import KeitaroChange, OfferStatus, Stream, StreamOffer
from app.repositories.streams import StreamRepository
from app.services.errors import (
    ConflictsPendingError,
    NoConflictError,
    OfferAlreadyInStreamError,
    OfferNotFoundError,
    OfferNotInStreamError,
    OfferStateError,
    ShareError,
    StreamChangedInKeitaroError,
    StreamNotFoundError,
)
from app.services.shares import ShareSlot, rebalance

Keep = Literal["mine", "keitaro"]


class OfferEditor:
    def __init__(self, keitaro: KeitaroClient, streams: StreamRepository) -> None:
        self._keitaro = keitaro
        self._streams = streams

    async def list_streams(self, campaign_id: int) -> list[Stream]:
        """Потоки кампании с черновиком из нашей БД, без запроса к Keitaro."""
        return await self._streams.list_by_campaign(campaign_id)

    async def fetch(self, campaign_id: int) -> list[Stream]:
        """Fetch streams from KT: загрузить потоки кампании из Keitaro в нашу БД."""
        kt_streams, offers = await asyncio.gather(
            self._keitaro.get_campaign_streams(campaign_id),
            self._keitaro.list_offers(),
        )
        names = {offer.id: offer.name for offer in offers}
        known = {s.keitaro_id: s for s in await self._streams.list_by_campaign(campaign_id)}

        for kt_stream in kt_streams:
            stream = known.pop(kt_stream.id, None)
            is_new = stream is None
            if stream is None:
                stream = Stream(keitaro_id=kt_stream.id, campaign_id=campaign_id, offers=[])
                self._streams.add(stream)
            _sync_stream(stream, kt_stream, names, first_load=is_new)

        for gone in known.values():  # потоки, удалённые в Keitaro
            await self._streams.delete(gone)

        await self._streams.flush()
        return await self._streams.list_by_campaign(campaign_id)

    async def add_offer(self, stream_id: int, offer_id: int) -> Stream:
        """Add: новый оффер в поток (черновик), доли пересчитываются."""
        stream = await self._get_stream(stream_id)
        existing = _find_link(stream, offer_id)
        if existing is not None:
            removed = existing.status is OfferStatus.REMOVED
            hint = " (удалён — используйте Bring back)" if removed else ""
            raise OfferAlreadyInStreamError(f"Оффер {offer_id} уже есть в потоке{hint}")

        offers = await self._keitaro.list_offers()
        offer = next((o for o in offers if o.id == offer_id), None)
        if offer is None:
            raise OfferNotFoundError(f"Оффер {offer_id} не найден в Keitaro")

        with _rebalanced(stream):
            stream.offers.append(
                StreamOffer(
                    offer_id=offer.id,
                    offer_name=offer.name,
                    status=OfferStatus.ACTIVE,
                    share=0,
                    pinned=False,
                    sort_order=max((o.sort_order for o in stream.offers), default=-1) + 1,
                )
            )
        await self._streams.flush()
        return stream

    async def remove_offer(self, stream_id: int, offer_id: int) -> Stream:
        """Remove: оффер сереет (removed, 0%), остальные пересчитываются."""
        stream, link = await self._get_link(stream_id, offer_id)
        if link.status is OfferStatus.REMOVED:
            raise OfferStateError(f"Оффер {offer_id} уже удалён из потока")
        with _rebalanced(stream):
            link.status = OfferStatus.REMOVED
        await self._streams.flush()
        return stream

    async def bring_back(self, stream_id: int, offer_id: int) -> Stream:
        """Bring back: вернуть удалённый оффер в поток."""
        stream, link = await self._get_link(stream_id, offer_id)
        if link.status is not OfferStatus.REMOVED:
            raise OfferStateError(f"Оффер {offer_id} не удалён — возвращать нечего")
        with _rebalanced(stream):
            link.status = OfferStatus.ACTIVE
        await self._streams.flush()
        return stream

    async def pin(self, stream_id: int, offer_id: int) -> Stream:
        """Закрепить текущую долю: она перестаёт пересчитываться."""
        return await self._change_active(stream_id, offer_id, pinned=True)

    async def unpin(self, stream_id: int, offer_id: int) -> Stream:
        """Снять пин: доля снова считается автоматически."""
        return await self._change_active(stream_id, offer_id, pinned=False)

    async def set_share(self, stream_id: int, offer_id: int, share: int) -> Stream:
        """Задать долю вручную; введённое число закрепляется (DISPUTED.md №1)."""
        return await self._change_active(stream_id, offer_id, pinned=True, share=share)

    async def push(self, stream_id: int) -> Stream:
        """Push to KT: отправить активные офферы с долями; черновик становится опубликованным."""
        stream = await self._get_stream(stream_id)
        if stream.has_conflicts:
            ids = ", ".join(str(link.offer_id) for link in stream.offers if link.conflict)
            raise ConflictsPendingError(f"Решите конфликты с Keitaro по офферам {ids}, затем Push")
        await self._ensure_unchanged_in_keitaro(stream)
        active = [link for link in stream.offers if link.status is OfferStatus.ACTIVE]
        await self._keitaro.update_stream_offers(
            stream.keitaro_id,
            [StreamOfferPayload(offer_id=link.offer_id, share=link.share) for link in active],
        )  # при ошибке KeitaroError локально ничего не меняется — черновик остаётся

        for link in list(stream.offers):
            if link.status is OfferStatus.REMOVED and link.published_status is None:
                stream.offers.remove(
                    link
                )  # добавили и удалили до публикации — в Keitaro его не было
            else:
                link.published_status, link.published_share = link.status, link.share
                _clear_marks(link)
        await self._streams.flush()
        return stream

    async def resolve(self, stream_id: int, offer_id: int, keep: Keep) -> Stream:
        """Решить конфликт оффера: «оставить моё» (черновик) или «взять из Keitaro»."""
        stream, link = await self._get_link(stream_id, offer_id)
        if not link.conflict:
            raise NoConflictError(f"У оффера {offer_id} нет конфликта с Keitaro")
        _resolve(link, keep)
        _rebalance_after_resolve(stream)
        await self._streams.flush()
        return stream

    async def resolve_all(self, stream_id: int, keep: Keep) -> Stream:
        """«Всё моё» / «всё из Keitaro» — то же, что решить каждый конфликт потока."""
        stream = await self._get_stream(stream_id)
        for link in stream.offers:
            if link.conflict:
                _resolve(link, keep)
        _rebalance_after_resolve(stream)
        await self._streams.flush()
        return stream

    async def _ensure_unchanged_in_keitaro(self, stream: Stream) -> None:
        """Push отправляет весь список офферов: если Keitaro изменился после Fetch — не затираем."""
        current = await self._keitaro.get_stream(stream.keitaro_id)
        in_keitaro = {offer.offer_id: offer.share for offer in current.offers}
        published = {
            link.offer_id: link.published_share
            for link in stream.offers
            if link.published_status is OfferStatus.ACTIVE
        }
        if in_keitaro != published:
            raise StreamChangedInKeitaroError(
                f"Поток {stream.keitaro_id} изменён в Keitaro после загрузки: "
                "сделайте Fetch streams from KT и повторите"
            )

    async def cancel(self, stream_id: int) -> Stream:
        """Cancel: отменить черновик — вернуть опубликованное состояние. Пины не трогаем."""
        stream = await self._get_stream(stream_id)
        for link in list(stream.offers):
            if link.published_status is None:
                stream.offers.remove(link)  # добавлен до публикации
            else:
                link.status, link.share = link.published_status, link.published_share
                link.conflict = False
                _clear_marks(link)
        await self._streams.flush()
        return stream

    async def acknowledge(self, stream_id: int) -> Stream:
        """«Понятно»: снять пометки «изменено в Keitaro». Конфликты остаются — их нужно решить."""
        stream = await self._get_stream(stream_id)
        for link in stream.offers:
            _clear_marks(link)
        await self._streams.flush()
        return stream

    async def _change_active(
        self, stream_id: int, offer_id: int, *, pinned: bool, share: int | None = None
    ) -> Stream:
        stream, link = await self._get_link(stream_id, offer_id)
        if link.status is OfferStatus.REMOVED:
            raise OfferStateError(f"Оффер {offer_id} удалён: сначала Bring back")
        with _rebalanced(stream):
            link.pinned = pinned
            if share is not None:
                link.share = share
        await self._streams.flush()
        return stream

    async def _get_link(self, stream_id: int, offer_id: int) -> tuple[Stream, StreamOffer]:
        stream = await self._get_stream(stream_id)
        link = _find_link(stream, offer_id)
        if link is None:
            raise OfferNotInStreamError(f"Оффера {offer_id} нет в потоке {stream_id}")
        return stream, link

    async def _get_stream(self, stream_id: int) -> Stream:
        stream = await self._streams.get_by_keitaro_id(stream_id)
        if stream is None:
            raise StreamNotFoundError(
                f"Поток {stream_id} не загружен в редактор: сначала Fetch streams from KT"
            )
        return stream


def _find_link(stream: Stream, offer_id: int) -> StreamOffer | None:
    return next((link for link in stream.offers if link.offer_id == offer_id), None)


@contextmanager
def _rebalanced(stream: Stream) -> Iterator[None]:
    """Изменить поток и пересчитать доли; если доли невозможны (ShareError) — откатить изменение."""
    snapshot = [(link, link.status, link.share, link.pinned) for link in stream.offers]
    yield
    try:
        _apply_rebalance(stream)
    except ShareError:
        stream.offers[:] = [link for link, *_ in snapshot]
        for link, status, share, pinned in snapshot:
            link.status, link.share, link.pinned = status, share, pinned
        raise


def _apply_rebalance(stream: Stream, fixed: frozenset[int] = frozenset()) -> None:
    """Пересчитать доли. Неподвижны: пины, нерешённые конфликты (DISPUTED.md №8) и `fixed`."""
    slots = [
        ShareSlot(
            active=link.status is OfferStatus.ACTIVE,
            pinned=link.pinned or link.conflict or link.offer_id in fixed,
            share=link.share,
        )
        for link in stream.offers
    ]
    shares = rebalance(slots)  # ShareError — до каких-либо изменений
    for link, share in zip(stream.offers, shares, strict=True):
        link.share = share


def _clear_marks(link: StreamOffer) -> None:
    link.keitaro_change = None
    link.keitaro_share_before = None


def _resolve(link: StreamOffer, keep: Keep) -> None:
    if keep == "keitaro":
        link.status, link.share = link.published_status, link.published_share
    link.conflict = False


def _rebalance_after_resolve(stream: Stream) -> None:
    """После выбора выбранные цифры не должны «уплыть»: офферы, затронутые Keitaro (с пометкой),
    неподвижны, остаток поглощают только наши расчётные доли. Нет черновика — не трогаем ничего
    (везде «из Keitaro» = ровно состояние Keitaro). Не сходится — оставляем как выбрано."""
    if not stream.has_draft:
        return
    touched = frozenset(link.offer_id for link in stream.offers if link.keitaro_change is not None)
    try:
        _apply_rebalance(stream, fixed=touched)
    except ShareError:
        pass


def _sync_stream(
    stream: Stream, kt_stream: KeitaroStream, names: dict[int, str], *, first_load: bool
) -> None:
    """Трёхстороннее слияние с Keitaro (DISPUTED.md №8): P — published_*, D — черновик, K — Keitaro.

    K = P — ничего не делаем; K ≠ P и D = P — принимаем K с пометкой; K ≠ P и D ≠ P — конфликт:
    черновик не трогаем, P := K. Доли не пересчитываем (DISPUTED.md №4).
    """
    stream.name = kt_stream.name
    stream.position = kt_stream.position
    stream.type = kt_stream.type

    kt_shares = {kt_offer.offer_id: kt_offer.share for kt_offer in kt_stream.offers}
    for link in stream.offers:
        if link.offer_id in kt_shares:
            in_keitaro = (OfferStatus.ACTIVE, kt_shares.pop(link.offer_id))
        else:  # удалён в Keitaro руками — как будто удалили у нас (видео)
            in_keitaro = (OfferStatus.REMOVED, 0)
        _merge(link, *in_keitaro)
        link.offer_name = names.get(link.offer_id, link.offer_name)

    next_order = max((link.sort_order for link in stream.offers), default=-1) + 1
    for order, (offer_id, share) in enumerate(kt_shares.items(), start=next_order):
        link = StreamOffer(
            offer_id=offer_id,
            offer_name=names.get(offer_id, f"Offer {offer_id}"),
            pinned=False,
            sort_order=order,
            conflict=False,
        )
        _set_published(link, OfferStatus.ACTIVE, share)  # добавлен в Keitaro (DISPUTED.md №6)
        if not first_load:
            link.keitaro_change = KeitaroChange.ADDED
        stream.offers.append(link)


def _merge(link: StreamOffer, status: OfferStatus, share: int) -> None:
    before_status, before_share = link.published_status, link.published_share
    if (status, share) == (before_status, before_share):
        return  # в Keitaro ничего не менялось — черновик (если есть) остаётся

    was_active = before_status is OfferStatus.ACTIVE
    if status is OfferStatus.REMOVED:
        link.keitaro_change = KeitaroChange.REMOVED
    elif was_active:
        link.keitaro_change = KeitaroChange.SHARE_CHANGED
    else:
        link.keitaro_change = KeitaroChange.ADDED
    link.keitaro_share_before = before_share if was_active else None

    if link.is_changed:  # и у нас черновик по этому офферу — конфликт
        link.conflict = True
        link.published_status, link.published_share = status, share
    else:
        _set_published(link, status, share)


def _set_published(link: StreamOffer, status: OfferStatus, share: int) -> None:
    link.status = link.published_status = status
    link.share = link.published_share = share
