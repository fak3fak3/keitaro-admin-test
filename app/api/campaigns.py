from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.deps import SettingsDep, get_campaign_creator
from app.schemas.campaign import CampaignCreateRequest
from app.services.campaign_creator import CampaignCreator

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignOut(BaseModel):
    keitaro_id: int
    name: str
    alias: str
    geo: list[str]
    offer_id: int
    url: str


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreateRequest,
    creator: Annotated[CampaignCreator, Depends(get_campaign_creator)],
    settings: SettingsDep,
) -> CampaignOut:
    created = await creator.create(body)
    return CampaignOut(
        keitaro_id=created.keitaro_id,
        name=created.name,
        alias=created.alias,
        geo=created.geo,
        offer_id=created.offer_id,
        url=f"https://{settings.keitaro_domain}/{created.alias}",
    )
