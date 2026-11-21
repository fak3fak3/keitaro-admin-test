from app.clients.keitaro.client import KeitaroClient
from app.clients.keitaro.errors import KeitaroError
from app.models.campaign import Campaign
from app.repositories.campaigns import CampaignRepository
from app.services.errors import CampaignNotFoundError


class CampaignConnector:
    def __init__(self, keitaro: KeitaroClient, campaigns: CampaignRepository) -> None:
        self._keitaro = keitaro
        self._campaigns = campaigns

    async def connect(self, campaign_id: int) -> Campaign:
        existing = await self._campaigns.get_by_keitaro_id(campaign_id)
        if existing:
            return existing

        try:
            campaign = await self._keitaro.get_campaign(campaign_id)
        except KeitaroError as exc:
            if exc.status_code == 404:
                raise CampaignNotFoundError(
                    f"Кампания {campaign_id} не найдена в Keitaro"
                ) from exc
            raise

        return await self._campaigns.add_connected(campaign)
