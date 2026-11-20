from sqlalchemy import text

from app.db.session import create_engine, create_sessionmaker


async def test_sessionmaker_opens_working_async_session():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    sessionmaker = create_sessionmaker(engine)

    async with sessionmaker() as session:
        result = await session.scalar(text("select 1"))

    await engine.dispose()
    assert result == 1
