async def test_connect_existing_campaign_registers_it_and_returns_it(api, keitaro_api):
    keitaro_api.get("/campaigns/93212").respond(
        json={"id": 93212, "name": "campaign 2", "alias": "campaign-2"}
    )

    response = await api.post("/api/campaigns/connect", json={"keitaro_id": 93212})

    assert response.status_code == 201
    assert response.json() == {
        "keitaro_id": 93212,
        "name": "campaign 2",
        "alias": "campaign-2",
        "geo": None,
        "offer_id": None,
        "url": "https://kylovoa.com/campaign-2",
    }
    campaigns = await api.get("/api/campaigns")
    assert [campaign["keitaro_id"] for campaign in campaigns.json()] == [93212]


async def test_connect_unknown_campaign_returns_not_found(api, keitaro_api):
    keitaro_api.get("/campaigns/999999").respond(
        status_code=404, json={"error": "Campaign not found"}
    )

    response = await api.post("/api/campaigns/connect", json={"keitaro_id": 999999})

    assert response.status_code == 404
    assert response.json() == {"detail": "Кампания 999999 не найдена в Keitaro"}


async def test_connect_already_registered_campaign_is_idempotent(api, keitaro_api):
    route = keitaro_api.get("/campaigns/93212").respond(
        json={"id": 93212, "name": "campaign 2", "alias": "campaign-2"}
    )
    first = await api.post("/api/campaigns/connect", json={"keitaro_id": 93212})
    second = await api.post("/api/campaigns/connect", json={"keitaro_id": 93212})

    assert first.status_code == second.status_code == 201
    assert second.json()["keitaro_id"] == 93212
    campaigns = await api.get("/api/campaigns")
    assert len(campaigns.json()) == 1
    assert len(route.calls) == 1
