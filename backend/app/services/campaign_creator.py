import asyncio
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.clients.keitaro import KeitaroClient, KeitaroError
from app.clients.keitaro.schemas import CampaignCreate, StreamCreate, StreamFilter, StreamOffer
from app.repositories.campaigns import CampaignRepository
from app.schemas.campaign import CampaignCreateRequest, CreatedCampaign
from app.services.alias import make_alias
from app.services.errors import CampaignSetupError, OfferNotFoundError

__all__ = [
    "CampaignCreator",
    "CampaignDefaults",
    "CampaignSetupError",
    "CreatedCampaign",
    "OfferNotFoundError",
]

GEO_REDIRECT_URL = "https://google.com"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CampaignDefaults:
    """Имена домена, группы и источника в Keitaro, с которыми создаются кампании."""

    domain: str
    group: str
    traffic_source: str


class CampaignCreator:
    """Часть 1 ТЗ: кампания с гео-потоком на Google и потоком на оффер."""

    def __init__(
        self,
        keitaro: KeitaroClient,
        defaults: CampaignDefaults,
        campaigns: CampaignRepository,
        alias_factory: Callable[[str], str] = make_alias,
    ) -> None:
        self._keitaro = keitaro
        self._defaults = defaults
        self._campaigns = campaigns
        self._alias_factory = alias_factory

    async def create(self, request: CampaignCreateRequest) -> CreatedCampaign:
        domains, groups, sources, offers = await asyncio.gather(
            self._keitaro.list_domains(),
            self._keitaro.list_campaign_groups(),
            self._keitaro.list_traffic_sources(),
            self._keitaro.list_offers(),
        )
        domain_id = _find_id(domains, self._defaults.domain, "домен")
        group_id = _find_id(groups, self._defaults.group, "группа кампаний")
        source_id = _find_id(sources, self._defaults.traffic_source, "источник трафика")
        if all(offer.id != request.offer_id for offer in offers):
            raise OfferNotFoundError(f"Оффер {request.offer_id} не найден в Keitaro")

        campaign = await self._keitaro.create_campaign(
            CampaignCreate(
                name=request.name,
                alias=self._alias_factory(request.name),
                domain_id=domain_id,
                group_id=group_id,
                traffic_source_id=source_id,
            )
        )
        try:
            geo_stream = await self._keitaro.create_stream(_geo_stream(campaign.id, request.geo))
            offer_stream = await self._keitaro.create_stream(
                _offer_stream(campaign.id, request.offer_id)
            )
        except KeitaroError:
            await self._rollback(campaign.id)
            raise

        created = CreatedCampaign(
            keitaro_id=campaign.id,
            name=campaign.name,
            alias=campaign.alias,
            geo=request.geo,
            offer_id=request.offer_id,
            geo_stream_id=geo_stream.id,
            offer_stream_id=offer_stream.id,
        )
        await self._campaigns.add(created)
        return created

    async def _rollback(self, campaign_id: int) -> None:
        """Убираем полусозданную кампанию; сбой отката не должен скрыть исходную ошибку."""
        try:
            await self._keitaro.delete_campaign(campaign_id)
        except KeitaroError:
            logger.exception("Не удалось откатить кампанию %s в Keitaro", campaign_id)


def _geo_stream(campaign_id: int, geo: list[str]) -> StreamCreate:
    """Поток 1: всех из указанных стран редиректим на Google."""
    return StreamCreate(
        campaign_id=campaign_id,
        name=f"Geo {','.join(geo)} → Google",
        type="regular",
        position=1,
        schema="redirect",
        action_type="http",
        action_payload=GEO_REDIRECT_URL,
        filters=[StreamFilter(name="country", mode="accept", payload=geo)],
    )


def _offer_stream(campaign_id: int, offer_id: int) -> StreamCreate:
    """Поток 2 (по умолчанию): всех остальных отправляем на оффер."""
    return StreamCreate(
        campaign_id=campaign_id,
        name="Offers",
        type="default",
        position=2,
        schema="landings",
        action_type="http",
        offers=[StreamOffer(offer_id=offer_id, share=100)],
    )


class _Named(Protocol):
    id: int
    name: str


def _find_id(items: Sequence[_Named], name: str, label: str) -> int:
    for item in items:
        if item.name == name:
            return item.id
    raise CampaignSetupError(f"В Keitaro не найден {label} '{name}' (проверьте настройки .env)")
