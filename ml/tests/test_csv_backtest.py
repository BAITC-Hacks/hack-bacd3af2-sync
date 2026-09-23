import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from src.config import MODEL_DIR
from src.backtesting.csv_replay import replay_csv, OUTPUT_COLUMNS
from src.backtesting.evaluate import evaluate


def synthetic_export(start="2026-01-31", periods=2):
    """Synthetic interface fixture, never real February observations."""
    parts = []
    for origin in pd.date_range(start, periods=periods, freq="D"):
        for turbine in (1, 2):
            times = pd.date_range(origin, periods=48, freq="h")
            parts.append(pd.DataFrame({"forecast_origin": origin, "timestamp": times, "turbine_id": turbine,
                                       "wind_speed": 6., "temperature": 1.4, "latitude": 43.64,
                                       "longitude": 78.53, "weather_valid_time": origin - pd.Timedelta(hours=1),
                                       "weather_source": "synthetic-test:run=" + (origin - pd.Timedelta(hours=12)).strftime("%Y-%m-%dT%H:%MZ")}))
    return pd.concat(parts, ignore_index=True)


class CSVBacktestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "february_backtest.csv"

    def tearDown(self):
        self.temp.cleanup()

    def run_csv(self, frame, **kwargs):
        frame.to_csv(self.path, index=False)
        return replay_csv(self.path, self.root / "run", start="2026-01-31", end="2026-02-01", **kwargs)

    def test_both_windows_format_overlaps_model_switch_and_no_network(self):
        frame = synthetic_export().sample(frac=1, random_state=42)
        with patch("socket.create_connection", side_effect=AssertionError("No network allowed")):
            results = self.run_csv(frame)
        for horizon, predictions in results.items():
            self.assertEqual(list(predictions), OUTPUT_COLUMNS)
            self.assertEqual(len(predictions), 4*horizon)
            self.assertEqual(predictions.horizon_hours.min(), 1)
            self.assertEqual(predictions.horizon_hours.max(), horizon)
            self.assertFalse(predictions.duplicated(["forecast_origin", "target_timestamp", "turbine_id"]).any())
            if horizon == 48:
                self.assertTrue(predictions.duplicated(["target_timestamp", "turbine_id"]).any())
            for turbine in (1, 2):
                self.assertEqual(predictions.loc[predictions.turbine_id.eq(turbine)].model_version.nunique(), 2)
            record = json.loads((self.root / "run" / f"{horizon}h/run.json").read_text())
            self.assertEqual(record["forecast_window_hours"], horizon)
            self.assertEqual(record["batches"][0]["weather_lead_hours_min"], 7.)
            self.assertEqual(record["batches"][0]["weather_lead_hours_max"], horizon + 6.)

    def test_full_month_expected_counts(self):
        synthetic_export(periods=29).to_csv(self.path, index=False)
        results = replay_csv(self.path, self.root / "run")
        self.assertEqual(len(results[24]), 1392)
        self.assertEqual(len(results[48]), 2784)
        self.assertEqual(results[48].forecast_origin.nunique(), 29)
        self.assertEqual(results[48].target_timestamp.max(), pd.Timestamp("2026-03-01 23:00"))

    def test_incomplete_and_duplicate_batches_fail_before_output(self):
        frame = synthetic_export()
        for broken in (frame.iloc[:-1], frame.loc[frame.turbine_id.eq(1)], pd.concat([frame, frame.iloc[:1]])):
            with self.assertRaises(ValueError):
                self.run_csv(broken)
            self.assertFalse((self.root / "run").exists())

    def test_bad_valid_time_and_future_power_field_fail(self):
        frame = synthetic_export()
        frame.loc[0, "weather_valid_time"] += pd.Timedelta(hours=1)
        with self.assertRaisesRegex(ValueError, "weather_valid_time"):
            self.run_csv(frame)
        frame = synthetic_export()
        frame["power_mean"] = .5
        with self.assertRaisesRegex(ValueError, "exactly"):
            self.run_csv(frame)

    def test_future_run_and_false_availability_rejected(self):
        frame = synthetic_export()
        frame.loc[0, "weather_source"] = "test:run=2026-01-31T00:00Z"
        with self.assertRaisesRegex(ValueError, "initialization"):
            self.run_csv(frame)
        frame = synthetic_export()
        frame.loc[0, "weather_valid_time"] = pd.Timestamp("2026-01-31 01:00")
        with self.assertRaisesRegex(ValueError, "Leakage guard"):
            self.run_csv(frame)

    def test_first_origin_rejects_final_models(self):
        with self.assertRaisesRegex(ValueError, "Leakage guard"):
            self.run_csv(synthetic_export(), early_model_dir=MODEL_DIR)
        self.assertFalse((self.root / "run").exists())

    def test_new_format_evaluation_separate_and_filters_january(self):
        results = self.run_csv(synthetic_export())
        labels = results[48][["target_timestamp", "turbine_id", "predicted_power"]].drop_duplicates(["target_timestamp", "turbine_id"])
        labels = labels.rename(columns={"target_timestamp": "timestamp", "predicted_power": "power_mean"})
        labels = labels.loc[labels.timestamp.ge("2026-02-01")]
        actuals = self.root / "synthetic_labels.csv"
        labels.to_csv(actuals, index=False)
        with patch("src.inference.predict.predict_with_models", side_effect=AssertionError("Do not predict")):
            for horizon in (24, 48):
                result = evaluate(self.root / f"run/{horizon}h", actuals, self.root / f"metrics_{horizon}.json")
                self.assertEqual(result["forecast_window_hours"], horizon)
                self.assertEqual(result["excluded_prediction_pairs_outside_target_interval"], 48)
                self.assertEqual(result["missing_label_pairs"], 0)
                self.assertIn("by_horizon", result["turbines"]["1"]["metrics"])

    def test_missing_export_fails_without_generating_data(self):
        with self.assertRaisesRegex(FileNotFoundError, "Backend weather export"):
            replay_csv(self.path, self.root / "run")
        self.assertFalse((self.root / "run").exists())
