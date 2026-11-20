from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.schemas.campaign import CreatedCampaign


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, created: CreatedCampaign) -> Campaign:
        campaign = Campaign(
            keitaro_id=created.keitaro_id,
            name=created.name,
            alias=created.alias,
            geo=created.geo,
            offer_id=created.offer_id,
            geo_stream_id=created.geo_stream_id,
            offer_stream_id=created.offer_stream_id,
        )
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign)
        return campaign

    async def get_by_keitaro_id(self, keitaro_id: int) -> Campaign | None:
        return await self._session.scalar(select(Campaign).where(Campaign.keitaro_id == keitaro_id))

    async def list(self) -> list[Campaign]:
        result = await self._session.scalars(select(Campaign).order_by(Campaign.id.desc()))
        return list(result)
