from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import KeitaroDep

router = APIRouter(prefix="/offers", tags=["offers"])

SEARCH_LIMIT = 20


class OfferOut(BaseModel):
    id: int
    name: str


@router.get("")
async def search_offers(
    keitaro: KeitaroDep, q: Annotated[str, Query(max_length=100)] = ""
) -> list[OfferOut]:
    """Автокомплит офферов: подстрока в названии (без учёта регистра) или в id."""
    needle = q.strip().lower()
    offers = await keitaro.list_offers()
    found = [o for o in offers if needle in o.name.lower() or needle in str(o.id)]
    return [OfferOut(id=o.id, name=o.name) for o in found[:SEARCH_LIMIT]]
