import json

import httpx
import pytest

from app.clients.keitaro import KeitaroError
from app.repositories.campaigns import CampaignRepository
from app.schemas.campaign import CampaignCreateRequest
from app.services.campaign_creator import (
    CampaignCreator,
    CampaignDefaults,
    CampaignSetupError,
    OfferNotFoundError,
)

DEFAULTS = CampaignDefaults(domain="kylovoa.com", group="FORTESTS", traffic_source="FORTESTS")


def mock_directories(keitaro_api):
    keitaro_api.get("/domains").respond(json=[{"id": 1813, "name": "kylovoa.com"}])
    keitaro_api.get("/groups", params={"type": "campaigns"}).respond(
        json=[{"id": 1, "name": "other"}, {"id": 10332, "name": "FORTESTS"}]
    )
    keitaro_api.get("/traffic_sources").respond(json=[{"id": 836, "name": "FORTESTS"}])
    keitaro_api.get("/offers").respond(json=[{"id": 18813, "name": "Flexacil"}])


def echo_stream(first_id):
    """POST /streams: отвечает телом запроса с новым id, как Keitaro."""
    ids = iter(range(first_id, first_id + 100))

    def handler(request):
        return httpx.Response(
            200, json={"id": next(ids), "state": "active", **json.loads(request.content)}
        )

    return handler


def creator(keitaro, campaigns):
    return CampaignCreator(
        keitaro, DEFAULTS, campaigns, alias_factory=lambda name: "my-campaign-abc123"
    )


@pytest.fixture
def campaigns(db_session):
    return CampaignRepository(db_session)


async def test_creates_campaign_with_geo_redirect_and_offer_streams(
    keitaro, keitaro_api, campaigns
):
    mock_directories(keitaro_api)
    campaign_route = keitaro_api.post("/campaigns").respond(
        json={"id": 500, "name": "My campaign", "alias": "my-campaign-abc123"}
    )
    streams_route = keitaro_api.post("/streams").mock(side_effect=echo_stream(first_id=601))

    result = await creator(keitaro, campaigns).create(
        CampaignCreateRequest(name="My campaign", geo="MX,AU", offer_id=18813)
    )

    assert json.loads(campaign_route.calls.last.request.content) == {
        "name": "My campaign",
        "alias": "my-campaign-abc123",
        "domain_id": 1813,
        "group_id": 10332,
        "traffic_source_id": 836,
    }
    geo_stream, offer_stream = (json.loads(call.request.content) for call in streams_route.calls)
    assert geo_stream == {
        "campaign_id": 500,
        "name": "Geo MX,AU → Google",
        "type": "regular",
        "position": 1,
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://google.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["MX", "AU"]}],
        "offers": [],
    }
    assert offer_stream == {
        "campaign_id": 500,
        "name": "Offers",
        "type": "default",
        "position": 2,
        "schema": "landings",
        "action_type": "http",
        "filters": [],
        "offers": [{"offer_id": 18813, "share": 100, "state": "active"}],
    }
    assert (result.keitaro_id, result.alias, result.geo, result.offer_id) == (
        500,
        "my-campaign-abc123",
        ["MX", "AU"],
        18813,
    )
    assert (result.geo_stream_id, result.offer_stream_id) == (601, 602)


async def test_missing_group_raises_setup_error_and_creates_nothing(
    keitaro, keitaro_api, campaigns
):
    keitaro_api.get("/domains").respond(json=[{"id": 1813, "name": "kylovoa.com"}])
    keitaro_api.get("/groups", params={"type": "campaigns"}).respond(json=[{"id": 1, "name": "x"}])
    keitaro_api.get("/traffic_sources").respond(json=[{"id": 836, "name": "FORTESTS"}])
    keitaro_api.get("/offers").respond(json=[{"id": 18813, "name": "Flexacil"}])

    # POST /campaigns не замокан: попытка создать кампанию уронит тест ошибкой respx.
    with pytest.raises(CampaignSetupError, match="группа кампаний 'FORTESTS'"):
        await creator(keitaro, campaigns).create(
            CampaignCreateRequest(name="X", geo="AU", offer_id=18813)
        )


async def test_unknown_offer_raises_and_creates_nothing(keitaro, keitaro_api, campaigns):
    mock_directories(keitaro_api)

    with pytest.raises(OfferNotFoundError, match="99999"):
        await creator(keitaro, campaigns).create(
            CampaignCreateRequest(name="X", geo="AU", offer_id=99999)
        )


async def test_stream_failure_rolls_back_created_campaign(keitaro, keitaro_api, campaigns):
    mock_directories(keitaro_api)
    keitaro_api.post("/campaigns").respond(json={"id": 500, "name": "X", "alias": "x-abc123"})
    keitaro_api.post("/streams").respond(status_code=422, json={"error": "Invalid filter"})
    delete_route = keitaro_api.delete("/campaigns/500").respond(json={})

    with pytest.raises(KeitaroError, match="Invalid filter"):
        await creator(keitaro, campaigns).create(
            CampaignCreateRequest(name="X", geo="AU", offer_id=18813)
        )

    assert delete_route.called


async def test_failed_rollback_does_not_hide_original_error(keitaro, keitaro_api, campaigns):
    mock_directories(keitaro_api)
    keitaro_api.post("/campaigns").respond(json={"id": 500, "name": "X", "alias": "x-abc123"})
    keitaro_api.post("/streams").respond(status_code=422, json={"error": "Invalid filter"})
    keitaro_api.delete("/campaigns/500").respond(status_code=500, json={"error": "boom"})

    with pytest.raises(KeitaroError, match="Invalid filter"):
        await creator(keitaro, campaigns).create(
            CampaignCreateRequest(name="X", geo="AU", offer_id=18813)
        )


async def test_created_campaign_is_saved_to_registry(keitaro, keitaro_api, campaigns):
    mock_directories(keitaro_api)
    keitaro_api.post("/campaigns").respond(
        json={"id": 500, "name": "My campaign", "alias": "my-campaign-abc123"}
    )
    keitaro_api.post("/streams").mock(side_effect=echo_stream(first_id=601))

    await creator(keitaro, campaigns).create(
        CampaignCreateRequest(name="My campaign", geo="MX", offer_id=18813)
    )

    saved = await campaigns.get_by_keitaro_id(500)
    assert saved is not None
    assert (saved.geo, saved.offer_stream_id) == (["MX"], 602)


async def test_rolled_back_campaign_is_not_saved(keitaro, keitaro_api, campaigns):
    mock_directories(keitaro_api)
    keitaro_api.post("/campaigns").respond(json={"id": 500, "name": "X", "alias": "x-abc123"})
    keitaro_api.post("/streams").respond(status_code=422, json={"error": "Invalid filter"})
    keitaro_api.delete("/campaigns/500").respond(json={})

    with pytest.raises(KeitaroError):
        await creator(keitaro, campaigns).create(
            CampaignCreateRequest(name="X", geo="AU", offer_id=18813)
        )

    assert await campaigns.list() == []
