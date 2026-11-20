import json

from tests.services.test_offer_editor import (
    CAMPAIGN,
    GEO,
    GEO_STREAM,
    OFFER_STREAM,
    OFFERS,
    echo_offers,
    keitaro_now,
    kt_stream,
    mock_keitaro,
)


async def test_fetch_returns_campaign_streams_with_offers(api, keitaro_api):
    mock_keitaro(keitaro_api, [GEO, kt_stream(OFFER_STREAM, [(3749, 60), (3717, 40)])])

    response = await api.post(f"/api/campaigns/{CAMPAIGN}/fetch")

    assert response.status_code == 200
    geo, offers = response.json()
    assert geo == {
        "id": GEO_STREAM,
        "campaign_id": CAMPAIGN,
        "name": "Geo AU → Google",
        "type": "regular",
        "position": 1,
        "has_draft": False,
        "has_conflicts": False,
        "offers": [],
    }
    assert offers["offers"][0] == {
        "offer_id": 3749,
        "offer_name": "Miaflow 0009",
        "status": "active",
        "share": 60,
        "pinned": False,
        "changed": False,
        "published_status": "active",
        "published_share": 60,
        "keitaro_change": None,
        "keitaro_share_before": None,
        "conflict": False,
    }
    assert [o["offer_id"] for o in offers["offers"]] == [3749, 3717]


async def fetch(api, keitaro_api, offers):
    """Fetch кампании с одним потоком офферов; после него моки Keitaro сброшены."""
    mock_keitaro(keitaro_api, [kt_stream(OFFER_STREAM, offers)])
    response = await api.post(f"/api/campaigns/{CAMPAIGN}/fetch")
    assert response.status_code == 200
    keitaro_api.routes.clear()


def shares(stream):
    return [(o["offer_id"], o["status"], o["share"], o["pinned"]) for o in stream["offers"]]


async def test_streams_are_read_from_our_db_without_keitaro(api, keitaro_api):
    await fetch(api, keitaro_api, [(3749, 100)])

    response = await api.get(f"/api/campaigns/{CAMPAIGN}/streams")

    assert response.status_code == 200
    assert [shares(s) for s in response.json()] == [[(3749, "active", 100, False)]]


async def test_streams_of_not_fetched_campaign_are_empty(api):
    response = await api.get(f"/api/campaigns/{CAMPAIGN}/streams")

    assert response.json() == []


async def test_add_offer_rebalances_stream(api, keitaro_api):
    await fetch(api, keitaro_api, [(3749, 100)])
    keitaro_api.get("/offers").respond(json=OFFERS)

    response = await api.post(f"/api/streams/{OFFER_STREAM}/offers", json={"offer_id": 3717})

    assert response.status_code == 200
    assert shares(response.json()) == [(3749, "active", 50, False), (3717, "active", 50, False)]
    assert response.json()["has_draft"] is True


def offer_url(offer_id, action):
    return f"/api/streams/{OFFER_STREAM}/offers/{offer_id}/{action}"


async def test_remove_and_bring_back_offer(api, keitaro_api):
    await fetch(api, keitaro_api, [(3749, 50), (3717, 50)])

    removed = await api.post(offer_url(3717, "remove"))
    back = await api.post(offer_url(3717, "bring-back"))

    assert removed.status_code == 200
    assert shares(removed.json()) == [(3749, "active", 100, False), (3717, "removed", 0, False)]
    assert shares(back.json()) == [(3749, "active", 50, False), (3717, "active", 50, False)]


THREE = [(3749, 34), (3717, 33), (11111, 33)]


async def test_pin_and_unpin_offer(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)

    pinned = await api.post(offer_url(3717, "pin"))
    unpinned = await api.post(offer_url(3717, "unpin"))

    assert pinned.status_code == 200
    assert shares(pinned.json())[1] == (3717, "active", 33, True)
    assert shares(unpinned.json())[1] == (3717, "active", 33, False)


async def test_set_share_pins_it_and_rebalances_others(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)

    response = await api.put(offer_url(3717, "share"), json={"share": 50})

    assert response.status_code == 200
    assert shares(response.json()) == [
        (3749, "active", 25, False),
        (3717, "active", 50, True),
        (11111, "active", 25, False),
    ]


async def test_share_outside_0_100_is_rejected_with_422(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)

    response = await api.put(offer_url(3717, "share"), json={"share": 101})

    assert response.status_code == 422


STREAM_URL = f"/api/streams/{OFFER_STREAM}"


async def test_push_publishes_draft(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)
    await api.post(offer_url(3717, "remove"))
    keitaro_now(keitaro_api, THREE)
    route = keitaro_api.put(f"/streams/{OFFER_STREAM}").mock(side_effect=echo_offers)

    response = await api.post(f"{STREAM_URL}/push")

    assert response.status_code == 200
    sent = json.loads(route.calls.last.request.content)["offers"]
    assert [(o["offer_id"], o["share"]) for o in sent] == [(3749, 50), (11111, 50)]
    assert response.json()["has_draft"] is False


