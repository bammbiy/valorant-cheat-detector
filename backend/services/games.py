from __future__ import annotations

from dataclasses import dataclass

from backend.models.analysis import GameId


@dataclass(frozen=True)
class GameCatalogItem:
    """게임 선택 화면에 필요한 제품 메타데이터."""

    id: GameId
    label: str
    status: str
    data_source: str
    description: str


GAME_CATALOG: tuple[GameCatalogItem, ...] = (
    GameCatalogItem(
        id=GameId.VALORANT,
        label="VALORANT",
        status="available",
        data_source="Riot official API",
        description="매치 기록 기반 분석",
    ),
    GameCatalogItem(
        id=GameId.OVERWATCH,
        label="OVERWATCH",
        status="research",
        data_source="Replay / approved source",
        description="공식 데이터 소스 검증 중",
    ),
)


def serialize_game_catalog() -> list[dict[str, str]]:
    """게임 카탈로그를 API 응답용 명시적 타입으로 변환한다."""
    return [
        {
            "id": item.id.value,
            "label": item.label,
            "status": item.status,
            "data_source": item.data_source,
            "description": item.description,
        }
        for item in GAME_CATALOG
    ]
