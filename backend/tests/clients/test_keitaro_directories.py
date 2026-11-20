from tests.conftest import TOKEN


async def test_list_domains_sends_api_key_and_parses_domains(keitaro, keitaro_api):
    route = keitaro_api.get("/domains").respond(
        json=[{"id": 1, "name": "in.posdk.xyz", "state": "active", "group_id": None}]
    )

    domains = await keitaro.list_domains()

    assert route.calls.last.request.headers["Api-Key"] == TOKEN
    assert [(d.id, d.name) for d in domains] == [(1, "in.posdk.xyz")]


async def test_list_campaign_groups_requests_campaign_type(keitaro, keitaro_api):
    route = keitaro_api.get("/groups", params={"type": "campaigns"}).respond(
        json=[{"id": 7, "name": "FORTESTS", "position": 1, "type": "campaigns"}]
    )

    groups = await keitaro.list_campaign_groups()

    assert route.called
    assert [(g.id, g.name) for g in groups] == [(7, "FORTESTS")]


async def test_list_traffic_sources(keitaro, keitaro_api):
    keitaro_api.get("/traffic_sources").respond(
        json=[{"id": 3, "name": "FORTESTS", "state": "active"}]
    )

    sources = await keitaro.list_traffic_sources()

    assert [(s.id, s.name) for s in sources] == [(3, "FORTESTS")]


async def test_list_offers(keitaro, keitaro_api):
    keitaro_api.get("/offers").respond(
        json=[
            {"id": 3749, "name": "Miaflow [BEAUTY-RO-BE_0009]", "state": "active"},
            {"id": 3717, "name": "Miaflow [BEAUTY-RO-BE_0008]", "state": "active"},
        ]
    )

    offers = await keitaro.list_offers()

    assert [(o.id, o.name) for o in offers] == [
        (3749, "Miaflow [BEAUTY-RO-BE_0009]"),
        (3717, "Miaflow [BEAUTY-RO-BE_0008]"),
    ]
