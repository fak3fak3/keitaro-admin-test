from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.keitaro import KeitaroClient
from app.core.config import Settings
from app.repositories.campaigns import CampaignRepository
from app.repositories.streams import StreamRepository
from app.services.campaign_creator import CampaignCreator, CampaignDefaults
from app.services.offer_editor import OfferEditor


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Сессия на запрос: commit при успехе, rollback при ошибке."""
    async with request.app.state.sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_keitaro(request: Request, settings: SettingsDep) -> KeitaroClient:
    return KeitaroClient(
        base_url=settings.keitaro_url,
        token=settings.keitaro_admin_token.get_secret_value(),
        http=request.app.state.http,
    )


KeitaroDep = Annotated[KeitaroClient, Depends(get_keitaro)]


def get_campaign_creator(
    keitaro: KeitaroDep, session: SessionDep, settings: SettingsDep
) -> CampaignCreator:
    defaults = CampaignDefaults(
        domain=settings.keitaro_domain,
        group=settings.keitaro_group,
        traffic_source=settings.keitaro_traffic_source,
    )
    return CampaignCreator(keitaro, defaults, CampaignRepository(session))


def get_offer_editor(keitaro: KeitaroDep, session: SessionDep) -> OfferEditor:
    return OfferEditor(keitaro, StreamRepository(session))


EditorDep = Annotated[OfferEditor, Depends(get_offer_editor)]
