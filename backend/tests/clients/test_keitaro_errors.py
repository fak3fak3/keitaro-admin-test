import httpx
import pytest

from app.clients.keitaro import KeitaroError


async def test_error_response_raises_keitaro_error_with_message(keitaro, keitaro_api):
    keitaro_api.delete("/campaigns/1").respond(
        status_code=400, json={"error": "Campaign not found"}
    )

    with pytest.raises(KeitaroError) as exc_info:
        await keitaro.delete_campaign(1)

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == "Campaign not found"
    assert "Campaign not found" in str(exc_info.value)


async def test_unauthorized_raises_keitaro_error_with_status(keitaro, keitaro_api):
    keitaro_api.get("/offers").respond(status_code=401, json={"error": "Unauthorized"})

    with pytest.raises(KeitaroError) as exc_info:
        await keitaro.list_offers()

    assert exc_info.value.status_code == 401
    assert exc_info.value.message == "Unauthorized"


async def test_non_json_error_body_is_kept_as_message(keitaro, keitaro_api):
    keitaro_api.get("/offers").respond(status_code=502, text="Bad Gateway")

    with pytest.raises(KeitaroError) as exc_info:
        await keitaro.list_offers()

    assert exc_info.value.status_code == 502
    assert exc_info.value.message == "Bad Gateway"


async def test_network_failure_raises_keitaro_error_without_status(keitaro, keitaro_api):
    keitaro_api.get("/offers").mock(side_effect=httpx.ConnectError("connection refused"))

    with pytest.raises(KeitaroError) as exc_info:
        await keitaro.list_offers()

    assert exc_info.value.status_code is None
