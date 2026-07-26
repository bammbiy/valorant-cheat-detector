# plan.md — ValoScan 개선 구현 계획

> 상태: ✅ 승인됨  
> 작성: 2025-04-21  
> 기반: research.md Gap 목록 + CLAUDE.md 규칙

---

## 목표

research.md에서 발견한 Gap 해결 + 워크플로우 인프라(린터, pre-commit, GC 에이전트) 추가

---

## 변경 범위

### [1] detection.py — ML 매직 넘버 config 이동
```python
# before (detection.py)
_MODELS = [
    ("Random Forest",    0.97),
    ...
]

# after (config.py에 추가)
ml_model_scales: list[float] = [0.97, 0.94, 0.91, 0.88, 0.95]
ml_model_names: list[str] = ["Random Forest","XGBoost","LSTM (시계열)","Isolation Forest","k-NN"]
```

### [2] analyzer.py — asyncio.gather로 병렬 fetch
```python
# before
for mid in match_ids[:limit]:
    detail = await client.get_match(mid, platform)

# after
tasks = [client.get_match(mid, platform) for mid in match_ids[:limit]]
results = await asyncio.gather(*tasks, return_exceptions=True)
# return_exceptions=True → 개별 실패가 전체를 죽이지 않음
```

### [3] detection.py — stdev 실패 시 로깅
```python
except statistics.StatisticsError as e:
    logging.warning("stdev 계산 실패: %s (샘플 수: %d)", e, len(hs_vals))
```

### [4] tests/ 추가
- `tests/test_detection.py`: 빈 입력, 높은 HS, trust 경계값
- `tests/test_analyzer.py`: demo mode fixture 반환 확인
- pytest + httpx AsyncClient로 실제 라우터 테스트

### [5] 린터 + pre-commit 설정
- `ruff` (linting + formatting)
- `mypy` (strict type check)
- `.pre-commit-config.yaml`
- `pyproject.toml`

### [6] 가비지 컬렉션 에이전트
- `scripts/gc_agent.py`: 코드베이스 주기적 점검 스크립트
  - 미사용 import 탐지
  - TODO 주석 탐지 → 경고
  - 함수 길이 50줄 초과 탐지
  - `demo_data.py` 직접 import 여부 탐지

---

## 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `backend/core/config.py` | ML 관련 설정 추가 |
| `backend/services/detection.py` | config 참조, 로깅 추가 |
| `backend/services/analyzer.py` | asyncio.gather 병렬화 |
| `tests/test_detection.py` | 신규 생성 |
| `tests/test_analyzer.py` | 신규 생성 |
| `pyproject.toml` | 신규 생성 |
| `.pre-commit-config.yaml` | 신규 생성 |
| `scripts/gc_agent.py` | 신규 생성 |

---

## 완료 체크리스트

- [x] CLAUDE.md 작성
- [x] research.md 작성
- [x] plan.md 작성
- [x] config.py ML 설정 추가
- [x] detection.py 리팩터 (서브함수 분리, 로깅, 매직넘버 제거)
- [x] analyzer.py 병렬화 (asyncio.gather)
- [x] tests/ 작성 (test_detection.py, test_analyzer.py)
- [x] pyproject.toml (ruff, mypy, pytest 설정)
- [x] .pre-commit-config.yaml
- [x] scripts/gc_agent.py
- [x] scripts/hooks/ (4개 훅 스크립트)

## ValoScan Next: 멀티게임 분석 플랫폼과 안전한 알림

### 제품 방향

- VALORANT와 Overwatch를 `GameAdapter` 인터페이스로 묶고, 게임별 데이터 수집기와 탐지 모델은 분리한다.
- 결과는 핵 확정이 아니라 `clean / review / high-risk`의 근거 기반 위험 신호로 표시한다.
- 실시간 기능은 게임 메모리, DLL, 패킷, 안티치트 우회에 접근하지 않는다.
- 상대방 실시간 스카우팅 오버레이는 기본 기능으로 제공하지 않고, 경기 후 리포트·관전자/리뷰 모드 알림을 우선한다.

### 단계별 구현

#### Phase 1 — 기반 정리

- `backend/services/games/` 아래에 `GameAdapter`, `ValorantAdapter`, `OverwatchAdapter`를 추가한다.
- `AnalysisResult`에 `game`, `data_source`, `confidence`, `evidence_quality`, `limitations`를 추가한다.
- 공개 매치 집계 데이터만으로 물리적 에임을 판정할 수 없으므로 `physics check`는 `behavioral anomaly proxy`로 노출한다.
- 한국어 UI의 인코딩 깨짐을 제거하고 게임 선택 → 분석 → 근거 확인 흐름으로 재구성한다.

#### Phase 2 — Overwatch 분석

- Blizzard 공식 공개 API에서 제공되는 범위를 먼저 검증한다. 공식 매치 히스토리/실시간 경기 데이터가 없으면 허용된 리플레이·영상·수동 이벤트 소스만 지원한다.
- 영웅·역할·맵·모드별로 특징량을 분리하고, 서로 다른 역할을 같은 기준으로 비교하지 않는다.
- 표본 수, 패치 버전, 모드, 영웅별 플레이시간을 신뢰도에 반영한다.

#### Phase 3 — 실시간 알림 에이전트

- 웹앱은 분석·대시보드, 별도 로컬 에이전트는 알림·세션 상태를 담당한다.
- 1차 알림은 Windows toast·트레이 아이콘·웹 푸시로 제공하고, 게임 화면 위에 플레이어 식별 정보를 그리지 않는다.
- 알림에는 위험 점수보다 근거, 표본 수, 마지막 업데이트 시각, `review needed` 상태를 표시한다.
- 사용자 동의, 알림 끄기, 로그 보존 기간, 오탐 신고 기능을 기본 제공한다.

#### Phase 4 — 정확도 개선

- 합성 데모 데이터가 아닌 라벨된 경기·리플레이 데이터셋을 먼저 만든다.
- 시간 분할 검증, 게임·패치·역할별 교차검증, calibration, precision/recall, false-positive rate를 대시보드로 공개한다.
- 독립된 근거가 2개 이상 일치할 때만 high-risk로 올리고, 자동 제재나 공개 낙인 대신 review queue로 연결한다.

#### Phase 5 — 제품화/디자인

- MVP는 반응형 웹으로 유지하고, 로컬 알림이 필요할 때만 Tauri 데스크톱 셸을 추가한다.
- 다크 분석 콘솔은 유지하되 상태 배지·근거 카드·신뢰도·표본 수를 함께 보여준다.
- 홈, 분석 결과, 라이브 알림 센터, 데이터 품질/모델 설명, 설정의 5개 화면으로 구성한다.
