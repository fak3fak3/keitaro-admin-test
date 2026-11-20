import json

import httpx
import pytest

from app.clients.keitaro import KeitaroError
from app.repositories.streams import StreamRepository
from app.services.errors import (
    OfferAlreadyInStreamError,
    OfferNotFoundError,
    OfferNotInStreamError,
    ShareError,
    StreamNotFoundError,
)
from app.services.offer_editor import OfferEditor

CAMPAIGN = 217109
GEO_STREAM = 1333642
OFFER_STREAM = 1333643

OFFERS = [
    {"id": 3749, "name": "Miaflow 0009"},
    {"id": 3717, "name": "Miaflow 0008"},
    {"id": 11111, "name": "FitoMishki"},
    {"id": 11112, "name": "Oxys"},
]


def kt_stream(stream_id, offers=(), name="Offers", position=2, type_="default"):
    """Поток в формате ответа Keitaro; offers — пары (offer_id, share)."""
    return {
        "id": stream_id,
        "campaign_id": CAMPAIGN,
        "name": name,
        "type": type_,
        "position": position,
        "schema": "landings" if offers else "redirect",
        "action_type": "http",
        "state": "active",
        "filters": [],
        "offers": [
            {"offer_id": offer_id, "share": share, "state": "active"} for offer_id, share in offers
        ],
    }


GEO = kt_stream(GEO_STREAM, name="Geo AU → Google", position=1, type_="regular")


def mock_keitaro(keitaro_api, streams, offers=OFFERS):
    keitaro_api.get(f"/campaigns/{CAMPAIGN}/streams").respond(json=streams)
    keitaro_api.get("/offers").respond(json=offers)


@pytest.fixture
def streams(db_session):
    return StreamRepository(db_session)


@pytest.fixture
def editor(keitaro, streams):
    return OfferEditor(keitaro, streams)


def offers_view(stream):
    """Компактный вид офферов потока для сравнения."""
    return [(o.offer_id, o.status.value, o.share, o.pinned) for o in stream.offers]


async def test_first_fetch_stores_streams_with_published_offers(editor, keitaro_api):
    mock_keitaro(
        keitaro_api,
        [GEO, kt_stream(OFFER_STREAM, [(3749, 33), (3717, 33), (99999, 34)])],
    )

    geo, offers = await editor.fetch(CAMPAIGN)

    assert (geo.keitaro_id, geo.name, geo.offers) == (GEO_STREAM, "Geo AU → Google", [])
    assert offers.keitaro_id == OFFER_STREAM
    assert offers_view(offers) == [
        (3749, "active", 33, False),
        (3717, "active", 33, False),
        (99999, "active", 34, False),
    ]
    assert [o.offer_name for o in offers.offers] == ["Miaflow 0009", "Miaflow 0008", "Offer 99999"]
    assert offers.has_draft is False


async def refetch(editor, keitaro_api, streams):
    """Повторный Fetch с новым ответом Keitaro (старые маршруты respx заменяются)."""
    keitaro_api.routes.clear()
    mock_keitaro(keitaro_api, streams)
    return await editor.fetch(CAMPAIGN)


async def test_refetch_marks_offers_deleted_in_keitaro_as_removed(editor, keitaro_api):
    four = [(3749, 25), (3717, 25), (11111, 25), (11112, 25)]
    mock_keitaro(keitaro_api, [GEO, kt_stream(OFFER_STREAM, four)])
    await editor.fetch(CAMPAIGN)

    # видео: в Keitaro руками удалили два оффера, остальные остались по 25%
    _, offers = await refetch(
        editor, keitaro_api, [GEO, kt_stream(OFFER_STREAM, [(3717, 25), (11112, 25)])]
    )

    assert offers_view(offers) == [
        (3749, "removed", 0, False),
        (3717, "active", 25, False),
        (11111, "removed", 0, False),
        (11112, "active", 25, False),
    ]
    assert offers.has_draft is False  # это состояние Keitaro, а не наш черновик


async def test_refetch_appends_offers_added_in_keitaro(editor, keitaro_api):
    mock_keitaro(keitaro_api, [kt_stream(OFFER_STREAM, [(3749, 100)])])
    await editor.fetch(CAMPAIGN)

    (offers,) = await refetch(
        editor, keitaro_api, [kt_stream(OFFER_STREAM, [(11112, 40), (3749, 60)])]
    )

    assert offers_view(offers) == [(3749, "active", 60, False), (11112, "active", 40, False)]
    assert offers.has_draft is False


async def test_refetch_updates_stream_and_drops_streams_deleted_in_keitaro(editor, keitaro_api):
    mock_keitaro(keitaro_api, [GEO, kt_stream(OFFER_STREAM, [(3749, 100)])])
    await editor.fetch(CAMPAIGN)

    streams = await refetch(
        editor, keitaro_api, [kt_stream(OFFER_STREAM, [(3749, 100)], name="Renamed", position=1)]
    )

    assert [(s.keitaro_id, s.name, s.position) for s in streams] == [(OFFER_STREAM, "Renamed", 1)]


