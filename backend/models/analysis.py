from pydantic import BaseModel
from enum import Enum


class Verdict(str, Enum):
    CLEAN = "clean"
    SUSPECT = "suspect"
    CHEATER = "cheater"


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
    flags: list[Flag]
    ml_votes: list[MLVote]
    matches: list[MatchRecord]
    hs_history: list[float]
    suspicion_history: list[int]
    demo: bool = False
