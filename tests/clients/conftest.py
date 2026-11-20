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
