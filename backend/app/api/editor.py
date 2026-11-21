"""Часть 2 ТЗ: редактор офферов в потоках кампании. Поток адресуется своим id в Keitaro."""

from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import EditorDep, LiveDep
from app.models.stream import KeitaroChange, OfferStatus, Stream
from app.services.offer_editor import Keep

router = APIRouter(tags=["editor"])


class StreamOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: int
    offer_name: str
    status: OfferStatus
    share: int
    pinned: bool
    changed: bool = Field(validation_alias="is_changed")
    published_status: OfferStatus | None
    published_share: int | None
    keitaro_change: KeitaroChange | None
    keitaro_share_before: int | None
    conflict: bool


class StreamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(validation_alias="keitaro_id")
    campaign_id: int
    name: str
    type: str
    position: int | None
    has_draft: bool
    has_conflicts: bool
    offers: list[StreamOfferOut]


class AddOfferIn(BaseModel):
    offer_id: int = Field(gt=0)


class ShareIn(BaseModel):
    share: int = Field(ge=0, le=100)


class ResolveIn(BaseModel):
    keep: Keep  # "mine" — оставить черновик, "keitaro" — взять значение из Keitaro


def _out(stream: Stream) -> StreamOut:
    return StreamOut.model_validate(stream)


@router.post("/campaigns/{campaign_id}/fetch")
async def fetch_streams(campaign_id: int, editor: EditorDep) -> list[StreamOut]:
    """Fetch streams from KT: загрузить потоки кампании из Keitaro (слияние с черновиком)."""
    return [_out(stream) for stream in await editor.fetch(campaign_id)]


@router.get("/campaigns/{campaign_id}/streams")
async def list_streams(campaign_id: int, editor: EditorDep) -> list[StreamOut]:
    """Потоки кампании в редакторе (из нашей БД). Пусто — кампанию ещё не загружали (Fetch)."""
    return [_out(stream) for stream in await editor.list_streams(campaign_id)]


@router.post("/streams/{stream_id}/offers")
async def add_offer(stream_id: int, body: AddOfferIn, editor: EditorDep) -> StreamOut:
    """Add: добавить оффер в черновик потока, доли пересчитываются."""
    return _out(await editor.add_offer(stream_id, body.offer_id))


@router.post("/streams/{stream_id}/offers/{offer_id}/remove")
async def remove_offer(stream_id: int, offer_id: int, editor: EditorDep) -> StreamOut:
    """Remove: оффер остаётся в потоке серым (removed, 0%), остальные пересчитываются."""
    return _out(await editor.remove_offer(stream_id, offer_id))


@router.post("/streams/{stream_id}/offers/{offer_id}/bring-back")
async def bring_back(stream_id: int, offer_id: int, editor: EditorDep) -> StreamOut:
    """Bring back: вернуть удалённый оффер."""
    return _out(await editor.bring_back(stream_id, offer_id))


@router.post("/streams/{stream_id}/offers/{offer_id}/pin")
async def pin(stream_id: int, offer_id: int, editor: EditorDep) -> StreamOut:
    """Закрепить текущую долю оффера."""
    return _out(await editor.pin(stream_id, offer_id))


@router.post("/streams/{stream_id}/offers/{offer_id}/unpin")
async def unpin(stream_id: int, offer_id: int, editor: EditorDep) -> StreamOut:
    """Снять пин: доля снова считается автоматически."""
    return _out(await editor.unpin(stream_id, offer_id))


@router.put("/streams/{stream_id}/offers/{offer_id}/share")
async def set_share(stream_id: int, offer_id: int, body: ShareIn, editor: EditorDep) -> StreamOut:
    """Задать долю вручную: она закрепляется, остальные пересчитываются (DISPUTED.md №1)."""
    return _out(await editor.set_share(stream_id, offer_id, body.share))


@router.post("/streams/{stream_id}/push")
async def push(stream_id: int, editor: EditorDep) -> StreamOut:
    """Push to KT: опубликовать черновик. 409 — конфликты не решены или Keitaro изменился."""
    return _out(await editor.push(stream_id))


@router.post("/streams/{stream_id}/cancel")
async def cancel(stream_id: int, editor: EditorDep) -> StreamOut:
    """Cancel: отменить черновик, вернуть опубликованное состояние."""
    return _out(await editor.cancel(stream_id))


@router.post("/streams/{stream_id}/offers/{offer_id}/resolve")
async def resolve(stream_id: int, offer_id: int, body: ResolveIn, editor: EditorDep) -> StreamOut:
    """Решить конфликт одного оффера с Keitaro (DISPUTED.md №8)."""
    return _out(await editor.resolve(stream_id, offer_id, body.keep))


@router.post("/streams/{stream_id}/resolve")
async def resolve_all(stream_id: int, body: ResolveIn, editor: EditorDep) -> StreamOut:
    """Решить все конфликты потока одинаково: «всё моё» или «всё из Keitaro»."""
    return _out(await editor.resolve_all(stream_id, body.keep))


@router.post("/streams/{stream_id}/acknowledge")
async def acknowledge(stream_id: int, editor: EditorDep) -> StreamOut:
    """«Понятно»: снять пометки об изменениях в Keitaro. Конфликты остаются."""
    return _out(await editor.acknowledge(stream_id))


@router.get("/campaigns/{campaign_id}/live", response_class=EventSourceResponse)
async def live_streams(campaign_id: int, live: LiveDep) -> AsyncIterator[ServerSentEvent]:
    """Live-обновление редактора (SSE): пока соединение открыто, бэкенд опрашивает Keitaro.

    События: `streams` — потоки после слияния, когда в Keitaro что-то изменилось;
    `keitaro_error` — Keitaro ответил ошибкой (опрос продолжается).
    """
    async with live.subscribe(campaign_id) as events:
        while (event := await events.get()) is not None:  # None — приложение останавливается
            if event.kind == "streams":
                data = [_out(stream).model_dump(mode="json") for stream in event.streams]
                yield ServerSentEvent(event="streams", data=data)
            else:
                # не "error": в браузере это имя занято сетевыми ошибками EventSource (onerror)
                yield ServerSentEvent(event="keitaro_error", data={"detail": event.detail})
