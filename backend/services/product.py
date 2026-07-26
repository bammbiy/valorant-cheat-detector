from __future__ import annotations

from backend.models.product import ModelReport, ModelSignal, QualityReport


def get_quality_report() -> QualityReport:
    """모델 품질 화면에 표시할 검증 상태와 한계를 반환한다."""
    return QualityReport(
        status="prototype",
        benchmark_label="프로토타입 예시 수치 · 실측 검증 전",
        accuracy=96.3,
        false_positive_rate=0.8,
        sample_count=2_400_000,
        coverage=62.0,
        calibration="검증 데이터셋 연결 전",
        validation_method="시간 분할 교차검증 예정",
        limitations=[
            "현재 데모 수치는 제품 UI 검증용이며 실제 판정 성능을 보장하지 않습니다.",
            "공개 매치 집계 데이터만 사용하므로 원시 에임·마우스 텔레메트리를 판정하지 않습니다.",
            "자동 제재가 아닌 검토 보조용 신호로만 사용합니다.",
        ],
    )


def get_model_report() -> ModelReport:
    """탐지 신호와 모델 운영 안전장치를 반환한다."""
    return ModelReport(
        version="detection-proxy v0.2",
        decision_policy="독립 신호 2개 이상 일치 시 review queue 등록",
        signals=[
            ModelSignal(
                name="통계 이상",
                role="HS율·KDA·경기 간 변화",
                status="active",
                limitation="역할·맵·패치별 기준선이 필요합니다.",
            ),
            ModelSignal(
                name="행동 이상 프록시",
                role="집계 스탯에서 비정상 패턴 추정",
                status="proxy",
                limitation="물리적 에임이나 메모리를 직접 관측하지 않습니다.",
            ),
            ModelSignal(
                name="ML 앙상블",
                role="보정된 위험 점수와 모델 간 합의",
                status="calibration pending",
                limitation="라벨 데이터와 시간 분할 검증이 필요합니다.",
            ),
            ModelSignal(
                name="누적 신뢰도",
                role="표본 수와 장기 일관성 반영",
                status="active",
                limitation="표본이 적으면 confidence가 낮게 유지됩니다.",
            ),
        ],
        safeguards=[
            "게임 메모리·DLL·패킷·안티치트 우회에 접근하지 않습니다.",
            "의심도는 제재나 공개 낙인을 위한 판정값이 아닙니다.",
            "표본 수와 데이터 소스를 모든 분석 결과에 함께 표시합니다.",
        ],
    )