async def test_cancel_restores_published_state(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)
    await api.post(offer_url(3717, "remove"))

    response = await api.post(f"{STREAM_URL}/cancel")

    assert response.status_code == 200
    assert shares(response.json()) == [
        (3749, "active", 34, False),
        (3717, "active", 33, False),
        (11111, "active", 33, False),
    ]


async def conflict(api, keitaro_api):
    """Черновик: удалили 3717 (3749 → 50%). В Keitaro тем временем 3749: 34 → 60.

    Конфликт по 3749: изменён и у нас, и в Keitaro.
    """
    await fetch(api, keitaro_api, THREE)
    await api.post(offer_url(3717, "remove"))
    await fetch(api, keitaro_api, [(3749, 60), (3717, 33), (11111, 33)])


async def test_conflicts_are_shown_and_resolved_per_offer(api, keitaro_api):
    await conflict(api, keitaro_api)
    (stream,) = (await api.get(f"/api/campaigns/{CAMPAIGN}/streams")).json()
    offer = stream["offers"][0]
    assert stream["has_conflicts"] is True
    assert (offer["conflict"], offer["keitaro_change"], offer["keitaro_share_before"]) == (
        True,
        "share_changed",
        34,
    )

    response = await api.post(offer_url(3749, "resolve"), json={"keep": "keitaro"})

    assert response.status_code == 200
    assert response.json()["has_conflicts"] is False
    assert shares(response.json()) == [
        (3749, "active", 60, False),
        (3717, "removed", 0, False),
        (11111, "active", 40, False),
    ]


async def test_resolve_all_keeps_mine(api, keitaro_api):
    await conflict(api, keitaro_api)

    response = await api.post(f"{STREAM_URL}/resolve", json={"keep": "mine"})

    assert response.status_code == 200
    assert response.json()["has_conflicts"] is False
    assert shares(response.json())[0] == (3749, "active", 50, False)


async def test_unknown_keep_value_is_rejected_with_422(api, keitaro_api):
    await conflict(api, keitaro_api)

    response = await api.post(offer_url(3749, "resolve"), json={"keep": "theirs"})

    assert response.status_code == 422


async def test_acknowledge_clears_marks_but_keeps_conflicts(api, keitaro_api):
    await conflict(api, keitaro_api)

    response = await api.post(f"{STREAM_URL}/acknowledge")

    assert response.status_code == 200
    offer = response.json()["offers"][0]
    assert (offer["keitaro_change"], offer["conflict"]) == (None, True)


async def test_not_fetched_stream_returns_404_with_hint(api):
    response = await api.post("/api/streams/1/cancel")

    assert response.status_code == 404
    assert "сначала Fetch streams from KT" in response.json()["detail"]


async def test_offer_not_in_stream_returns_404(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)

    response = await api.post(offer_url(11112, "pin"))

    assert response.status_code == 404


async def test_action_not_allowed_in_offer_state_returns_409(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)
    await api.post(offer_url(3717, "remove"))

    response = await api.post(offer_url(3717, "remove"))

    assert response.status_code == 409
    assert response.json() == {"detail": "Оффер 3717 уже удалён из потока"}


async def test_adding_offer_already_in_stream_returns_409(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)

    response = await api.post(f"{STREAM_URL}/offers", json={"offer_id": 3717})

    assert response.status_code == 409


async def test_resolving_offer_without_conflict_returns_409(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)

    response = await api.post(offer_url(3717, "resolve"), json={"keep": "mine"})

    assert response.status_code == 409


async def test_push_with_pending_conflicts_returns_409_without_calling_keitaro(api, keitaro_api):
    await conflict(api, keitaro_api)  # моков Keitaro нет: любой запрос к нему уронит тест

    response = await api.post(f"{STREAM_URL}/push")

    assert response.status_code == 409
    assert "3749" in response.json()["detail"]


async def test_push_when_keitaro_changed_after_fetch_returns_409(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)
    await api.post(offer_url(3717, "remove"))
    keitaro_now(keitaro_api, [(3749, 100)])  # кто-то поменял поток в Keitaro

    response = await api.post(f"{STREAM_URL}/push")

    assert response.status_code == 409
    assert "Fetch" in response.json()["detail"]


async def test_impossible_share_returns_400_and_keeps_stream(api, keitaro_api):
    await fetch(api, keitaro_api, THREE)

    response = await api.put(offer_url(3717, "share"), json={"share": 100})
    (stream,) = (await api.get(f"/api/campaigns/{CAMPAIGN}/streams")).json()

    assert response.status_code == 400
    assert stream["has_draft"] is False
