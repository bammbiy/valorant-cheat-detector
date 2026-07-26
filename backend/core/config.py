from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    riot_api_key: str = "RGAPI-DEMO"
    demo_mode: bool = True

    # Riot routing — in .env pass as JSON:
    #   REGION_PLATFORM='{"kr":"kr","ap":"ap","eu":"eu","na":"na1"}'
    region_platform: Dict[str, str] = {
        "kr": "kr", "ap": "ap", "eu": "eu", "na": "na1",
    }
    region_routing: Dict[str, str] = {
        "kr": "asia", "ap": "asia", "eu": "europe", "na": "americas",
    }

    # Detection thresholds
    hs_normal_avg: float = 0.52
    hs_alert: float = 0.80
    hs_spike_delta: float = 0.25
    hs_consistency_max_std: float = 0.04
    hs_consistency_min_avg: float = 0.60
    hs_physics_hard: float = 0.90
    hs_physics_soft: float = 0.75
    kda_alert: float = 6.0
    kda_physics_alert: float = 7.0

    # Subsystem weights — must sum to 1.0
    weight_stat: float = 0.30
    weight_phys: float = 0.30
    weight_ml: float = 0.25
    weight_trust: float = 0.15

    # ML ensemble
    ml_model_names: List[str] = [
        "Random Forest", "XGBoost", "LSTM (시계열)", "Isolation Forest", "k-NN",
    ]
    ml_model_scales: List[float] = [0.97, 0.94, 0.91, 0.88, 0.95]
    ml_logit_bias: float = -0.45

    # Evidence confidence calibration
    confidence_full_sample: int = 10
    confidence_min: int = 35
    confidence_max: int = 95

    # Trust score
    trust_games_to_max_base: int = 150
    trust_base_max: float = 50.0
    trust_base_bonus: float = 20.0
    trust_hs_hard_threshold: float = 0.80
    trust_hs_soft_threshold: float = 0.65
    trust_hs_hard_penalty: int = 25
    trust_hs_soft_penalty: int = 12
    trust_winrate_alert: float = 0.75
    trust_winrate_penalty: int = 15
    trust_min: int = 5
    trust_max: int = 95

    # API
    match_history_limit: int = 20
    match_detail_limit: int = 10
    http_timeout: float = 10.0

    @property
    def is_demo(self) -> bool:
        return self.demo_mode or self.riot_api_key == "RGAPI-DEMO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
