from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field
from enum import Enum


class Verdict(str, Enum):
    CLEAN = "clean"
    SUSPECT = "suspect"
    CHEATER = "cheater"


class GameId(str, Enum):
    VALORANT = "valorant"
    OVERWATCH = "overwatch"


class Flag(BaseModel):
    severity: str           # "red" | "amber" | "green"
    title: str
    detail: str
    source: str


class MatchRecord(BaseModel):
    map: str
    agent: str
    kda: str
    hs_pct: float
    adr: int
    suspicion: int
    won: bool


class SubsystemScores(BaseModel):
    stat_anomaly: int
    physics: int
    ml_ensemble: int
    trust_score: int


class MLVote(BaseModel):
    model: str
    confidence: int


class PlayerStats(BaseModel):
    avg_hs_pct: float
    avg_kda: float
    avg_adr: int
    win_rate: float
    games_analyzed: int


class AnalysisResult(BaseModel):
    name: str
    tag: str
    rank: str
    region: str
    suspicion_pct: int
    verdict: Verdict
    stats: PlayerStats
    subsystems: SubsystemScores
    flags: List[Flag]
    ml_votes: List[MLVote]
    matches: List[MatchRecord]
    hs_history: List[float]
    suspicion_history: List[int]
    game: GameId = GameId.VALORANT
    data_source: str = "riot_api"
    confidence: int = 50
    evidence_quality: str = "limited"
    limitations: List[str] = Field(default_factory=list)
    demo: bool = False
