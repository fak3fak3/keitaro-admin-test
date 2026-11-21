import httpx
import pytest
import respx

from app.clients.keitaro import KeitaroClient

KEITARO_URL = "https://kt.example"
API = f"{KEITARO_URL}/admin_api/v1"
TOKEN = "test-token"


@pytest.fixture
def keitaro_api():
    with respx.mock(base_url=API, assert_all_called=True) as mock:
        yield mock


@pytest.fixture
async def keitaro(keitaro_api):
    async with httpx.AsyncClient() as http:
        yield KeitaroClient(base_url=KEITARO_URL, token=TOKEN, http=http)


@pytest.fixture
async def db_session():
    """Сессия на чистой in-memory SQLite со всеми таблицами моделей."""
    import app.models  # noqa: F401  регистрирует модели в Base.metadata
    from app.db.base import Base
    from app.db.session import create_engine, create_sessionmaker

    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with create_sessionmaker(engine)() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def editor_lock():
    import asyncio

    return asyncio.Lock()


@pytest.fixture
async def api(keitaro, keitaro_api, db_session, editor_lock):
    """HTTP-клиент к нашему приложению; Keitaro — мок respx, БД — in-memory."""
    from httpx import ASGITransport, AsyncClient

    from app.api import deps
    from app.core.config import Settings
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[deps.get_settings] = lambda: Settings(
        keitaro_url=KEITARO_URL, keitaro_admin_token=TOKEN, _env_file=None
    )
    app.dependency_overrides[deps.get_keitaro] = lambda: keitaro
    app.dependency_overrides[deps.get_session] = lambda: db_session
    app.dependency_overrides[deps.get_editor_lock] = lambda: editor_lock

    # ASGITransport ходит в приложение напрямую, respx его не перехватывает.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
