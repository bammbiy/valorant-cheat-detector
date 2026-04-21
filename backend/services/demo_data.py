from backend.models.analysis import (
    AnalysisResult, Flag, MatchRecord, MLVote,
    PlayerStats, SubsystemScores, Verdict,
)

DEMO_PLAYERS: dict[str, AnalysisResult] = {
    "shadowx#kr1": AnalysisResult(
        name="ShadowX", tag="KR1", rank="Radiant #312", region="kr",
        suspicion_pct=91, verdict=Verdict.CHEATER, demo=True,
        stats=PlayerStats(avg_hs_pct=94.0, avg_kda=8.4, avg_adr=312, win_rate=71.0, games_analyzed=10),
        subsystems=SubsystemScores(stat_anomaly=88, physics=96, ml_ensemble=93, trust_score=14),
        flags=[
            Flag(severity="red",   title="에임 스냅 물리 한계 초과",        detail="avg snap 8.1ms — hw limit 12ms 미달",                source="physics"),
            Flag(severity="red",   title="헤드샷율 Radiant 상위 0.01%",     detail="94% vs avg 52% (+42%p)",                             source="stat"),
            Flag(severity="red",   title="반응속도 62ms — 인간 임계값 미달", detail="150ms 이하 6회 연속 · aimbot pattern detected",        source="physics"),
            Flag(severity="red",   title="벽 너머 선조준 71% 일치",          detail="비가시 구역 pre-aim 다수 감지",                       source="physics"),
            Flag(severity="amber", title="3경기 내 HS율 +38%p 급상승",       detail="56% → 94% · 핵 활성화 의심",                         source="stat"),
        ],
        ml_votes=[
            MLVote(model="Random Forest",    confidence=97),
            MLVote(model="XGBoost",          confidence=94),
            MLVote(model="LSTM (시계열)",     confidence=91),
            MLVote(model="Isolation Forest", confidence=88),
            MLVote(model="k-NN",             confidence=95),
        ],
        matches=[
            MatchRecord(map="Sunset",  agent="Jett",   kda="28/4/6",  hs_pct=96, adr=334, suspicion=94, won=True),
            MatchRecord(map="Abyss",   agent="Neon",   kda="24/5/8",  hs_pct=93, adr=308, suspicion=91, won=True),
            MatchRecord(map="Bind",    agent="Jett",   kda="31/3/4",  hs_pct=97, adr=341, suspicion=95, won=True),
            MatchRecord(map="Haven",   agent="Reyna",  kda="22/7/5",  hs_pct=91, adr=287, suspicion=89, won=False),
            MatchRecord(map="Icebox",  agent="Jett",   kda="19/6/9",  hs_pct=89, adr=271, suspicion=86, won=True),
        ],
        hs_history=[56,58,61,65,70,78,85,89,92,94],
        suspicion_history=[42,45,50,58,67,74,80,85,88,91],
    ),
    "progamer#kr2": AnalysisResult(
        name="ProGamer", tag="KR2", rank="Immortal 3 #88", region="kr",
        suspicion_pct=29, verdict=Verdict.CLEAN, demo=True,
        stats=PlayerStats(avg_hs_pct=47.0, avg_kda=2.1, avg_adr=168, win_rate=54.0, games_analyzed=10),
        subsystems=SubsystemScores(stat_anomaly=28, physics=22, ml_ensemble=31, trust_score=78),
        flags=[
            Flag(severity="green", title="에임 지표 정상 범위",  detail="HS율·스냅 속도 모두 정상 분포 내", source="stat"),
            Flag(severity="green", title="반응속도 정상",        detail="avg 198ms — 정상 범위 150–300ms",  source="physics"),
        ],
        ml_votes=[
            MLVote(model="Random Forest",    confidence=27),
            MLVote(model="XGBoost",          confidence=31),
            MLVote(model="LSTM (시계열)",     confidence=28),
            MLVote(model="Isolation Forest", confidence=24),
            MLVote(model="k-NN",             confidence=30),
        ],
        matches=[
            MatchRecord(map="Ascent", agent="Omen",      kda="14/9/7",  hs_pct=49, adr=172, suspicion=27, won=True),
            MatchRecord(map="Sunset", agent="Omen",      kda="11/11/8", hs_pct=45, adr=155, suspicion=30, won=False),
            MatchRecord(map="Lotus",  agent="Brimstone", kda="13/8/12", hs_pct=48, adr=168, suspicion=28, won=True),
            MatchRecord(map="Haven",  agent="Omen",      kda="12/10/6", hs_pct=44, adr=161, suspicion=31, won=True),
            MatchRecord(map="Bind",   agent="Brimstone", kda="10/12/9", hs_pct=47, adr=158, suspicion=29, won=False),
        ],
        hs_history=[42,45,44,47,46,48,45,47,46,47],
        suspicion_history=[30,28,31,27,29,28,30,29,28,29],
    ),
    "snipegod#kr3": AnalysisResult(
        name="SnipeGod", tag="KR3", rank="Diamond 1 #241", region="kr",
        suspicion_pct=67, verdict=Verdict.SUSPECT, demo=True,
        stats=PlayerStats(avg_hs_pct=73.0, avg_kda=4.1, avg_adr=241, win_rate=63.0, games_analyzed=10),
        subsystems=SubsystemScores(stat_anomaly=72, physics=58, ml_ensemble=64, trust_score=51),
        flags=[
            Flag(severity="red",   title="HS율 10경기 내 +32%p 급상승",   detail="41% → 73% · 통계적 이상 변화율",       source="stat"),
            Flag(severity="amber", title="반응 일관성 비정상",              detail="σ=8ms — 정상 25–50ms 대비 과도히 일정", source="physics"),
            Flag(severity="amber", title="비가시 구역 pre-aim 38% 일치",   detail="연막·벽 너머 선점 조준 패턴 다수",      source="physics"),
        ],
        ml_votes=[
            MLVote(model="Random Forest",    confidence=68),
            MLVote(model="XGBoost",          confidence=65),
            MLVote(model="LSTM (시계열)",     confidence=61),
            MLVote(model="Isolation Forest", confidence=57),
            MLVote(model="k-NN",             confidence=66),
        ],
        matches=[
            MatchRecord(map="Icebox", agent="Chamber", kda="22/6/3",  hs_pct=76, adr=258, suspicion=70, won=True),
            MatchRecord(map="Sunset", agent="Chamber", kda="19/8/5",  hs_pct=74, adr=247, suspicion=67, won=True),
            MatchRecord(map="Ascent", agent="Chamber", kda="17/9/7",  hs_pct=71, adr=233, suspicion=65, won=False),
            MatchRecord(map="Haven",  agent="Chamber", kda="20/7/4",  hs_pct=73, adr=251, suspicion=68, won=True),
            MatchRecord(map="Bind",   agent="Jett",    kda="15/10/6", hs_pct=69, adr=224, suspicion=63, won=False),
        ],
        hs_history=[41,43,45,48,53,58,63,67,70,73],
        suspicion_history=[35,38,40,44,50,55,59,62,65,67],
    ),
}
