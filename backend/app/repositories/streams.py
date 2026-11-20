from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stream import Stream


class StreamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_campaign(self, campaign_id: int) -> list[Stream]:
        result = await self._session.scalars(
            select(Stream)
            .where(Stream.campaign_id == campaign_id)
            .order_by(Stream.position, Stream.id)
        )
        return list(result)

    async def get_by_keitaro_id(self, keitaro_id: int) -> Stream | None:
        return await self._session.scalar(select(Stream).where(Stream.keitaro_id == keitaro_id))

    def add(self, stream: Stream) -> None:
        self._session.add(stream)

    async def delete(self, stream: Stream) -> None:
        await self._session.delete(stream)

    async def flush(self) -> None:
        await self._session.flush()
