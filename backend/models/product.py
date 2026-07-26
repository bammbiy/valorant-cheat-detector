from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class QualityReport(BaseModel):
    status: str
    benchmark_label: str
    accuracy: Optional[float]
    false_positive_rate: Optional[float]
    sample_count: int
    coverage: float
    calibration: str
    validation_method: str
    limitations: List[str]


class ModelSignal(BaseModel):
    name: str
    role: str
    status: str
    limitation: str


class ModelReport(BaseModel):
    version: str
    decision_policy: str
    signals: List[ModelSignal]
    safeguards: List[str]
