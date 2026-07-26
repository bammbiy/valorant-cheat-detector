from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field

from backend.core.config import get_settings
from backend.models.analysis import Flag, MLVote

log = logging.getLogger(__name__)
cfg = get_settings()


@dataclass
class MatchData:
    hs: float
    kda: float
    adr: int
    won: bool
    map: str = ""
    agent: str = ""
    kills: int = 0
    deaths: int = 1
    assists: int = 0


@dataclass
class SubsystemResult:
    score: float
    flags: list[Flag] = field(default_factory=list)


# ── stat anomaly ──────────────────────────────────────────────────────────────

def _check_absolute_hs(avg_hs: float, flags: list[Flag]) -> float:
    if avg_hs <= cfg.hs_alert:
        return 0.0
    severity = min((avg_hs - cfg.hs_alert) / 0.15, 1.0)
    flags.append(Flag(
        severity="red",
        title=f"헤드샷율 {avg_hs * 100:.0f}% — 정상 상위 0.1% 초과",
        detail=f"레디언트 평균({cfg.hs_normal_avg * 100:.0f}%) 대비 +{(avg_hs - cfg.hs_normal_avg) * 100:.0f}%p",
        source="stat",
    ))
    return 0.35 * severity


def _check_hs_spike(hs_vals: list[float], flags: list[Flag]) -> float:
    if len(hs_vals) < 5:
        return 0.0
    early = sum(hs_vals[:5]) / 5
    late  = sum(hs_vals[-5:]) / 5
    if late - early <= cfg.hs_spike_delta:
        return 0.0
    flags.append(Flag(
        severity="amber",
        title=f"헤드샷율 {(late - early) * 100:.0f}%p 급상승",
        detail=f"이전 5경기 {early * 100:.0f}% → 최근 {late * 100:.0f}%",
        source="stat",
    ))
    return 0.25


def _check_hs_consistency(hs_vals: list[float], avg_hs: float, flags: list[Flag]) -> float:
    if len(hs_vals) < 4:
        return 0.0
    try:
        std = statistics.stdev(hs_vals)
    except statistics.StatisticsError as exc:
        log.warning("stdev 계산 실패: %s (샘플 수: %d)", exc, len(hs_vals))
        return 0.0
    if std >= cfg.hs_consistency_max_std or avg_hs < cfg.hs_consistency_min_avg:
        return 0.0
    flags.append(Flag(
        severity="amber",
        title="헤드샷율 일관성 비정상 (σ 낮음)",
        detail=f"σ={std * 100:.1f}% — 정상 범위 5–15%",
        source="stat",
    ))
    return 0.18


def _check_kda(avg_kda: float, flags: list[Flag]) -> float:
    if avg_kda <= cfg.kda_alert:
        return 0.0
    flags.append(Flag(
        severity="red",
        title=f"K/D {avg_kda:.1f} — 같은 랭크 상위 0.3%",
        detail="헤드샷율 이상과 결합 시 의심도 상승",
        source="stat",
    ))
    return 0.20


def run_stat_anomaly(matches: list[MatchData]) -> SubsystemResult:
    """헤드샷율·KDA 통계 이상 탐지."""
    if not matches:
        return SubsystemResult(score=0.0)

    hs_vals  = [m.hs  for m in matches]
    kda_vals = [m.kda for m in matches]
    avg_hs   = sum(hs_vals)  / len(hs_vals)
    avg_kda  = sum(kda_vals) / len(kda_vals)

    flags: list[Flag] = []
    score = (
        _check_absolute_hs(avg_hs, flags)
        + _check_hs_spike(hs_vals, flags)
        + _check_hs_consistency(hs_vals, avg_hs, flags)
        + _check_kda(avg_kda, flags)
    )
    return SubsystemResult(score=min(score, 1.0), flags=flags)


# ── physics impossibility ─────────────────────────────────────────────────────
# Riot public API exposes only aggregate stats — no raw aim/mouse telemetry.
# These checks proxy from HS rate and KDA. A production implementation
# would require kernel-level data (out of scope for public-API tools).

