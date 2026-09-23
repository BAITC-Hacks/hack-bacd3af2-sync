import unittest
import numpy as np
import pandas as pd
from src.data.preprocess import aggregate_hourly


class HourlyTests(unittest.TestCase):
    def frame(self, times):
        return pd.DataFrame({"timestamp": pd.to_datetime(times), "wind_speed": np.arange(len(times), dtype=float),
                             "power": [.5] * len(times), "temperature": [10.] * len(times)})

    def run_hourly(self, frame):
        return aggregate_hourly(frame, 1, start="2023-01-01 00:00", end="2023-01-01 02:50")

    def test_hour_boundary_means_and_missing_hours(self):
        frame = self.frame(pd.date_range("2023-01-01", periods=7, freq="10min"))
        hourly, summary = self.run_hourly(frame)
        self.assertEqual(hourly.observation_count.tolist(), [6, 1, 0])
        self.assertEqual(hourly.training_eligible.tolist(), [True, False, False])
        self.assertEqual(hourly.wind_speed_mean.iloc[0], 2.5)
        self.assertAlmostEqual(hourly.wind_speed_std.iloc[0], np.std(np.arange(6), ddof=1))
        self.assertTrue(pd.isna(hourly.wind_speed_std.iloc[1]))
        self.assertTrue(pd.isna(hourly.power_mean.iloc[2]))
        self.assertEqual(hourly.available_at.iloc[0], pd.Timestamp("2023-01-01 01:00"))
        self.assertEqual(summary["accepted_timestamp_rows"], 7)

    def test_invalid_values_mask_only_affected_cells(self):
        frame = self.frame(pd.date_range("2023-01-01", periods=6, freq="10min"))
        frame.loc[0, "power"] = 2
        frame.loc[1, "wind_speed"] = -1
        frame.loc[2, "temperature"] = np.inf
        original = frame.copy(deep=True)
        hourly, summary = self.run_hourly(frame)
        self.assertEqual(hourly.observation_count.iloc[0], 6)
        self.assertEqual(hourly.power_count.iloc[0], 5)
        self.assertFalse(hourly.training_eligible.iloc[0])
        self.assertEqual(summary["masked_cells"], {"wind_speed": 1, "power": 1, "temperature": 1})
        pd.testing.assert_frame_equal(frame, original)

    def test_duplicates_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.run_hourly(self.frame(["2023-01-01", "2023-01-01"]))

    def test_excluded_rows_are_accounted_for(self):
        frame = self.frame([pd.Timestamp("2022-12-31 23:50"), pd.Timestamp("2023-01-01 00:05"), pd.NaT])
        hourly, summary = self.run_hourly(frame)
        self.assertEqual(summary["invalid_timestamp_rows"], 1)
        self.assertEqual(summary["outside_period_rows"], 1)
        self.assertEqual(summary["off_grid_rows_in_period"], 1)
        self.assertEqual(hourly.observation_count.sum(), 0)

    def test_future_values_cannot_change_an_earlier_hour(self):
        frame = self.frame(pd.date_range("2023-01-01", periods=12, freq="10min"))
        before, _ = self.run_hourly(frame)
        frame.loc[6:, "power"] = 1
        after, _ = self.run_hourly(frame)
        pd.testing.assert_series_equal(before.iloc[0], after.iloc[0])

    def test_partial_study_bounds_fail(self):
        with self.assertRaisesRegex(ValueError, "complete hours"):
            aggregate_hourly(self.frame([]), 1, start="2023-01-01 00:10", end="2023-01-01 02:50")


if __name__ == "__main__":
    unittest.main()