async def fetched(editor, keitaro_api, offers):
    """Поток с офферами, загруженный в редактор и опубликованный (без черновика)."""
    mock_keitaro(keitaro_api, [kt_stream(OFFER_STREAM, offers)])
    (stream,) = await editor.fetch(CAMPAIGN)
    return stream


THREE = [(11111, 34), (3749, 33), (3717, 33)]


async def test_add_offer_rebalances_and_makes_draft(editor, keitaro_api):
    await fetched(editor, keitaro_api, THREE)

    stream = await editor.add_offer(OFFER_STREAM, 11112)

    assert offers_view(stream) == [
        (11111, "active", 25, False),
        (3749, "active", 25, False),
        (3717, "active", 25, False),
        (11112, "active", 25, False),
    ]
    assert stream.offers[-1].offer_name == "Oxys"
    assert stream.has_draft is True


async def test_add_unknown_offer_is_rejected(editor, keitaro_api):
    await fetched(editor, keitaro_api, THREE)

    with pytest.raises(OfferNotFoundError):
        await editor.add_offer(OFFER_STREAM, 424242)


async def test_add_offer_already_in_stream_is_rejected(editor, keitaro_api):
    await fetched(editor, keitaro_api, THREE)

    with pytest.raises(OfferAlreadyInStreamError):
        await editor.add_offer(OFFER_STREAM, 3749)


async def test_add_to_unknown_stream_is_rejected(editor):
    # поток проверяется по нашей БД до запросов в Keitaro
    with pytest.raises(StreamNotFoundError):
        await editor.add_offer(777, 3749)


FOUR = [(3749, 25), (3717, 25), (11111, 25), (11112, 25)]


async def test_remove_offer_zeroes_it_and_rebalances_others(editor, keitaro_api):
    await fetched(editor, keitaro_api, FOUR)

    stream = await editor.remove_offer(OFFER_STREAM, 3717)

    # видео: удалённый оффер серый с 0%, остальные пересчитаны
    assert offers_view(stream) == [
        (3749, "active", 34, False),
        (3717, "removed", 0, False),
        (11111, "active", 33, False),
        (11112, "active", 33, False),
    ]
    assert stream.has_draft is True


async def test_remove_last_active_offer_is_allowed(editor, keitaro_api):
    # DISPUTED.md №2
    await fetched(editor, keitaro_api, [(3749, 100)])

    stream = await editor.remove_offer(OFFER_STREAM, 3749)

    assert offers_view(stream) == [(3749, "removed", 0, False)]


async def test_bring_back_returns_removed_offer_and_rebalances(editor, keitaro_api):
    await fetched(editor, keitaro_api, FOUR)
    await editor.remove_offer(OFFER_STREAM, 3717)

    stream = await editor.bring_back(OFFER_STREAM, 3717)

    assert offers_view(stream) == [
        (3749, "active", 25, False),
        (3717, "active", 25, False),
        (11111, "active", 25, False),
        (11112, "active", 25, False),
    ]


@pytest.mark.parametrize("action", ["remove_offer", "bring_back"])
async def test_offer_not_in_stream_is_rejected(editor, keitaro_api, action):
    await fetched(editor, keitaro_api, FOUR)

    with pytest.raises(OfferNotInStreamError):
        await getattr(editor, action)(OFFER_STREAM, 424242)


async def test_remove_already_removed_and_bring_back_active_are_rejected(editor, keitaro_api):
    await fetched(editor, keitaro_api, FOUR)
    await editor.remove_offer(OFFER_STREAM, 3717)

    with pytest.raises(OfferNotInStreamError, match="уже удалён"):
        await editor.remove_offer(OFFER_STREAM, 3717)
    with pytest.raises(OfferNotInStreamError, match="не удалён"):
        await editor.bring_back(OFFER_STREAM, 3749)


async def test_pinned_share_survives_later_changes(editor, keitaro_api):
    await fetched(editor, keitaro_api, FOUR)

    stream = await editor.pin(OFFER_STREAM, 3717)
    assert offers_view(stream)[1] == (3717, "active", 25, True)
    assert stream.has_draft is False  # пин — только наша настройка

    stream = await editor.remove_offer(OFFER_STREAM, 11111)

    # видео: запиненные 25% остались, остальные 38/37
    assert offers_view(stream) == [
        (3749, "active", 38, False),
        (3717, "active", 25, True),
        (11111, "removed", 0, False),
        (11112, "active", 37, False),
    ]


async def test_unpin_returns_share_to_auto(editor, keitaro_api):
    await fetched(editor, keitaro_api, FOUR)
    await editor.set_share(OFFER_STREAM, 3749, 40)

    stream = await editor.unpin(OFFER_STREAM, 3749)

    assert [share for _, _, share, _ in offers_view(stream)] == [25, 25, 25, 25]
    assert not any(pinned for *_, pinned in offers_view(stream))


