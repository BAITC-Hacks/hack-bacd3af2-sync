import unittest
import numpy as np
import pandas as pd
from src.features.build_features import build_features
from src.training.validation import validate_history, training_before, forecast_pairs
from src.training.baselines import historical_baselines, EmpiricalPowerCurve
from src.training.evaluate import metrics


def history(start="2025-01-01", periods=240):
    times = pd.date_range(start, periods=periods, freq="h")
    result = pd.DataFrame({"timestamp": times, "available_at": times + pd.Timedelta(hours=1),
                          "power_mean": np.arange(periods) % 24 / 24,
                          "wind_speed_mean": 5., "temperature_mean": 10., "training_eligible": True})
    for col in ("observation_count", "wind_speed_count", "temperature_count", "power_count"):
        result[col] = 6
    return result


class LeakageTests(unittest.TestCase):
    def test_february_is_rejected_even_when_ineligible(self):
        frame = history("2026-01-31", 25)
        frame.loc[24, "training_eligible"] = False
        with self.assertRaisesRegex(ValueError, "February"):
            validate_history(frame)

    def test_last_january_hour_is_allowed_at_midnight_only(self):
        frame = history("2026-01-31", 24)
        validate_history(frame)
        self.assertEqual(len(training_before(frame, "2026-01-31 23:00")), 23)
        self.assertEqual(len(training_before(frame, "2026-02-01")), 24)
        with self.assertRaises(ValueError):
            training_before(frame, "2026-02-02")

    def test_forged_availability_fails(self):
        frame = history()
        frame["available_at"] = frame.timestamp
        with self.assertRaisesRegex(ValueError, "interval end"):
            validate_history(frame)

    def test_train_cutoff_excludes_future_targets(self):
        frame = history()
        train = training_before(frame, "2025-01-04")
        frame.loc[frame.timestamp.ge("2025-01-04"), "power_mean"] = 1000
        pd.testing.assert_frame_equal(train, training_before(frame, "2025-01-04"))

    def test_baselines_ignore_all_future_power_for_both_days(self):
        frame = history()
        pairs = forecast_pairs(frame, "2025-01-04", "2025-01-06")
        original, _ = historical_baselines(frame, pairs)
        frame.loc[frame.timestamp.ge("2025-01-04"), "power_mean"] = 999
        changed, _ = historical_baselines(frame, pairs)
        for name in original:
            np.testing.assert_array_equal(original[name], changed[name])
        np.testing.assert_array_equal(original["seasonal_persistence"][:24], original["seasonal_persistence"][24:])

    def test_missing_targets_preserve_horizon_and_seasonal_fallback(self):
        frame = history()
        frame.loc[frame.timestamp.eq("2025-01-04 01:00"), "training_eligible"] = False
        frame.loc[frame.timestamp.eq("2025-01-03 01:00"), "training_eligible"] = False
        pairs = forecast_pairs(frame, "2025-01-04", "2025-01-06")
        self.assertNotIn(2, pairs.horizon_hour.tolist())
        self.assertIn(48, pairs.horizon_hour.tolist())
        _, notes = historical_baselines(frame, pairs)
        self.assertEqual(notes["seasonal_fallback_rows"], 1)

    def test_features_ignore_target_and_diagnostics(self):
        weather = pd.DataFrame({"timestamp": pd.date_range("2025-01-01", periods=2, freq="h"),
                                "wind_speed": [3., 8.], "temperature": [0., 10.], "power_mean": [.1, .2]})
        before = build_features(weather)
        weather["power_mean"] = 999
        weather["wind_speed_std"] = 999
        pd.testing.assert_frame_equal(before, build_features(weather))
        self.assertNotIn("power_mean", before)
        self.assertEqual(before.wind_speed_cubed.tolist(), [27, 512])

    def test_invalid_weather_rejected(self):
        with self.assertRaises(ValueError):
            build_features(pd.DataFrame({"timestamp": [pd.Timestamp("2025-01-01")], "wind_speed": [-1], "temperature": [0]}))

    def test_curve_fits_only_supplied_rows_and_interpolates(self):
        model = EmpiricalPowerCurve().fit(pd.DataFrame({"wind_speed": [0., 10.]}), [0., 1.])
        np.testing.assert_allclose(model.predict(pd.DataFrame({"wind_speed": [0., 5., 10., 20.]})), [0, .5, 1, 1])

    def test_metrics_and_constant_target(self):
        result = metrics([0., 1.], [.25, .75])
        self.assertEqual(result["mae"], .25)
        self.assertEqual(result["rmse"], .25)
        self.assertEqual(result["r2"], .75)
        self.assertIsNone(metrics([1., 1.], [0., 0.])["r2"])


if __name__ == "__main__":
    unittest.main()
