from app.repositories.campaigns import CampaignRepository
from app.schemas.campaign import CreatedCampaign

CREATED = CreatedCampaign(
    keitaro_id=500,
    name="My campaign",
    alias="my-campaign-abc123",
    geo=["MX", "AU"],
    offer_id=18813,
    geo_stream_id=601,
    offer_stream_id=602,
)


async def test_saved_campaign_can_be_read_back(db_session):
    repo = CampaignRepository(db_session)

    await repo.add(CREATED)
    saved = await repo.get_by_keitaro_id(500)

    assert saved is not None
    assert (saved.name, saved.alias, saved.geo, saved.offer_id) == (
        "My campaign",
        "my-campaign-abc123",
        ["MX", "AU"],
        18813,
    )
    assert (saved.geo_stream_id, saved.offer_stream_id) == (601, 602)
    assert saved.created_at is not None


async def test_list_returns_newest_first(db_session):
    repo = CampaignRepository(db_session)
    await repo.add(CREATED)
    await repo.add(
        CreatedCampaign(**{**CREATED.__dict__, "keitaro_id": 501, "alias": "second-abc123"})
    )

    campaigns = await repo.list()

    assert [c.keitaro_id for c in campaigns] == [501, 500]
