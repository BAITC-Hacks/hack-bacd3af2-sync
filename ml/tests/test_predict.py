import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from src.config import MODEL_DIR, TIMEZONE
from src.inference.predict import predict_power, OUTPUT_COLUMNS
from src.inference.artifacts import clear_model_cache, get_model, ModelArtifactError, ModelBundle
from src.weather.schema import validate_weather


def weather(hours=24, origin="2026-02-01"):
    """Synthetic contract fixture, not archived forecasts or February observations."""
    return pd.DataFrame({"timestamp": pd.date_range(origin, periods=hours, freq="h"),
                         "forecast_origin": pd.Timestamp(origin), "wind_speed": np.linspace(0, 14, hours),
                         "temperature": 15., "latitude": 43.64, "longitude": 78.53})


class PredictTests(unittest.TestCase):
    def tearDown(self):
        clear_model_cache()

    def test_real_artifacts_both_turbines_and_horizons(self):
        with patch.dict(os.environ, {"TURBINE_MODEL_DIR": str(MODEL_DIR)}):
            for turbine in (1, 2):
                for horizon in (24, 48):
                    frame = weather(horizon)
                    original = frame.copy(deep=True)
                    result = predict_power(turbine, frame, horizon, pd.Timestamp("2026-02-01"))
                    self.assertEqual(list(result), OUTPUT_COLUMNS)
                    self.assertEqual(result.horizon_hour.tolist(), list(range(1, horizon+1)))
                    self.assertTrue(result.predicted_power.between(0, 1).all())
                    self.assertEqual(result.attrs["timezone"], TIMEZONE)
                    pd.testing.assert_frame_equal(frame, original)

    def test_aware_and_naive_predictions_match_and_rows_sort(self):
        frame = weather().sample(frac=1, random_state=42)
        expected = predict_power(1, frame, 24, pd.Timestamp("2026-02-01"))
        for column in ("timestamp", "forecast_origin"):
            frame[column] = frame[column].dt.tz_localize(TIMEZONE)
        actual = predict_power(1, frame, 24, pd.Timestamp("2026-02-01", tz=TIMEZONE))
        pd.testing.assert_frame_equal(expected, actual)

    def test_final_model_rejects_january_origin(self):
        with self.assertRaisesRegex(ValueError, "Leakage guard"):
            predict_power(1, weather(origin="2026-01-31"), 24, pd.Timestamp("2026-01-31"))

    def test_model_cache_and_missing_artifact(self):
        clear_model_cache()
        self.assertIs(get_model(1, MODEL_DIR), get_model(1, MODEL_DIR))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ModelArtifactError):
                get_model(1, folder)

    def test_corrupted_model_fails_hash_check(self):
        with tempfile.TemporaryDirectory() as folder:
            artifact = Path(folder) / "turbine_1"
            artifact.mkdir()
            metadata = json.loads((MODEL_DIR / "turbine_1" / "metadata.json").read_text())
            (artifact / "metadata.json").write_text(json.dumps(metadata))
            (artifact / "model.cbm").write_bytes(b"corrupted")
            with self.assertRaisesRegex(ModelArtifactError, "SHA-256"):
                get_model(1, folder)

    def test_clipping_is_logged_and_returned(self):
        class Fake:
            def predict(self, features):
                return np.full(len(features), 1.2)
        bundle = ModelBundle(Fake(), ("wind_speed", "temperature"), "test-only", pd.Timestamp("2026-02-01"))
        with patch("src.inference.predict.get_model", return_value=bundle), self.assertLogs("src.inference.predict", level="WARNING"):
            result = predict_power(1, weather(), 24, pd.Timestamp("2026-02-01"))
        self.assertEqual(result.attrs["diagnostics"]["clipped_above_one"], 24)
        self.assertTrue(result.predicted_power.eq(1).all())


class WeatherSchemaTests(unittest.TestCase):
    def check(self, frame, **overrides):
        params = {"turbine_id": 1, "weather": frame, "horizon_hours": 24, "forecast_origin": pd.Timestamp("2026-02-01")}
        params.update(overrides)
        return validate_weather(**params)

    def test_invalid_horizons_and_ids(self):
        for value in (0, 23, 25, 72, True, 24.):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(weather(), horizon_hours=value)
        for value in (0, 3, True, "1", 1.):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(weather(), turbine_id=value)

    def test_missing_duplicate_and_extra_hours_fail(self):
        duplicate = weather()
        duplicate.loc[1, "timestamp"] = duplicate.loc[0, "timestamp"]
        gap = weather()
        gap.loc[23, "timestamp"] += pd.Timedelta(hours=1)
        for frame in (weather().iloc[:-1], weather(48), duplicate, gap):
            with self.assertRaises(ValueError):
                self.check(frame)

    def test_missing_columns_values_and_physical_errors(self):
        with self.assertRaises(ValueError):
            self.check(weather().drop(columns="wind_speed"))
        for column, value in (("wind_speed", -1), ("wind_speed", np.inf), ("temperature", np.nan),
                              ("temperature", -274), ("latitude", 91), ("longitude", 181)):
            frame = weather()
            frame.loc[0, column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                self.check(frame)

    def test_mismatched_origin_timezone_and_location_fail(self):
        frame = weather()
        frame.loc[0, "forecast_origin"] += pd.Timedelta(hours=1)
        with self.assertRaises(ValueError):
            self.check(frame)
        frame = weather()
        frame["timestamp"] = frame.timestamp.dt.tz_localize("UTC")
        with self.assertRaises(ValueError):
            self.check(frame)
        frame = weather()
        frame.loc[0, "latitude"] = 40.
        with self.assertRaises(ValueError):
            self.check(frame)

    def test_regional_temperatures_are_preserved(self):
        frame = weather()
        frame.loc[0, "temperature"] = 1.4
        validated, _ = self.check(frame)
        np.testing.assert_array_equal(validated.temperature, frame.temperature)


if __name__ == "__main__":
    unittest.main()
