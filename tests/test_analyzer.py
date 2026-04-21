"""Integration tests for backend/services/analyzer.py (demo mode)."""
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from backend.models.analysis import Verdict
from backend.services.demo_data import DEMO_PLAYERS


@pytest.mark.asyncio
class TestAnalyzerDemoMode:
    async def test_known_cheater_returns_high_suspicion(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/analyze/kr/ShadowX/KR1")
        assert r.status_code == 200
        data = r.json()
        assert data["suspicion_pct"] >= 75
        assert data["verdict"] == Verdict.CHEATER

    async def test_clean_player_returns_low_suspicion(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/analyze/kr/ProGamer/KR2")
        assert r.status_code == 200
        data = r.json()
        assert data["suspicion_pct"] < 45
        assert data["verdict"] == Verdict.CLEAN

    async def test_response_shape(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/analyze/kr/ShadowX/KR1")
        data = r.json()
        required_keys = {
            "name", "tag", "rank", "suspicion_pct", "verdict",
            "stats", "subsystems", "flags", "ml_votes", "matches",
            "hs_history", "suspicion_history", "demo",
        }
        assert required_keys.issubset(data.keys())

    async def test_demo_flag_is_set(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/analyze/kr/ShadowX/KR1")
        assert r.json()["demo"] is True

    async def test_unknown_player_falls_back_to_first_demo(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/analyze/kr/UnknownUser/XYZ")
        assert r.status_code == 200
        first = next(iter(DEMO_PLAYERS.values()))
        assert r.json()["name"] == first.name

    async def test_flags_have_required_fields(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/analyze/kr/ShadowX/KR1")
        for flag in r.json()["flags"]:
            assert "severity" in flag
            assert "title" in flag
            assert "detail" in flag
            assert flag["severity"] in ("red", "amber", "green")

    async def test_health_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["demo_mode"] is True
