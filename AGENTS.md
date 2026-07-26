# AGENTS.md — ValoScan 업무 지침서

> 이 파일은 매 세션 시작 시 가장 먼저 읽어야 한다.
> 에이전트가 실수할 때마다 한 줄씩 추가된다. 절대 삭제하지 말 것.

---

## 프로젝트 개요

발로란트 전적 기반 핵 의심도 분석 웹앱.
Riot 공식 API만 사용. 게임 메모리 접근 없음.

```
valoscan/
├── main.py                   # FastAPI 진입점 (uvicorn)
├── backend/
│   ├── api/routes.py         # 라우터 (GET /api/analyze, /api/health)
│   ├── core/config.py        # pydantic-settings (절대 하드코딩 금지)
│   ├── models/analysis.py    # Pydantic v2 응답 스키마
│   └── services/
│       ├── riot_client.py    # Riot API HTTP 클라이언트
│       ├── detection.py      # 탐지 엔진 4개 서브시스템
│       ├── analyzer.py       # 오케스트레이터
│       └── demo_data.py      # 데모 픽스처 (실제 API 없을 때)
└── frontend/
    ├── index.html
    ├── static/css/main.css
    └── static/js/app.js
```

---

## 절대 규칙 (위반 시 pre-commit에서 차단됨)

- API 키를 코드에 하드코딩하지 말 것 → `.env` 파일만 사용
- `Any` 타입 사용 금지 → 명시적 타입 필수
- `print()` 디버깅 금지 → `logging` 모듈 사용
- `except Exception` naked catch 금지 → 구체적 예외 명시
- 함수 하나가 50줄 초과하면 분리할 것
- `TODO` 주석을 커밋하지 말 것 → 이슈로 올리거나 구현하고 커밋
- `demo_data.py`를 프로덕션 로직에서 import하지 말 것 → `analyzer.py`만 거쳐야 함

---

## 아키텍처 결정 (변경 전 반드시 plan.md 작성)

- 탐지 로직은 `detection.py`에만 위치. `routes.py`에 비즈니스 로직 넣지 말 것
- 새 서브시스템 추가 시 `SubsystemScores` 모델도 함께 업데이트
- 가중치 변경은 `config.py`의 `weight_*` 필드로만
- 프론트엔드 → 백엔드 통신은 `/api/*` 엔드포인트만. 직접 Riot API 호출 금지

---

## 과거 실수 기록 (에이전트가 반복한 실수들)

- [ 2025-04-21 ] `routes.py`에 탐지 로직을 직접 작성했다가 `detection.py`로 이동함
- [ 2025-04-21 ] `hs_pct` 계산 시 `total_shots=0` 케이스를 처리 안 해서 ZeroDivisionError 발생
- [ 2025-04-21 ] `demo_data.py`를 `routes.py`에서 직접 import했다가 `analyzer.py` 레이어 우회 문제 발생

---

## 코드 스타일

- Python 3.11+, Pydantic v2, FastAPI 0.111+
- 타입 힌트 전부 명시 (return type 포함)
- 함수 docstring: 한 줄 요약 + Args/Returns (퍼블릭 함수만)
- 상수는 `config.py`로, 매직 넘버 금지
