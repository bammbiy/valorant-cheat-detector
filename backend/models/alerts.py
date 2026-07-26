from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from backend.models.analysis import GameId


class AlertSeverity(str, Enum):
    REVIEW = "review"
    HIGH_RISK = "high-risk"


class Alert(BaseModel):
    id: str
    game: GameId
    player: str
    suspicion_pct: int
    severity: AlertSeverity
    title: str
    detail: str
    created_at: float
