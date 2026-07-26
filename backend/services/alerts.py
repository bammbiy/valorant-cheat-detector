from __future__ import annotations

import time
from collections import deque
from typing import Deque, List, Optional

from backend.models.alerts import Alert, AlertSeverity
from backend.models.analysis import AnalysisResult, GameId

_ALERT_RETENTION_SECONDS = 600
_alerts: Deque[Alert] = deque(maxlen=50)


def record_analysis_alert(result: AnalysisResult) -> None:
    """고위험 분석 결과를 중복 없이 로컬 알림 큐에 기록한다."""
    if result.suspicion_pct < 75:
        return

    now = time.time()
    recent = next(
        (
            alert
            for alert in reversed(_alerts)
            if alert.player == result.name and now - alert.created_at < _ALERT_RETENTION_SECONDS
        ),
        None,
    )
    if recent is not None:
        return

    severity = AlertSeverity.HIGH_RISK if result.suspicion_pct >= 85 else AlertSeverity.REVIEW
    _alerts.append(
        Alert(
            id=f"{result.game.value}:{result.name}:{int(now)}",
            game=result.game,
            player=f"{result.name}#{result.tag}",
            suspicion_pct=result.suspicion_pct,
            severity=severity,
            title="검토 필요 분석 결과",
            detail=f"{result.suspicion_pct}% 의심도 · {result.stats.games_analyzed}경기 표본 · 자동 제재 없음",
            created_at=now,
        )
    )


def list_alerts(game: Optional[GameId] = None, since: float = 0.0) -> List[Alert]:
    """지정 게임과 시각 이후의 로컬 알림을 반환한다."""
    cutoff = time.time() - _ALERT_RETENTION_SECONDS
    return [
        alert
        for alert in _alerts
        if alert.created_at >= max(cutoff, since)
        and (game is None or alert.game == game)
    ]
