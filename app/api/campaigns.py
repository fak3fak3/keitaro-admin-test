from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.deps import SessionDep, SettingsDep, get_campaign_creator
from app.core.config import Settings
from app.models.campaign import Campaign
from app.repositories.campaigns import CampaignRepository
from app.schemas.campaign import CampaignCreateRequest, CreatedCampaign
from app.services.campaign_creator import CampaignCreator

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignOut(BaseModel):
    keitaro_id: int
    name: str
    alias: str
    geo: list[str]
    offer_id: int
    url: str

    @classmethod
    def build(cls, campaign: Campaign | CreatedCampaign, settings: Settings) -> "CampaignOut":
        return cls(
            keitaro_id=campaign.keitaro_id,
            name=campaign.name,
            alias=campaign.alias,
            geo=campaign.geo,
            offer_id=campaign.offer_id,
            url=f"https://{settings.keitaro_domain}/{campaign.alias}",
        )


@router.get("")
async def list_campaigns(session: SessionDep, settings: SettingsDep) -> list[CampaignOut]:
    """Кампании, созданные через обёртку, новые сверху."""
    campaigns = await CampaignRepository(session).list()
    return [CampaignOut.build(campaign, settings) for campaign in campaigns]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreateRequest,
    creator: Annotated[CampaignCreator, Depends(get_campaign_creator)],
    settings: SettingsDep,
) -> CampaignOut:
    created = await creator.create(body)
    return CampaignOut.build(created, settings)
