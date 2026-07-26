from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from backend.core.config import get_settings
from backend.models.analysis import (
    AnalysisResult, MatchRecord, PlayerStats,
    SubsystemScores, Verdict,
)
from backend.services.detection import (
    MatchData,
    compute_final,
    compute_trust,
    run_ml_ensemble,
    compute_evidence_confidence,
    run_physics_check,
    run_stat_anomaly,
)
from backend.services.alerts import record_analysis_alert
from backend.services.demo_data import DEMO_PLAYERS
from backend.services.riot_client import RiotClient

log = logging.getLogger(__name__)
cfg = get_settings()
_client = RiotClient()


def _parse_match(detail: dict, puuid: str) -> MatchData | None:
    """매치 상세 dict에서 해당 플레이어 MatchData 추출. 파싱 실패 시 None."""
    all_players = detail.get("players", {}).get("allPlayers", [])
    match_info  = detail.get("matchInfo", {})
    teams       = detail.get("teams", {})

    for p in all_players:
        if p.get("puuid") != puuid:
            continue

        stats       = p.get("stats", {})
        hs          = stats.get("headShots", 0)
        body        = stats.get("bodyShots", 0)
        leg         = stats.get("legShots",  0)
        total_shots = hs + body + leg or 1
        hs_pct      = hs / total_shots

        kills   = stats.get("kills",   0)
        deaths  = max(stats.get("deaths",  1), 1)
        assists = stats.get("assists", 0)

        rounds  = max(match_info.get("roundsPlayed", 1), 1)
        damage  = stats.get("damage", {})
        adr     = int(damage.get("dealt", 0) / rounds) if isinstance(damage, dict) else 0

        team_id = p.get("teamId", "").lower()
        won     = teams.get(team_id, {}).get("won", False)

        return MatchData(
            hs=round(hs_pct, 4),
            kda=round((kills + assists) / deaths, 2),
            adr=adr,
            won=won,
            map=match_info.get("mapId", "Unknown"),
            agent=p.get("characterId", "Unknown"),
            kills=kills,
            deaths=deaths,
            assists=assists,
        )

    return None


def _build_match_record(m: MatchData, suspicion: int) -> MatchRecord:
    return MatchRecord(
        map=m.map,
        agent=m.agent,
        kda=f"{m.kills}/{m.deaths}/{m.assists}",
        hs_pct=round(m.hs * 100, 1),
        adr=m.adr,
        suspicion=suspicion,
        won=m.won,
    )


def _derive_verdict(suspicion: int) -> Verdict:
    if suspicion >= 75:
        return Verdict.CHEATER
    if suspicion >= 45:
        return Verdict.SUSPECT
    return Verdict.CLEAN


async def _fetch_matches_parallel(
    match_ids: list[str], platform: str
) -> list[dict]:
    """매치 상세 정보를 asyncio.gather로 병렬 조회. 개별 실패는 무시."""
    tasks = [_client.get_match(mid, platform) for mid in match_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    details: list[dict] = []
    for mid, result in zip(match_ids, results):
        if isinstance(result, Exception):
            log.warning("매치 %s 조회 실패: %s", mid, result)
        else:
            details.append(result)
    return details


async def analyze_player(name: str, tag: str, region: str) -> AnalysisResult:
    """플레이어 닉네임으로 핵 의심도 분석 수행."""
    if cfg.is_demo:
        key = f"{name}#{tag}".lower()
        result = DEMO_PLAYERS.get(key) or next(iter(DEMO_PLAYERS.values()))
        log.info("demo 데이터 반환: %s", key)
        record_analysis_alert(result)
        return result

    platform = cfg.region_platform.get(region)
    routing  = cfg.region_routing.get(region)
    if not platform or not routing:
        raise HTTPException(400, f"지원하지 않는 지역: {region}")

    account   = await _client.get_account(name, tag, routing)
    puuid     = account["puuid"]
    match_ids = await _client.get_match_list(puuid, platform, cfg.match_history_limit)

    if not match_ids:
        raise HTTPException(404, "전적이 없거나 비공개 계정입니다.")

    details     = await _fetch_matches_parallel(match_ids[:cfg.match_detail_limit], platform)
    raw_matches = [m for d in details if (m := _parse_match(d, puuid)) is not None]

    if not raw_matches:
        raise HTTPException(404, "경기 데이터를 파싱할 수 없습니다.")

    stat_r         = run_stat_anomaly(raw_matches)
    phys_r         = run_physics_check(raw_matches)
    ml_score, votes = run_ml_ensemble(raw_matches)
    trust          = compute_trust(raw_matches)
    susp           = compute_final(stat_r.score, phys_r.score, ml_score, trust)
    confidence     = compute_evidence_confidence(
        raw_matches, stat_r.score, phys_r.score, ml_score
    )

    # per-match suspicion (independent single-match analysis)
    match_records: list[MatchRecord] = []
    for m in raw_matches:
        per_stat  = run_stat_anomaly([m]).score
        per_phys  = run_physics_check([m]).score
        per_ml, _ = run_ml_ensemble([m])
        per_susp  = compute_final(per_stat, per_phys, per_ml, trust)
        match_records.append(_build_match_record(m, per_susp))

    total   = len(raw_matches)
    avg_hs  = sum(m.hs  for m in raw_matches) / total
    avg_kda = sum(m.kda for m in raw_matches) / total
    avg_adr = int(sum(m.adr for m in raw_matches) / total)
    wins    = sum(1 for m in raw_matches if m.won)

    result = AnalysisResult(
        name=name,
        tag=tag,
        rank="—",
        region=region,
        suspicion_pct=susp,
        verdict=_derive_verdict(susp),
        stats=PlayerStats(
            avg_hs_pct=round(avg_hs * 100, 1),
            avg_kda=round(avg_kda, 2),
            avg_adr=avg_adr,
            win_rate=round(wins / total * 100, 1),
            games_analyzed=total,
        ),
        subsystems=SubsystemScores(
            stat_anomaly=int(stat_r.score * 100),
            physics=int(phys_r.score * 100),
            ml_ensemble=int(ml_score * 100),
            trust_score=trust,
        ),
        flags=stat_r.flags + phys_r.flags,
        ml_votes=votes,
        matches=match_records[:5],
        hs_history=[round(m.hs * 100, 1) for m in raw_matches],
        suspicion_history=[r.suspicion for r in match_records],
        confidence=confidence,
        evidence_quality="aggregate" if len(raw_matches) >= 5 else "limited",
        limitations=["공개 API 집계 데이터만 사용하며 게임 메모리·원시 에임 텔레메트리는 수집하지 않습니다."],
    )
    record_analysis_alert(result)
    return result
