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
