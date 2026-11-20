OFFERS = [
    {"id": 18813, "name": "18813 Flexacil [JOINT-PE] [vsl es -] ReactJs v4"},
    {"id": 3749, "name": "Miaflow [BEAUTY-RO-BE_0009]"},
    {"id": 3717, "name": "Miaflow [BEAUTY-RO-BE_0008]"},
]


async def test_search_offers_by_name_is_case_insensitive(api, keitaro_api):
    keitaro_api.get("/offers").respond(json=OFFERS)

    response = await api.get("/api/offers", params={"q": "miaFLOW"})

    assert response.status_code == 200
    assert response.json() == [
        {"id": 3749, "name": "Miaflow [BEAUTY-RO-BE_0009]"},
        {"id": 3717, "name": "Miaflow [BEAUTY-RO-BE_0008]"},
    ]


async def test_search_offers_by_id(api, keitaro_api):
    keitaro_api.get("/offers").respond(json=OFFERS)

    response = await api.get("/api/offers", params={"q": "3749"})

    assert [o["id"] for o in response.json()] == [3749]


async def test_empty_query_returns_limited_list(api, keitaro_api):
    keitaro_api.get("/offers").respond(json=[{"id": i, "name": f"Offer {i}"} for i in range(1, 51)])

    response = await api.get("/api/offers")

    assert len(response.json()) == 20
