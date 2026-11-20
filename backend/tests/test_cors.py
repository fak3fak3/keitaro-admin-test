from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def preflight(app, origin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.options(
            "/api/campaigns",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )


async def test_frontend_dev_server_is_allowed_by_default(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    response = await preflight(create_app(), "http://localhost:5173")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_origins_are_configured_as_comma_separated_list(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://editor.example")
    app = create_app()

    allowed = await preflight(app, "https://editor.example")
    other = await preflight(app, "https://evil.example")

    assert allowed.headers["access-control-allow-origin"] == "https://editor.example"
    assert "access-control-allow-origin" not in other.headers
