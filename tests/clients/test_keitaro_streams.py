import json

from app.clients.keitaro.schemas import StreamCreate, StreamFilter, StreamOffer

GEO_STREAM = {
    "id": 564220,
    "campaign_id": 93212,
    "name": "Flow 1",
    "type": "forced",
    "position": 1,
    "schema": "redirect",
    "action_type": "http",
    "action_payload": "https://google.com",
    "state": "active",
    "filters": [
        {"id": 1, "stream_id": 564220, "name": "country", "mode": "accept", "payload": ["AU"]}
    ],
    "offers": [],
}

OFFER_STREAM = {
    "id": 564221,
    "campaign_id": 93212,
    "name": "Flow 2",
    "type": "regular",
    "position": 2,
    "schema": "landings",
    "action_type": "http",
    "action_payload": None,
    "state": "active",
    "filters": [],
    "offers": [
        {"id": 11, "stream_id": 564221, "offer_id": 3749, "share": 33, "state": "active"},
        {"id": 12, "stream_id": 564221, "offer_id": 3717, "share": 33, "state": "active"},
        {"id": 13, "stream_id": 564221, "offer_id": 11111, "share": 34, "state": "active"},
    ],
}


async def test_get_campaign_streams_parses_streams_with_offers(keitaro, keitaro_api):
    keitaro_api.get("/campaigns/93212/streams").respond(json=[GEO_STREAM, OFFER_STREAM])

    streams = await keitaro.get_campaign_streams(93212)

    geo, offers = streams
    assert (geo.id, geo.name, geo.type, geo.schema_) == (564220, "Flow 1", "forced", "redirect")
    assert geo.offers == []
    assert offers.id == 564221
    assert [(o.offer_id, o.share, o.state) for o in offers.offers] == [
        (3749, 33, "active"),
        (3717, 33, "active"),
        (11111, 34, "active"),
    ]


async def test_create_stream_posts_redirect_stream_with_country_filter(keitaro, keitaro_api):
    route = keitaro_api.post("/streams").respond(json=GEO_STREAM)

    stream = await keitaro.create_stream(
        StreamCreate(
            campaign_id=93212,
            name="Flow 1",
            type="forced",
            position=1,
            schema="redirect",
            action_type="http",
            action_payload="https://google.com",
            filters=[StreamFilter(name="country", mode="accept", payload=["AU"])],
        )
    )

    assert json.loads(route.calls.last.request.content) == {
        "campaign_id": 93212,
        "name": "Flow 1",
        "type": "forced",
        "position": 1,
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://google.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["AU"]}],
        "offers": [],
    }
    assert stream.id == 564220


async def test_update_stream_offers_puts_full_offer_list(keitaro, keitaro_api):
    updated = {
        **OFFER_STREAM,
        "offers": [
            {"id": 11, "offer_id": 3749, "share": 50, "state": "active"},
            {"id": 14, "offer_id": 11112, "share": 50, "state": "active"},
        ],
    }
    route = keitaro_api.put("/streams/564221").respond(json=updated)

    stream = await keitaro.update_stream_offers(
        564221,
        [StreamOffer(offer_id=3749, share=50), StreamOffer(offer_id=11112, share=50)],
    )

    assert json.loads(route.calls.last.request.content) == {
        "offers": [
            {"offer_id": 3749, "share": 50, "state": "active"},
            {"offer_id": 11112, "share": 50, "state": "active"},
        ]
    }
    assert [(o.offer_id, o.share) for o in stream.offers] == [(3749, 50), (11112, 50)]


# Форма ответа снята с живого Keitaro (GET /campaigns/{id}/streams), данные обезличены.
# Отличия от спецификации: payload фильтра — массив (в спеке string), есть weight,
# offer_selection, created_at; action_options = null; у потока с офферами action_payload = "".
LIVE_STREAMS_RESPONSE = [
    {
        "id": 1,
        "type": "regular",
        "name": "Google (MX)",
        "campaign_id": 10,
        "position": 1,
        "action_options": None,
        "state": "active",
        "created_at": "2026-11-20 10:54:46",
        "action_type": "http",
        "action_payload": "https://www.google.com",
        "schema": "redirect",
        "collect_clicks": True,
        "filter_or": False,
        "weight": 0,
        "offer_selection": "before_click",
        "filters": [
            {
                "id": 5,
                "stream_id": 1,
                "name": "country",
                "mode": "accept",
                "payload": ["MX"],
                "oid": 5,
            }
        ],
        "offers": [],
    },
    {
        "id": 2,
        "type": "default",
        "name": "Offers",
        "campaign_id": 10,
        "position": 2,
        "action_options": None,
        "state": "active",
        "created_at": "2026-11-20 10:54:46",
        "action_type": "http",
        "action_payload": "",
        "schema": "landings",
        "collect_clicks": True,
        "filter_or": False,
        "weight": 0,
        "offer_selection": "before_click",
        "filters": [],
        "offers": [
            {
                "id": 7,
                "stream_id": 2,
                "offer_id": 18813,
                "state": "active",
                "share": 100,
                "created_at": "2026-11-20 10:54:46",
                "updated_at": "2026-11-20 10:54:46",
            }
        ],
    },
]


async def test_parses_live_keitaro_stream_response(keitaro, keitaro_api):
    keitaro_api.get("/campaigns/10/streams").respond(json=LIVE_STREAMS_RESPONSE)

    geo, offers = await keitaro.get_campaign_streams(10)

    assert geo.schema_ == "redirect"
    assert geo.filters[0].payload == ["MX"]
    assert offers.schema_ == "landings"
    assert [(o.offer_id, o.share) for o in offers.offers] == [(18813, 100)]


async def test_get_stream_returns_single_stream(keitaro, keitaro_api):
    keitaro_api.get("/streams/564221").respond(json=OFFER_STREAM)

    stream = await keitaro.get_stream(564221)

    assert stream.id == 564221
    assert [(o.offer_id, o.share) for o in stream.offers] == [(3749, 33), (3717, 33), (11111, 34)]
