from typing import Any

import httpx

from app.clients.keitaro.errors import KeitaroError
from app.clients.keitaro.schemas import (
    Campaign,
    CampaignCreate,
    Domain,
    Group,
    Offer,
    Stream,
    StreamCreate,
    StreamOffer,
    TrafficSource,
)


class KeitaroClient:
    """Тонкий async-клиент Keitaro Admin API v1."""

    def __init__(self, base_url: str, token: str, http: httpx.AsyncClient) -> None:
        self._api = f"{base_url.rstrip('/')}/admin_api/v1"
        self._headers = {"Api-Key": token}
        self._http = http

    async def list_domains(self) -> list[Domain]:
        data = await self._request("GET", "/domains")
        return [Domain.model_validate(item) for item in data]

    async def list_campaign_groups(self) -> list[Group]:
        data = await self._request("GET", "/groups", params={"type": "campaigns"})
        return [Group.model_validate(item) for item in data]

    async def list_traffic_sources(self) -> list[TrafficSource]:
        data = await self._request("GET", "/traffic_sources")
        return [TrafficSource.model_validate(item) for item in data]

    async def list_offers(self) -> list[Offer]:
        data = await self._request("GET", "/offers")
        return [Offer.model_validate(item) for item in data]

    async def create_campaign(self, payload: CampaignCreate) -> Campaign:
        data = await self._request("POST", "/campaigns", json=payload.model_dump())
        return Campaign.model_validate(data)

    async def delete_campaign(self, campaign_id: int) -> None:
        """Keitaro не удаляет кампанию насовсем, а переносит в архив."""
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    async def get_campaign_streams(self, campaign_id: int) -> list[Stream]:
        data = await self._request("GET", f"/campaigns/{campaign_id}/streams")
        return [Stream.model_validate(item) for item in data]

    async def create_stream(self, payload: StreamCreate) -> Stream:
        body = payload.model_dump(by_alias=True, exclude_none=True)
        data = await self._request("POST", "/streams", json=body)
        return Stream.model_validate(data)

    async def update_stream_offers(self, stream_id: int, offers: list[StreamOffer]) -> Stream:
        """Заменяет весь список офферов потока: оффер, которого нет в списке, удаляется."""
        body = {"offers": [offer.model_dump() for offer in offers]}
        data = await self._request("PUT", f"/streams/{stream_id}", json=body)
        return Stream.model_validate(data)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._http.request(
                method, f"{self._api}{path}", headers=self._headers, **kwargs
            )
        except httpx.HTTPError as exc:
            raise KeitaroError(str(exc)) from exc

        if response.is_error:
            raise KeitaroError(_error_message(response), status_code=response.status_code)
        if not response.content:
            return None
        return response.json()


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text
    if isinstance(body, dict) and "error" in body:
        return str(body["error"])
    return response.text
