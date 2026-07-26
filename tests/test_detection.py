"""Unit tests for backend/services/detection.py"""
import pytest

from backend.services.detection import (
    MatchData,
    compute_final,
    compute_evidence_confidence,
    compute_trust,
    run_ml_ensemble,
    run_physics_check,
    run_stat_anomaly,
)


def _match(hs: float = 0.50, kda: float = 1.5, adr: int = 150, won: bool = True) -> MatchData:
    return MatchData(hs=hs, kda=kda, adr=adr, won=won)


# ── run_stat_anomaly ──────────────────────────────────────────────────────────

class TestStatAnomaly:
    def test_empty_input_returns_zero(self):
        result = run_stat_anomaly([])
        assert result.score == 0.0
        assert result.flags == []

    def test_normal_player_low_score(self):
        matches = [_match(hs=0.48) for _ in range(10)]
        result = run_stat_anomaly(matches)
        assert result.score < 0.20
        assert not any(f.severity == "red" for f in result.flags)

    def test_high_hs_rate_triggers_red_flag(self):
        matches = [_match(hs=0.92) for _ in range(10)]
        result = run_stat_anomaly(matches)
        assert result.score > 0.30
        assert any(f.severity == "red" and "헤드샷율" in f.title for f in result.flags)

    def test_hs_spike_triggers_amber_flag(self):
        # early 5 games: 41%, late 5 games: 73% → +32%p > threshold(25%)
        matches = [_match(hs=0.41)] * 5 + [_match(hs=0.73)] * 5
        result = run_stat_anomaly(matches)
        assert any(f.severity == "amber" and "급상승" in f.title for f in result.flags)

    def test_high_kda_triggers_red_flag(self):
        matches = [_match(hs=0.50, kda=8.5) for _ in range(5)]
        result = run_stat_anomaly(matches)
        assert any(f.severity == "red" and "K/D" in f.title for f in result.flags)

    def test_score_capped_at_one(self):
        # Worst possible stats — score must not exceed 1.0
        matches = [_match(hs=0.99, kda=15.0) for _ in range(10)]
        result = run_stat_anomaly(matches)
        assert result.score <= 1.0

    def test_consistency_flag_with_uniform_high_hs(self):
        # Extremely consistent and high HS → suspicious
        matches = [_match(hs=0.92)] * 8
        result = run_stat_anomaly(matches)
        flag_titles = [f.title for f in result.flags]
        assert any("일관성" in t for t in flag_titles)


# ── run_physics_check ─────────────────────────────────────────────────────────

class TestPhysicsCheck:
    def test_empty_input_returns_zero(self):
        result = run_physics_check([])
        assert result.score == 0.0

    def test_normal_returns_green_flag(self):
        matches = [_match(hs=0.48, kda=1.5) for _ in range(5)]
        result = run_physics_check(matches)
        assert any(f.severity == "green" for f in result.flags)

    def test_very_high_hs_triggers_red(self):
        matches = [_match(hs=0.95, kda=3.0) for _ in range(5)]
        result = run_physics_check(matches)
        assert result.score >= 0.50
        assert any(f.severity == "red" for f in result.flags)

    def test_extreme_kda_triggers_red(self):
        matches = [_match(hs=0.50, kda=9.0) for _ in range(5)]
        result = run_physics_check(matches)
        assert any("KDA" in f.title for f in result.flags)


# ── run_ml_ensemble ───────────────────────────────────────────────────────────

class TestMlEnsemble:
    def test_empty_returns_zero(self):
        score, votes = run_ml_ensemble([])
        assert score == 0.0
        assert votes == []

    def test_cheater_profile_high_score(self):
        matches = [_match(hs=0.94, kda=8.4) for _ in range(10)]
        score, votes = run_ml_ensemble(matches)
        assert score > 0.70
        assert len(votes) == 5
        assert all(v.confidence > 70 for v in votes)

    def test_clean_profile_low_score(self):
        matches = [_match(hs=0.44, kda=1.8) for _ in range(10)]
        score, votes = run_ml_ensemble(matches)
        assert score < 0.40

    def test_confidence_in_valid_range(self):
        matches = [_match(hs=0.90, kda=7.0) for _ in range(5)]
        _, votes = run_ml_ensemble(matches)
        for v in votes:
            assert 1 <= v.confidence <= 99


# ── compute_trust ─────────────────────────────────────────────────────────────

class TestComputeTrust:
    def test_empty_matches_returns_fifty(self):
        assert compute_trust([]) == 50

    def test_many_normal_games_high_trust(self):
        matches = [_match(hs=0.47, won=True) for _ in range(100)]
        trust = compute_trust(matches)
        assert trust > 50

    def test_high_hs_reduces_trust(self):
        clean   = [_match(hs=0.47) for _ in range(50)]
        suspect = [_match(hs=0.90) for _ in range(50)]
        assert compute_trust(clean) > compute_trust(suspect)

    def test_trust_stays_in_bounds(self):
        for hs in [0.10, 0.50, 0.95]:
            for n in [1, 10, 200]:
                t = compute_trust([_match(hs=hs) for _ in range(n)])
                assert 5 <= t <= 95


class TestEvidenceConfidence:
    def test_more_matches_and_agreement_raise_confidence(self):
        small = [_match(hs=0.50, kda=1.5)]
        large = [_match(hs=0.50, kda=1.5) for _ in range(10)]
        low = compute_evidence_confidence(small, 0.1, 0.8, 0.2)
        high = compute_evidence_confidence(large, 0.4, 0.42, 0.41)
        assert high > low

    def test_confidence_stays_in_calibrated_range(self):
        matches = [_match(hs=0.95, kda=8.0) for _ in range(20)]
        score = compute_evidence_confidence(matches, 1.0, 1.0, 1.0)
        assert 35 <= score <= 95


# ── compute_final ─────────────────────────────────────────────────────────────

class TestComputeFinal:
    def test_all_zero_scores_with_mid_trust(self):
        result = compute_final(0.0, 0.0, 0.0, 50)
        # trust=50 → trust_factor=0.5, weight=0.15 → 0.075 * 100 = 7
        assert 1 <= result <= 20

    def test_all_max_scores_low_trust_near_99(self):
        result = compute_final(1.0, 1.0, 1.0, 5)
        assert result >= 95

    def test_result_always_in_range(self):
        for stat in [0.0, 0.5, 1.0]:
            for phys in [0.0, 0.5, 1.0]:
                for trust in [5, 50, 95]:
                    r = compute_final(stat, phys, 0.5, trust)
                    assert 1 <= r <= 99
