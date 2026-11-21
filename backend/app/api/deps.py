import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.keitaro import KeitaroClient
from app.core.config import Settings
from app.repositories.campaigns import CampaignRepository
from app.repositories.streams import StreamRepository
from app.services.campaign_creator import CampaignCreator, CampaignDefaults
from app.services.live import LiveStreams
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


def get_editor_lock(request: Request) -> asyncio.Lock:
    return request.app.state.editor_lock


async def hold_editor_lock(
    lock: Annotated[asyncio.Lock, Depends(get_editor_lock)],
) -> AsyncIterator[None]:
    """Действия редактора и слияние из live-опроса по очереди (DECISIONS.md №37).

    Объявлена раньше сессии БД: FastAPI закрывает зависимости в обратном порядке, поэтому
    замок отпускается после commit.
    """
    async with lock:
        yield


def get_campaign_creator(
    keitaro: KeitaroDep, session: SessionDep, settings: SettingsDep
) -> CampaignCreator:
    defaults = CampaignDefaults(
        domain=settings.keitaro_domain,
        group=settings.keitaro_group,
        traffic_source=settings.keitaro_traffic_source,
    )
    return CampaignCreator(keitaro, defaults, CampaignRepository(session))


def get_offer_editor(
    _lock: Annotated[None, Depends(hold_editor_lock)], keitaro: KeitaroDep, session: SessionDep
) -> OfferEditor:
    return OfferEditor(keitaro, StreamRepository(session))


EditorDep = Annotated[OfferEditor, Depends(get_offer_editor)]


def get_live(request: Request, keitaro: KeitaroDep, settings: SettingsDep) -> LiveStreams:
    """Сервис live-опроса: один на приложение, создаётся при первом открытии редактора."""
    state = request.app.state
    if getattr(state, "live", None) is None:
        sessionmaker = state.sessionmaker

        @asynccontextmanager
        async def editor_session() -> AsyncIterator[OfferEditor]:
            async with sessionmaker() as session:
                yield OfferEditor(keitaro, StreamRepository(session))
                await session.commit()

        state.live = LiveStreams(
            keitaro, editor_session, state.editor_lock, interval=settings.keitaro_poll_interval
        )
    return state.live


LiveDep = Annotated[LiveStreams, Depends(get_live)]
