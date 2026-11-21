import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import campaigns, editor, health, offers
from app.api.errors import register_error_handlers
from app.core.config import DatabaseSettings, WebSettings
from app.db.session import create_engine, create_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Один httpx-клиент и один engine БД на всё приложение."""
    engine = create_engine(DatabaseSettings().database_url)
    app.state.sessionmaker = create_sessionmaker(engine)
    app.state.editor_lock = asyncio.Lock()
    async with httpx.AsyncClient(timeout=30) as http:
        app.state.http = http
        app.state.live = None  # сервис live-опроса создаётся при первом открытии редактора
        yield
        if app.state.live is not None:
            # uvicorn доходит сюда, когда закроет соединения: SSE сами не закрываются, поэтому
            # сервер запускаем с --timeout-graceful-shutdown (README)
            await app.state.live.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Keitaro wrapper", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=WebSettings().cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(campaigns.router, prefix="/api")
    app.include_router(offers.router, prefix="/api")
    app.include_router(editor.router, prefix="/api")
    return app


app = create_app()
