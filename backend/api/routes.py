from __future__ import annotations

from typing import Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Query
from backend.models.analysis import AnalysisResult, GameId
from backend.services.analyzer import analyze_player
from backend.core.config import get_settings
from backend.services.games import serialize_game_catalog
from backend.models.alerts import Alert
from backend.services.alerts import list_alerts
from backend.models.product import ModelReport, QualityReport
from backend.services.product import get_model_report, get_quality_report

router = APIRouter(prefix="/api")
cfg = get_settings()


@router.get("/analyze/{region}/{name}/{tag}", response_model=AnalysisResult)
async def analyze(
    region: str,
    name: str,
    tag: str,
    game: GameId = Query(default=GameId.VALORANT),
) -> AnalysisResult:
    if game is GameId.OVERWATCH:
        raise HTTPException(
            status_code=501,
            detail="Overwatch 분석은 공식 데이터 소스 검증 후 제공됩니다.",
        )
    return await analyze_player(name=name, tag=tag, region=region.lower())


@router.get("/games")
async def games() -> List[Dict[str, str]]:
    """분석 가능한 게임과 데이터 소스 상태를 반환한다."""
    return serialize_game_catalog()


@router.get("/alerts", response_model=List[Alert])
async def alerts(
    game: Optional[GameId] = Query(default=None),
    since: float = Query(default=0.0, ge=0.0),
) -> List[Alert]:
    """최근 분석에서 생성된 로컬 검토 알림을 반환한다."""
    return list_alerts(game=game, since=since)


@router.get("/quality", response_model=QualityReport)
async def quality() -> QualityReport:
    """모델 품질과 검증 상태를 반환한다."""
    return get_quality_report()


@router.get("/model", response_model=ModelReport)
async def model() -> ModelReport:
    """탐지 모델의 신호와 안전장치를 반환한다."""
    return get_model_report()


@router.get("/health")
async def health() -> Dict[str, Union[bool, str]]:
    return {
        "status": "ok",
        "demo_mode": cfg.is_demo,
        "api_key_set": cfg.riot_api_key != "RGAPI-DEMO",
    }
