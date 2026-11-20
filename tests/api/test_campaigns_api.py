from tests.services.test_campaign_creator import echo_stream, mock_directories


async def test_create_campaign_returns_created_campaign_with_url(api, keitaro_api):
    mock_directories(keitaro_api)
    keitaro_api.post("/campaigns").respond(
        json={"id": 500, "name": "My campaign", "alias": "my-campaign-abc123"}
    )
    keitaro_api.post("/streams").mock(side_effect=echo_stream(first_id=601))

    response = await api.post(
        "/api/campaigns", json={"name": "My campaign", "geo": "MX,AU", "offer_id": 18813}
    )

    assert response.status_code == 201
    assert response.json() == {
        "keitaro_id": 500,
        "name": "My campaign",
        "alias": "my-campaign-abc123",
        "geo": ["MX", "AU"],
        "offer_id": 18813,
        "url": "https://kylovoa.com/my-campaign-abc123",
    }


async def test_invalid_geo_is_rejected_with_422(api):
    response = await api.post(
        "/api/campaigns", json={"name": "X", "geo": "Mexico", "offer_id": 18813}
    )

    assert response.status_code == 422


async def test_unknown_offer_returns_404_with_message(api, keitaro_api):
    mock_directories(keitaro_api)

    response = await api.post("/api/campaigns", json={"name": "X", "geo": "AU", "offer_id": 1})

    assert response.status_code == 404
    assert response.json() == {"detail": "Оффер 1 не найден в Keitaro"}


async def test_keitaro_failure_returns_502_with_message(api, keitaro_api):
    keitaro_api.get("/domains").respond(status_code=401, json={"error": "Unauthorized"})
    keitaro_api.get("/groups").respond(json=[])
    keitaro_api.get("/traffic_sources").respond(json=[])
    keitaro_api.get("/offers").respond(json=[])

    response = await api.post("/api/campaigns", json={"name": "X", "geo": "AU", "offer_id": 18813})

    assert response.status_code == 502
    assert response.json() == {"detail": "Keitaro API error (401): Unauthorized"}


async def test_setup_error_returns_503(api, keitaro_api):
    keitaro_api.get("/domains").respond(json=[])
    keitaro_api.get("/groups").respond(json=[])
    keitaro_api.get("/traffic_sources").respond(json=[])
    keitaro_api.get("/offers").respond(json=[])

    response = await api.post("/api/campaigns", json={"name": "X", "geo": "AU", "offer_id": 18813})

    assert response.status_code == 503
    assert "домен 'kylovoa.com'" in response.json()["detail"]


async def test_list_campaigns_returns_created_ones_newest_first(api, db_session):
    from app.repositories.campaigns import CampaignRepository
    from app.schemas.campaign import CreatedCampaign

    repo = CampaignRepository(db_session)
    for keitaro_id, alias in [(1, "first-aaa111"), (2, "second-bbb222")]:
        await repo.add(
            CreatedCampaign(
                keitaro_id=keitaro_id,
                name=alias.split("-")[0],
                alias=alias,
                geo=["AU"],
                offer_id=18813,
                geo_stream_id=10 + keitaro_id,
                offer_stream_id=20 + keitaro_id,
            )
        )

    response = await api.get("/api/campaigns")

    assert response.status_code == 200
    assert [(c["keitaro_id"], c["url"]) for c in response.json()] == [
        (2, "https://kylovoa.com/second-bbb222"),
        (1, "https://kylovoa.com/first-aaa111"),
    ]
