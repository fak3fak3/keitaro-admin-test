from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.deps import KeitaroDep, SessionDep, SettingsDep, get_campaign_creator
from app.core.config import Settings
from app.models.campaign import Campaign
from app.repositories.campaigns import CampaignRepository
from app.schemas.campaign import CampaignCreateRequest, CreatedCampaign
from app.services.campaign_connector import CampaignConnector
from app.services.campaign_creator import CampaignCreator


class CampaignConnectRequest(BaseModel):
    keitaro_id: int = Field(gt=0)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignOut(BaseModel):
    keitaro_id: int
    name: str
    alias: str
    geo: list[str] | None
    offer_id: int | None
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
    """Подключённые кампании, новые сверху."""
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


@router.post("/connect", status_code=status.HTTP_201_CREATED)
async def connect_campaign(
    body: CampaignConnectRequest,
    keitaro: KeitaroDep,
    session: SessionDep,
    settings: SettingsDep,
) -> CampaignOut:
    connector = CampaignConnector(keitaro, CampaignRepository(session))
    campaign = await connector.connect(body.keitaro_id)
    return CampaignOut.build(campaign, settings)
