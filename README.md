# ValoScan

발로란트 핵 의심도 분석기. Riot 공식 API 기반 전적 데이터를 4개 서브시스템으로 분석합니다.

## 구조

```
valoscan/
├── main.py                     # FastAPI 앱 진입점
├── requirements.txt
├── .env.example
├── backend/
│   ├── api/
│   │   └── routes.py           # GET /api/analyze/{region}/{name}/{tag}
│   ├── core/
│   │   └── config.py           # pydantic-settings 환경 설정
│   ├── models/
│   │   └── analysis.py         # Pydantic 응답 모델
│   └── services/
│       ├── riot_client.py      # Riot API HTTP 클라이언트
│       ├── detection.py        # 탐지 엔진 (stat / physics / ML / trust)
│       ├── analyzer.py         # 오케스트레이터
│       └── demo_data.py        # 데모 픽스처
└── frontend/
    ├── index.html
    └── static/
        ├── css/main.css
        └── js/app.js
```

## 실행

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 열어서 RIOT_API_KEY 입력

# 3. 서버 실행
python main.py

# 4. 브라우저
open http://localhost:8000
```

API 키 없이 실행하면 자동으로 demo 모드로 동작합니다.

## API

```
GET /api/analyze/{region}/{name}/{tag}
GET /api/health
GET /api/docs        # Swagger UI
```

## 탐지 로직

| 서브시스템 | 가중치 | 방식 |
|---|---|---|
| 통계 이상 | 30% | HS율 분포·스파이크·일관성, KDA 이상값 |
| 물리 불가능 | 30% | 집계 스탯 기반 프록시 추정 |
| ML 앙상블 | 25% | 로지스틱 회귀 (production에서 sklearn Pipeline으로 교체) |
| 누적 신뢰도 | 15% | 게임 수 × 통계 페널티 |

## 주의

- Riot 개발자 키는 24시간마다 갱신 필요 (분당 20 요청 제한)
- 비공개 전적 계정은 분석 불가
- 게임 메모리에 접근하지 않음 — Riot 공식 API만 사용
