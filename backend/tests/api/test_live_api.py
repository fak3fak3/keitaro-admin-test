import asyncio
import json
from contextlib import asynccontextmanager

from app.api import deps
from app.models.stream import OfferStatus, Stream, StreamOffer
from app.services.live import LiveEvent

CAMPAIGN = 217109


class FakeLive:
    """Отдаёт заранее заданные события и закрывает подписку (как при остановке приложения)."""

    def __init__(self, *events):
        self.events = events
        self.subscribed: list[int] = []

    @asynccontextmanager
    async def subscribe(self, campaign_id):
        self.subscribed.append(campaign_id)
        queue = asyncio.Queue()
        for event in [*self.events, None]:
            queue.put_nowait(event)
        yield queue


def offers_stream():
    link = StreamOffer(
        offer_id=3749,
        offer_name="Miaflow",
        status=OfferStatus.ACTIVE,
        share=100,
        pinned=False,
        sort_order=0,
        published_status=OfferStatus.ACTIVE,
        published_share=100,
        conflict=False,
    )
    return Stream(
        keitaro_id=1333643,
        campaign_id=CAMPAIGN,
        name="Offers",
        position=2,
        type="default",
        offers=[link],
    )


def parse_sse(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1) for line in block.splitlines() if not line.startswith(":")
        )
        events.append((fields.get("event"), json.loads(fields["data"])))
    return events


async def test_live_streams_events_until_closed(api):
    live = FakeLive(
        LiveEvent("streams", [offers_stream()]),
        LiveEvent("error", detail="Keitaro API error (401): Invalid API key"),
    )
    api._transport.app.dependency_overrides[deps.get_live] = lambda: live

    response = await api.get(f"/api/campaigns/{CAMPAIGN}/live")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    (kind, streams), error = parse_sse(response.text)
    assert kind == "streams"
    assert streams[0]["id"] == 1333643
    assert streams[0]["offers"][0]["share"] == 100
    assert error == ("keitaro_error", {"detail": "Keitaro API error (401): Invalid API key"})
    assert live.subscribed == [CAMPAIGN]
