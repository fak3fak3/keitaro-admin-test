from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import campaigns, health, offers
from app.api.errors import register_error_handlers
from app.core.config import DatabaseSettings
from app.db.session import create_engine, create_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Один httpx-клиент и один engine БД на всё приложение."""
    engine = create_engine(DatabaseSettings().database_url)
    app.state.sessionmaker = create_sessionmaker(engine)
    async with httpx.AsyncClient(timeout=30) as http:
        app.state.http = http
        yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Keitaro wrapper", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(campaigns.router, prefix="/api")
    app.include_router(offers.router, prefix="/api")
    return app


app = create_app()
