# research.md — ValoScan 코드베이스 심층 분석

> 생성: 2025-04-21  
> 목적: 리팩터링 전 현황 파악. 수정 전 반드시 읽을 것.

---

## 1. 데이터 흐름 전체 맵

```
HTTP GET /api/analyze/{region}/{name}/{tag}
  └─ routes.py::analyze()
       └─ analyzer.py::analyze_player()
            ├─ [demo mode] demo_data.py → AnalysisResult 즉시 반환
            └─ [live mode]
                 ├─ riot_client.py::get_account()      → puuid
                 ├─ riot_client.py::get_match_list()   → [match_id, ...]
                 ├─ riot_client.py::get_match() × N    → raw match dict
                 │
                 ├─ detection.py::run_stat_anomaly()   → SubsystemResult(score, flags)
                 ├─ detection.py::run_physics_check()  → SubsystemResult(score, flags)
                 ├─ detection.py::run_ml_ensemble()    → (float, [MLVote])
                 ├─ detection.py::compute_trust()      → int
                 └─ detection.py::compute_final()      → int  →  AnalysisResult
```

---

## 2. 핵심 파일별 분석

### backend/core/config.py
- `pydantic-settings` 기반. `.env` 파일 또는 환경변수로 주입
- `@lru_cache`로 싱글턴 보장 → 런타임 중 설정 변경 불가 (의도적)
- **주의**: `region_platform`, `region_routing`이 dict 타입인데 `.env`에서 JSON 문자열로 넣어야 함. 문서화 필요
- `is_demo` property: `riot_api_key == "RGAPI-DEMO"` OR `demo_mode=True` 중 하나라도 참이면 demo

### backend/models/analysis.py
- 모든 응답은 `AnalysisResult`로 직렬화
- `Verdict` Enum: `clean` | `suspect` | `cheater`
- `demo: bool = False` 필드가 있어 프론트엔드에서 DEMO 배지 표시 가능
- **gap**: `MatchRecord.hs_pct`가 float인데 프론트에서 `%` 없이 표시됨 → 단위 불일치 위험

### backend/services/detection.py

#### run_stat_anomaly(matches)
- HS율 절대값 → spike(5경기 윈도우) → 일관성(stddev) → KDA 순서로 점수 누적
- `score` cap: `min(score, 1.0)` → 최대 100%
- **gap**: `statistics.stdev`는 샘플 수 1이면 `StatisticsError` 발생. try/except로 감쌌지만 `pass`로 무시함 → 로그라도 남겨야 함

#### run_physics_check(matches)
- **중요 한계**: Riot 공개 API는 에임/마우스 원시 데이터를 제공하지 않음
- 현재 구현은 `avg_hs > 0.90` 등 집계 스탯으로 프록시 추정
- 코드 내 주석에 "Production: 커널 드라이버 필요" 명시됨 → 현재 physics 점수는 stat 점수의 변형에 가까움

#### run_ml_ensemble(matches)
- 실제 ML 없음. 로지스틱 함수로 단일 확률값 계산 후 5개 모델에 `scale` 계수 곱해 confidence 생성
- `_MODELS` 리스트의 scale 값들이 매직 넘버 (`0.97, 0.94, 0.91, 0.88, 0.95`)
- **gap**: `config.py`로 빼야 함

#### compute_trust(matches)
- `min(total / 3.0, 50)` → 150경기면 신뢰도 기본값 50
- 패널티: HS율 > 80% → -25, > 65% → -12, 승률 > 75% → -15
- 최종 `max(5, min(95, ...))` → 절대 0 또는 100이 되지 않음 (의도적)

#### compute_final(stat, phys, ml, trust)
- `trust_factor = (100 - trust) / 100` → trust가 낮을수록 의심도 상승
- 가중 합산 후 `× 100` → `int(min(99, max(1, ...)))` → 1~99 범위

### backend/services/analyzer.py
- per-match suspicion back-fill: 각 경기마다 단일 `MatchData`로 독립 분석 → 경기별 의심도
- **성능 gap**: `get_match()` N회 순차 호출. asyncio.gather로 병렬화 가능
- ADR proxy: `damage.dealt / rounds_played` → Riot API에 따라 필드명 다를 수 있음 (버전 확인 필요)

### frontend/static/js/app.js
- `API.analyze()` 하나의 fetch로 모든 데이터 수신
- 로딩 시퀀스는 실제 요청 진행과 무관한 fake log (UX 용도)
- `_charts` 객체에 Chart.js 인스턴스 저장 → 재렌더 시 `destroy()` 필수 (현재 구현됨)
- `colour()` 함수: 75% 이상 red, 45% 이상 amber, 그 이하 green → `config.py` 임계값과 동기화 필요

---

## 3. 발견된 Gap 목록

| # | 위치 | 문제 | 심각도 |
|---|------|------|--------|
| 1 | `detection.py` | ML scale 매직 넘버 → config로 이동 필요 | 낮음 |
| 2 | `detection.py` | `statistics.stdev` 실패 시 `pass` → 로깅 추가 필요 | 낮음 |
| 3 | `analyzer.py` | `get_match()` 순차 호출 → `asyncio.gather` 병렬화 | 중간 |
| 4 | `analyzer.py` | ADR 필드명 Riot API 버전에 따라 다름 → 방어 코드 | 중간 |
| 5 | `frontend/js/app.js` | colour() 임계값이 backend config와 분리됨 | 낮음 |
| 6 | `config.py` | dict 타입 env 설정 문서화 없음 | 낮음 |

---

## 4. 외부 의존성 버전 현황

```
fastapi         0.111+   # lifespan 이벤트 지원
uvicorn         0.29+    # HTTP/1.1 only (HTTP/2 미사용)
httpx           0.27+    # async client
pydantic        2.7+     # v2 API (v1 호환 레이어 없음)
pydantic-settings 2.2+
```

---

## 5. 테스트 현황

현재 테스트 없음. 추가해야 할 최소 케이스:
- `run_stat_anomaly([])` → score=0, flags=[]
- `run_stat_anomaly` with high HS → flags에 red 포함 확인
- `compute_trust([], )` → 50 반환 확인
- `analyze_player` demo mode → demo_data fixture 반환 확인
