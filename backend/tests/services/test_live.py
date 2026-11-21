import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest

from app.repositories.streams import StreamRepository
from app.services.live import LiveStreams
from app.services.offer_editor import OfferEditor
from tests.services.test_offer_editor import CAMPAIGN, OFFER_STREAM, OFFERS, kt_stream

INTERVAL = 0.01
WAIT = 1.0


class Keitaro:
    """Что сейчас лежит в Keitaro: тест меняет `offers`, опрос это видит."""

    def __init__(self, keitaro_api, offers):
        self.offers = offers
        self.down = False
        self.streams_route = keitaro_api.get(f"/campaigns/{CAMPAIGN}/streams").mock(
            side_effect=lambda request: self._streams()
        )
        keitaro_api.get("/offers").respond(json=OFFERS)

    def _streams(self):
        if self.down:
            return httpx.Response(401, json={"error": "Invalid API key"})
        return httpx.Response(200, json=[kt_stream(OFFER_STREAM, self.offers)])


@pytest.fixture
def lock():
    return asyncio.Lock()


@pytest.fixture
def live(keitaro, db_session, lock):
    @asynccontextmanager
    async def editor_session():
        yield OfferEditor(keitaro, StreamRepository(db_session))
        await db_session.flush()

    return LiveStreams(keitaro, editor_session, lock, interval=INTERVAL)


def shares(event):
    (stream,) = event.streams
    return [(o.offer_id, o.status.value, o.share) for o in stream.offers]


async def test_subscriber_first_gets_current_streams_from_keitaro(live, keitaro_api):
    Keitaro(keitaro_api, [(3749, 60), (3717, 40)])

    async with live.subscribe(CAMPAIGN) as events:
        event = await asyncio.wait_for(events.get(), WAIT)

    assert event.kind == "streams"
    assert shares(event) == [(3749, "active", 60), (3717, "active", 40)]


async def test_event_only_when_keitaro_changed(live, keitaro_api):
    keitaro = Keitaro(keitaro_api, [(3749, 60), (3717, 40)])

    async with live.subscribe(CAMPAIGN) as events:
        await asyncio.wait_for(events.get(), WAIT)
        calls = keitaro.streams_route.call_count
        await asyncio.sleep(INTERVAL * 10)
        assert keitaro.streams_route.call_count > calls  # опрос идёт
        assert events.empty()  # но без изменений событий нет

        keitaro.offers = [(3749, 50), (3717, 50)]  # кто-то поменял доли в Keitaro
        event = await asyncio.wait_for(events.get(), WAIT)

    assert shares(event) == [(3749, "active", 50), (3717, "active", 50)]
    assert [o.keitaro_change.value for o in event.streams[0].offers] == ["share_changed"] * 2


async def test_polling_stops_when_last_subscriber_leaves(live, keitaro_api):
    keitaro = Keitaro(keitaro_api, [(3749, 100)])

    async with live.subscribe(CAMPAIGN) as events:
        await asyncio.wait_for(events.get(), WAIT)
    await asyncio.sleep(INTERVAL * 3)  # дать опросу завершиться
    calls = keitaro.streams_route.call_count
    await asyncio.sleep(INTERVAL * 10)

    assert keitaro.streams_route.call_count == calls


async def test_second_subscriber_shares_polling_and_gets_current_state(live, keitaro_api):
    keitaro = Keitaro(keitaro_api, [(3749, 100)])

    async with live.subscribe(CAMPAIGN) as first:
        await asyncio.wait_for(first.get(), WAIT)
        async with live.subscribe(CAMPAIGN) as second:
            event = await asyncio.wait_for(second.get(), WAIT)
            calls = keitaro.streams_route.call_count
            await asyncio.sleep(INTERVAL * 10)
            polled = keitaro.streams_route.call_count - calls

    assert shares(event) == [(3749, "active", 100)]
    assert polled <= 11  # один опрос на кампанию, а не по одному на подписчика


async def test_keitaro_error_is_reported_once_and_polling_recovers(live, keitaro_api):
    keitaro = Keitaro(keitaro_api, [(3749, 100)])

    async with live.subscribe(CAMPAIGN) as events:
        await asyncio.wait_for(events.get(), WAIT)
        keitaro.down = True
        error = await asyncio.wait_for(events.get(), WAIT)
        await asyncio.sleep(INTERVAL * 10)
        assert events.empty()  # одна и та же ошибка не сыплется на каждом шаге

        keitaro.down = False
        recovered = await asyncio.wait_for(events.get(), WAIT)

    assert (error.kind, error.detail) == ("error", "Keitaro API error (401): Invalid API key")
    assert recovered.kind == "streams"


async def test_merge_waits_for_editor_action_holding_the_lock(live, keitaro_api, lock):
    Keitaro(keitaro_api, [(3749, 100)])

    async with lock:  # идёт действие пользователя в редакторе
        async with live.subscribe(CAMPAIGN) as events:
            await asyncio.sleep(INTERVAL * 10)
            assert events.empty()
    # здесь опрос уже остановлен; проверяем, что после освобождения слияние проходит
    async with live.subscribe(CAMPAIGN) as events:
        event = await asyncio.wait_for(events.get(), WAIT)

    assert event.kind == "streams"


async def test_close_ends_subscriptions_and_stops_polling(live, keitaro_api):
    keitaro = Keitaro(keitaro_api, [(3749, 100)])

    async with live.subscribe(CAMPAIGN) as events:
        await asyncio.wait_for(events.get(), WAIT)
        await live.close()
        closed = await asyncio.wait_for(events.get(), WAIT)
        calls = keitaro.streams_route.call_count
        await asyncio.sleep(INTERVAL * 10)

    assert closed is None  # сигнал подписчику: соединение закрывается
    assert keitaro.streams_route.call_count == calls
