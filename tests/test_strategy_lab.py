"""Synthetic tests only. No restricted competition data enters CI."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from backtest import compare, evaluate_holdout, match_draws, sorted_baselines, assess
from cricsheet_adapter import iter_rows
from tactics import optimize, phase


class StrategyLabTests(unittest.TestCase):
    def test_holdout_exposure_and_player_equal_weighting(self):
        hold = pd.DataFrame([
            {"pid": 1, "match_id": 1, "high_pressure": True, "units": 2, "residual": 3.0},
            {"pid": 2, "match_id": 1, "high_pressure": True, "units": 1, "residual": -1.0},
            {"pid": 3, "match_id": 1, "high_pressure": False, "units": 30, "residual": 50.0},
        ])
        summary = evaluate_holdout(hold, [1, 2, 3], draws=0, min_units=1)
        self.assertEqual(summary["evaluated"], 2)
        self.assertEqual(summary["missing_or_thin_player_ids"], [3])
        self.assertEqual(summary["pressure_opportunities"], 3)
        self.assertAlmostEqual(summary["future_mean_per_100"], 25.0)
        self.assertAlmostEqual(summary["opportunity_weighted_per_100"], 200 / 3)

    def test_shared_match_draws_cancel_when_membership_is_identical(self):
        hold = pd.DataFrame([
            {"pid": 1, "match_id": 1, "high_pressure": True, "units": 5, "residual": 3.0},
            {"pid": 2, "match_id": 2, "high_pressure": True, "units": 5, "residual": -2.0},
        ])
        choices = {"robust_pressure": [1, 2], "balanced_form": [2, 1]}
        result = compare(hold, choices, {1: "A", 2: "B"}, [1, 2], match_draws([1, 2], 100), 1)
        self.assertEqual(result["balanced_form"]["paired_difference_interval_95"], [0.0, 0.0])

    def test_empty_holdout_coverage_returns_missing_not_zero(self):
        hold = pd.DataFrame([
            {"pid": 1, "match_id": 1, "high_pressure": True, "units": 5, "residual": 3.0},
            {"pid": 1, "match_id": 2, "high_pressure": False, "units": 10, "residual": 30.0},
        ])
        result = evaluate_holdout(hold, [1], draws=10, min_units=10)
        self.assertEqual(result["evaluated"], 0)
        self.assertIsNone(result["future_mean_per_100"])
        self.assertIsNone(result["opportunity_weighted_per_100"])

    def test_baselines_only_rank_training_candidates(self):
        d = pd.DataFrame([{"pid": 1, "residual": 2, "units": 1, "high_pressure": True, "year": 2024},
                          {"pid": 2, "residual": 3, "units": 1, "high_pressure": True, "year": 2024},
                          {"pid": 3, "residual": 100, "units": 1, "high_pressure": True, "year": 2024}])
        rankings = sorted_baselines(d, [1, 2], 2024)
        self.assertTrue(all(3 not in picks for picks in rankings.values()))
        self.assertEqual(rankings["pressure_only"][:2], [2, 1])

    def test_reject_overlapping_train_and_holdout(self):
        train = pd.DataFrame([{"match_date": "2025-02-01"}])
        later = pd.DataFrame([{"match_date": "2025-01-01"}])
        with self.assertRaises(AssertionError):
            assess(train, later, 2024, 10)

    def test_rotation_legality(self):
        costs = {"Powerplay": 8.0, "Middle": 8.0, "Death": 8.0}
        config = {"source": "user_estimates", "overs": 20, "max_overs_per_bowler": 4,
                  "bowlers": [{"name": f"B{i}", "expected_runs_per_over": costs} for i in range(5)]}
        result = optimize(config)
        rotation = [row["bowler"] for row in result["optimal_rotation"]]
        self.assertEqual(len(rotation), 20)
        self.assertTrue(all(rotation[i] != rotation[i-1] for i in range(1, 20)))
        self.assertTrue(all(rotation.count(b) == 4 for b in set(rotation)))
        self.assertAlmostEqual(result["optimized_expected_runs"], 160.0)
        self.assertEqual(phase(5), "Powerplay")
        self.assertEqual(phase(6), "Middle")
        self.assertEqual(phase(15), "Death")

    def test_invalid_rotation_inputs(self):
        with self.assertRaises(ValueError):
            optimize({"source": "model_measured", "bowlers": []})

    def test_cricsheet_wides_and_wicket(self):
        match = {"info": {"match_type": "T20", "dates": ["2024-01-01"]}, "innings": [
            {"team": "A", "overs": [{"over": 0, "deliveries": [
                {"batter": "X", "bowler": "Y", "runs": {"batter": 0, "extras": 1, "total": 1},
                 "extras": {"wides": 1}},
                {"batter": "X", "bowler": "Y", "runs": {"batter": 2, "extras": 0, "total": 2},
                 "wickets": [{"player_out": "X", "kind": "caught"}]}
            ]}]}]}
        rows = list(iter_rows(match, "fixture"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["legal"], 0)
        self.assertEqual(rows[1]["legal"], 1)
        self.assertEqual(rows[1]["striker_dismissed"], 1)


if __name__ == "__main__":
    unittest.main()