def run_physics_check(matches: list[MatchData]) -> SubsystemResult:
    """물리적 불가능 이벤트 추정 (집계 스탯 프록시)."""
    if not matches:
        return SubsystemResult(score=0.0)

    avg_hs  = sum(m.hs  for m in matches) / len(matches)
    avg_kda = sum(m.kda for m in matches) / len(matches)
    flags: list[Flag] = []
    score = 0.0

    if avg_hs > cfg.hs_physics_hard:
        score += 0.50
        flags.append(Flag(
            severity="red",
            title="에임 정확도 물리 한계 근접",
            detail=f"HS율 {avg_hs * 100:.0f}% — 프로 평균(60%)의 1.5배 이상",
            source="physics",
        ))
    elif avg_hs > cfg.hs_physics_soft:
        score += 0.22

    if avg_kda > cfg.kda_physics_alert:
        score += 0.28
        flags.append(Flag(
            severity="red",
            title=f"KDA {avg_kda:.1f} — 반응속도 이상 추정",
            detail="극단적 생존율은 비정상 반응 패턴과 강한 상관관계",
            source="physics",
        ))

    if not flags:
        flags.append(Flag(
            severity="green",
            title="물리 이상 패턴 없음",
            detail="정상 범위",
            source="physics",
        ))

    return SubsystemResult(score=min(score, 1.0), flags=flags)


# ── ML ensemble ───────────────────────────────────────────────────────────────
# Production: swap _logistic_score() with a trained sklearn Pipeline.
# Feature vector would be the 47-dim representation of full match telemetry.

def _logistic_score(avg_hs: float, avg_kda: float) -> float:
    logit = (
        (avg_hs  - 0.50) * 2.9
        + (avg_kda - 1.50) * 0.38
        + (1.2 if avg_hs > cfg.hs_physics_hard and avg_kda > 5 else 0)
        + cfg.ml_logit_bias
    )
    return 1 / (1 + math.exp(-logit))


def run_ml_ensemble(matches: list[MatchData]) -> tuple[float, list[MLVote]]:
    """ML 앙상블 의심도 추정."""
    if not matches:
        return 0.0, []

    avg_hs  = sum(m.hs  for m in matches) / len(matches)
    avg_kda = sum(m.kda for m in matches) / len(matches)
    base    = _logistic_score(avg_hs, avg_kda)

    if len(cfg.ml_model_names) != len(cfg.ml_model_scales):
        log.error("ml_model_names / ml_model_scales 길이 불일치")
        return base, []

    votes = [
        MLVote(
            model=name,
            confidence=int(min(99, max(1, base * scale * 100))),
        )
        for name, scale in zip(cfg.ml_model_names, cfg.ml_model_scales)
    ]
    ensemble = sum(v.confidence for v in votes) / (len(votes) * 100)
    return round(ensemble, 4), votes


def compute_evidence_confidence(
    matches: list[MatchData], stat: float, physics: float, ml: float
) -> int:
    """표본 수와 독립 신호 일치도를 합쳐 보수적인 신뢰도를 계산한다."""
    if not matches:
        return cfg.confidence_min

    sample_factor = min(len(matches) / cfg.confidence_full_sample, 1.0)
    signal_spread = max(stat, physics, ml) - min(stat, physics, ml)
    agreement = 1.0 - min(signal_spread, 1.0)
    raw = cfg.confidence_min + 45 * sample_factor + 15 * agreement
    return int(max(cfg.confidence_min, min(cfg.confidence_max, raw)))


# ── trust score ───────────────────────────────────────────────────────────────

def compute_trust(matches: list[MatchData]) -> int:
    """경기 수·통계 기반 누적 신뢰도 점수 (5–95)."""
    total = len(matches)
    if total == 0:
        return 50

    base     = min(total / cfg.trust_games_to_max_base * cfg.trust_base_max, cfg.trust_base_max)
    wins     = sum(1 for m in matches if m.won)
    win_rate = wins / total
    avg_hs   = sum(m.hs for m in matches) / total

    penalty = 0
    if avg_hs > cfg.trust_hs_hard_threshold:
        penalty += cfg.trust_hs_hard_penalty
    elif avg_hs > cfg.trust_hs_soft_threshold:
        penalty += cfg.trust_hs_soft_penalty
    if win_rate > cfg.trust_winrate_alert and avg_hs > cfg.trust_hs_soft_threshold:
        penalty += cfg.trust_winrate_penalty

    return int(max(cfg.trust_min, min(cfg.trust_max, base - penalty + cfg.trust_base_bonus)))


# ── final score ───────────────────────────────────────────────────────────────

def compute_final(stat: float, phys: float, ml: float, trust: int) -> int:
    """4개 서브시스템 가중 합산 → 최종 의심도 (1–99)."""
    trust_factor = (100 - trust) / 100
    raw = (
        cfg.weight_stat  * stat
        + cfg.weight_phys  * phys
        + cfg.weight_ml    * ml
        + cfg.weight_trust * trust_factor
    )
    return int(min(99, max(1, raw * 100)))
