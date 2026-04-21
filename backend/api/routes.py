from fastapi import APIRouter, Query
from backend.models.analysis import AnalysisResult
from backend.services.analyzer import analyze_player
from backend.core.config import get_settings

router = APIRouter(prefix="/api")
cfg = get_settings()


@router.get("/analyze/{region}/{name}/{tag}", response_model=AnalysisResult)
async def analyze(
    region: str,
    name: str,
    tag: str,
):
    return await analyze_player(name=name, tag=tag, region=region.lower())


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "demo_mode": cfg.is_demo,
        "api_key_set": cfg.riot_api_key != "RGAPI-DEMO",
    }
