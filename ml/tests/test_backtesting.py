import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from src.backtesting.run import replay
from src.backtesting.evaluate import evaluate
from src.backtesting.prepare_snapshot import prepare
from src.config import MODEL_DIR


class ReplayTests(unittest.TestCase):
    """All weather and actuals here are synthetic fixtures, not real February data."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, start="2026-02-01", days=2):
        batches = []
        for day in pd.date_range(start, periods=days, freq="D"):
            for turbine in (1, 2):
                filename = f"t{turbine}_{day.date()}.csv"
                weather = pd.DataFrame({"timestamp": pd.date_range(day, periods=48, freq="h"),
                                        "forecast_origin": day, "wind_speed": 6., "temperature": 15.,
                                        "latitude": 43.64, "longitude": 78.53})
                weather.to_csv(self.root / filename, index=False)
                batches.append({"file": filename, "turbine_id": turbine, "forecast_origin": str(day),
                                "weather_run_available_at": str(day - pd.Timedelta(hours=6)),
                                "sha256": hashlib.sha256((self.root / filename).read_bytes()).hexdigest()})
        manifest = {"timezone": "Asia/Almaty", "data_kind": "archived_forecast",
                    "source": "SYNTHETIC TEST FIXTURE - not actual archived weather", "batches": batches}
        path = self.root / "manifest.json"
        path.write_text(json.dumps(manifest))
        return path, manifest

    def run_replay(self, path):
        return replay(path, self.root / "run", "2026-02-01", "2026-02-02", model_dir=MODEL_DIR)

    def test_overlapping_targets_keep_distinct_origins_and_evaluate_separately(self):
        path, _ = self.manifest()
        predictions = self.run_replay(path)
        self.assertEqual(len(predictions), 192)
        self.assertTrue(predictions.duplicated(["turbine_id", "timestamp"]).any())
        self.assertFalse(predictions.duplicated(["forecast_origin", "turbine_id", "timestamp"]).any())
        actual = predictions[["timestamp", "turbine_id", "predicted_power"]].drop_duplicates(["timestamp", "turbine_id"])
        actual = actual.rename(columns={"predicted_power": "power_mean"}).iloc[1:]
        actual.to_csv(self.root / "synthetic_actuals.csv", index=False)
        before = (self.root / "run/predictions.csv").read_bytes()
        with patch("src.inference.predict.predict_with_models", side_effect=AssertionError("evaluation must not predict")):
            result = evaluate(self.root / "run", self.root / "synthetic_actuals.csv", self.root / "evaluation.json")
        self.assertGreater(result["missing_label_pairs"], 0)
        self.assertEqual(result["turbines"]["1"]["metrics"]["overall"]["mae"], 0.)
        self.assertEqual(before, (self.root / "run/predictions.csv").read_bytes())

    def test_future_weather_run_rejected_before_output(self):
        path, manifest = self.manifest()
        manifest["batches"][0]["weather_run_available_at"] = "2026-02-01 01:00"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Leakage guard"):
            self.run_replay(path)
        self.assertFalse((self.root / "run").exists())

    def test_manifest_missing_batch_and_duplicate_rejected(self):
        path, manifest = self.manifest()
        original = list(manifest["batches"])
        for batches in (original[:-1], original + [original[0]]):
            manifest["batches"] = batches
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.run_replay(path)

    def test_changed_weather_hash_rejected(self):
        path, manifest = self.manifest()
        (self.root / manifest["batches"][0]["file"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.run_replay(path)

    def test_power_column_cannot_enter_replay(self):
        path, manifest = self.manifest()
        batch = manifest["batches"][0]
        file = self.root / batch["file"]
        frame = pd.read_csv(file)
        frame["power_mean"] = .5
        frame.to_csv(file, index=False)
        batch["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "never actual power"):
            self.run_replay(path)

    def test_january_requires_earlier_model(self):
        path, _ = self.manifest("2026-01-31", 1)
        with self.assertRaisesRegex(ValueError, "early-model-dir"):
            replay(path, self.root / "run", "2026-01-31", "2026-01-31")
        with self.assertRaisesRegex(ValueError, "Leakage guard"):
            replay(path, self.root / "run", "2026-01-31", "2026-01-31", early_model_dir=MODEL_DIR)

    def test_january_snapshot_and_february_model_switch(self):
        path, _ = self.manifest("2026-01-31", 2)
        predictions = replay(path, self.root / "run", "2026-01-31", "2026-02-01",
                             early_model_dir=MODEL_DIR / "asof_2026-01-31")
        self.assertEqual(len(predictions), 192)
        for turbine in (1, 2):
            versions = predictions.loc[predictions.turbine_id.eq(turbine)].groupby("forecast_origin").model_version.first()
            self.assertEqual(versions.nunique(), 2)

    def test_tampered_predictions_and_duplicate_labels_rejected(self):
        path, _ = self.manifest()
        predictions = self.run_replay(path)
        label = pd.DataFrame({"timestamp": ["2026-02-01", "2026-02-01"], "turbine_id": [1, 1], "power_mean": [.2, .2]})
        actuals = self.root / "synthetic_actuals.csv"
        label.to_csv(actuals, index=False)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluate(self.root / "run", actuals, self.root / "score.json")
        predictions.loc[0, "predicted_power"] = .99
        predictions.to_csv(self.root / "run/predictions.csv", index=False)
        with self.assertRaisesRegex(ValueError, "modified"):
            evaluate(self.root / "run", actuals, self.root / "score.json")

    def test_snapshot_cutoff_and_overwrite_guards(self):
        with self.assertRaisesRegex(ValueError, "selection"):
            prepare("2025-11-01", self.root / "snapshot")
        with self.assertRaises(ValueError):
            prepare("2026-02-02", self.root / "snapshot")
        with self.assertRaisesRegex(ValueError, "new directory"):
            prepare("2026-01-31", self.root)


if __name__ == "__main__":
    unittest.main()
