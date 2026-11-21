"""Live-обновление редактора: пока открыта страница кампании, бэкенд опрашивает Keitaro."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Literal

from app.clients.keitaro import KeitaroClient, KeitaroError
from app.models.stream import Stream
from app.services.offer_editor import OfferEditor

EditorSession = Callable[[], AbstractAsyncContextManager[OfferEditor]]


@dataclass(frozen=True)
class LiveEvent:
    kind: Literal["streams", "error"]
    streams: list[Stream] = field(default_factory=list)
    detail: str | None = None


@dataclass
class _Watch:
    task: asyncio.Task[None] | None = None
    subscribers: set[asyncio.Queue[LiveEvent | None]] = field(default_factory=set)
    snapshot: list[dict] | None = None  # потоки Keitaro на прошлом шаге опроса
    last: LiveEvent | None = None  # новый подписчик сразу получает текущее состояние

    def publish(self, event: LiveEvent) -> None:
        self.last = event
        for events in self.subscribers:
            events.put_nowait(event)


class LiveStreams:
    """Одна фоновая задача опроса на кампанию, пока есть хотя бы один подписчик."""

    def __init__(
        self,
        keitaro: KeitaroClient,
        editor_session: EditorSession,
        lock: asyncio.Lock,
        *,
        interval: float,
    ) -> None:
        self._keitaro = keitaro
        self._editor_session = editor_session
        self._lock = lock  # общий с действиями редактора: слияние не пересекается с ними
        self._interval = interval
        self._watches: dict[int, _Watch] = {}

    @asynccontextmanager
    async def subscribe(self, campaign_id: int) -> AsyncIterator[asyncio.Queue[LiveEvent | None]]:
        events: asyncio.Queue[LiveEvent | None] = asyncio.Queue()
        watch = self._watches.setdefault(campaign_id, _Watch())
        watch.subscribers.add(events)
        if watch.last is not None:
            events.put_nowait(watch.last)
        if watch.task is None:
            watch.task = asyncio.create_task(self._poll(campaign_id, watch))
        try:
            yield events
        finally:
            watch.subscribers.discard(events)
            if not watch.subscribers:  # ушёл последний — опрос этой кампании больше не нужен
                watch.task.cancel()
                self._watches.pop(campaign_id, None)

    async def close(self) -> None:
        """Остановка приложения: прекратить опросы и закрыть подписки (`None` в очереди)."""
        watches, self._watches = list(self._watches.values()), {}
        for watch in watches:
            if watch.task is not None:
                watch.task.cancel()
        await asyncio.gather(*(w.task for w in watches if w.task), return_exceptions=True)
        for watch in watches:
            for events in watch.subscribers:
                events.put_nowait(None)

    async def _poll(self, campaign_id: int, watch: _Watch) -> None:
        while True:
            try:
                await self._tick(campaign_id, watch)
            except KeitaroError as exc:
                watch.snapshot = None  # после восстановления — снова слияние и событие с потоками
                if watch.last != LiveEvent("error", detail=str(exc)):
                    watch.publish(LiveEvent("error", detail=str(exc)))
            await asyncio.sleep(self._interval)

    async def _tick(self, campaign_id: int, watch: _Watch) -> None:
        # Раз в интервал — один лёгкий запрос; слияние (ещё 2 запроса и запись в БД) — только
        # если в Keitaro что-то поменялось.
        kt_streams = await self._keitaro.get_campaign_streams(campaign_id)
        snapshot = [stream.model_dump() for stream in kt_streams]
        if snapshot == watch.snapshot:
            return
        async with self._lock, self._editor_session() as editor:
            streams = await editor.fetch(campaign_id)
        watch.snapshot = snapshot
        watch.publish(LiveEvent("streams", streams))