async def test_set_share_pins_value_and_rebalances_others(editor, keitaro_api):
    # DISPUTED.md №1: введённая доля закрепляется
    await fetched(editor, keitaro_api, FOUR)

    stream = await editor.set_share(OFFER_STREAM, 11111, 40)

    assert offers_view(stream) == [
        (3749, "active", 20, False),
        (3717, "active", 20, False),
        (11111, "active", 40, True),
        (11112, "active", 20, False),
    ]
    assert stream.has_draft is True


async def test_impossible_share_is_rejected_and_stream_is_unchanged(editor, keitaro_api):
    await fetched(editor, keitaro_api, [(3749, 50), (3717, 50)])

    with pytest.raises(ShareError):
        await editor.set_share(OFFER_STREAM, 3749, 100)

    stream = await editor.pin(OFFER_STREAM, 3717)  # перечитываем поток через любую операцию
    assert offers_view(stream) == [(3749, "active", 50, False), (3717, "active", 50, True)]


async def test_removing_last_unpinned_offer_with_pins_below_100_is_rejected(editor, keitaro_api):
    # DECISIONS.md №25: остаток некому отдать — сначала снимите пин
    await fetched(editor, keitaro_api, [(3749, 25), (3717, 75)])
    await editor.pin(OFFER_STREAM, 3749)

    with pytest.raises(ShareError, match="некому отдать"):
        await editor.remove_offer(OFFER_STREAM, 3717)

    stream = await editor.unpin(OFFER_STREAM, 3749)
    assert [status for _, status, _, _ in offers_view(stream)] == ["active", "active"]


@pytest.mark.parametrize("action", ["pin", "unpin"])
async def test_pin_removed_offer_is_rejected(editor, keitaro_api, action):
    await fetched(editor, keitaro_api, FOUR)
    await editor.remove_offer(OFFER_STREAM, 3717)

    with pytest.raises(OfferNotInStreamError, match="удалён"):
        await getattr(editor, action)(OFFER_STREAM, 3717)


def echo_offers(request):
    """PUT /streams/{id}: Keitaro отвечает потоком с отправленными офферами."""
    body = json.loads(request.content)
    offers = [(o["offer_id"], o["share"]) for o in body["offers"]]
    return httpx.Response(200, json=kt_stream(OFFER_STREAM, offers))


async def test_push_sends_active_offers_and_clears_draft(editor, keitaro_api):
    await fetched(editor, keitaro_api, FOUR)
    await editor.remove_offer(OFFER_STREAM, 3717)
    route = keitaro_api.put(f"/streams/{OFFER_STREAM}").mock(side_effect=echo_offers)

    stream = await editor.push(OFFER_STREAM)

    assert json.loads(route.calls.last.request.content) == {
        "offers": [
            {"offer_id": 3749, "share": 34, "state": "active"},
            {"offer_id": 11111, "share": 33, "state": "active"},
            {"offer_id": 11112, "share": 33, "state": "active"},
        ]
    }
    assert stream.has_draft is False
    # видео: после публикации удалённый оффер остаётся у нас в архиве (серым, с Bring back)
    assert offers_view(stream)[1] == (3717, "removed", 0, False)


async def test_failed_push_keeps_draft(editor, keitaro_api):
    await fetched(editor, keitaro_api, FOUR)
    await editor.remove_offer(OFFER_STREAM, 3717)
    keitaro_api.put(f"/streams/{OFFER_STREAM}").respond(status_code=500, json={"error": "boom"})

    with pytest.raises(KeitaroError):
        await editor.push(OFFER_STREAM)

    stream = await editor.pin(OFFER_STREAM, 3749)
    assert stream.has_draft is True


async def test_push_forgets_offer_added_and_removed_before_publish(editor, keitaro_api):
    await fetched(editor, keitaro_api, THREE)
    await editor.add_offer(OFFER_STREAM, 11112)
    await editor.remove_offer(OFFER_STREAM, 11112)
    keitaro_api.put(f"/streams/{OFFER_STREAM}").mock(side_effect=echo_offers)

    stream = await editor.push(OFFER_STREAM)

    assert [o.offer_id for o in stream.offers] == [11111, 3749, 3717]


async def test_cancel_drops_unpublished_offers_and_restores_published(editor, keitaro_api):
    await fetched(editor, keitaro_api, THREE)
    await editor.add_offer(OFFER_STREAM, 11112)
    await editor.remove_offer(OFFER_STREAM, 3749)

    stream = await editor.cancel(OFFER_STREAM)

    # видео: добавленные до публикации офферы удаляются, поток снова белый
    assert offers_view(stream) == [
        (11111, "active", 34, False),
        (3749, "active", 33, False),
        (3717, "active", 33, False),
    ]
    assert stream.has_draft is False


async def test_cancel_keeps_pins(editor, keitaro_api):
    await fetched(editor, keitaro_api, THREE)
    await editor.pin(OFFER_STREAM, 3717)
    await editor.remove_offer(OFFER_STREAM, 3749)

    stream = await editor.cancel(OFFER_STREAM)

    assert offers_view(stream)[2] == (3717, "active", 33, True)
