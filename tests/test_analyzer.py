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

    async def test_games_endpoint_exposes_overwatch_research_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/games")
        assert r.status_code == 200
        games = {item["id"]: item for item in r.json()}
        assert games["valorant"]["status"] == "available"
        assert games["overwatch"]["status"] == "research"

    async def test_overwatch_analysis_is_explicitly_unavailable(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/analyze/kr/ShadowX/KR1?game=overwatch")
        assert r.status_code == 501

    async def test_high_risk_analysis_creates_review_alert(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/api/analyze/kr/ShadowX/KR1")
            r = await client.get("/api/alerts?game=valorant")
        assert r.status_code == 200
        assert any(alert["player"] == "ShadowX#KR1" for alert in r.json())

    async def test_quality_and_model_endpoints_expose_limitations(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            quality_response = await client.get("/api/quality")
            model_response = await client.get("/api/model")
        assert quality_response.status_code == 200
        assert quality_response.json()["status"] == "prototype"
        assert quality_response.json()["limitations"]
        assert model_response.status_code == 200
        assert len(model_response.json()["signals"]) >= 3
        assert model_response.json()["safeguards"]
