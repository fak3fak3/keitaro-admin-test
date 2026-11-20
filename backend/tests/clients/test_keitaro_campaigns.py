import json

from app.clients.keitaro.schemas import CampaignCreate


async def test_create_campaign_posts_settings_and_returns_campaign(keitaro, keitaro_api):
    route = keitaro_api.post("/campaigns").respond(
        json={"id": 93212, "name": "campaign 2", "alias": "wVqN1R", "state": "active"}
    )

    campaign = await keitaro.create_campaign(
        CampaignCreate(
            name="campaign 2", alias="wVqN1R", domain_id=1, group_id=7, traffic_source_id=3
        )
    )

    assert json.loads(route.calls.last.request.content) == {
        "name": "campaign 2",
        "alias": "wVqN1R",
        "domain_id": 1,
        "group_id": 7,
        "traffic_source_id": 3,
    }
    assert (campaign.id, campaign.name, campaign.alias) == (93212, "campaign 2", "wVqN1R")


async def test_delete_campaign_moves_it_to_archive(keitaro, keitaro_api):
    route = keitaro_api.delete("/campaigns/93212").respond(status_code=201, json={})

    await keitaro.delete_campaign(93212)

    assert route.called


async def test_delete_campaign_accepts_empty_response_body(keitaro, keitaro_api):
    keitaro_api.delete("/campaigns/93212").respond(status_code=204)

    await keitaro.delete_campaign(93212)
