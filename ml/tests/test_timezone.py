import unittest
import pandas as pd
from src.config import TIMEZONE
from src.time_utils import local_timestamps
from src.features.build_features import build_features
from src.data.preprocess import aggregate_hourly
from src.training.validation import training_before


class TimezoneTests(unittest.TestCase):
    def test_serialized_offsets_match_almaty_without_clock_shift(self):
        for value in ("2026-02-01T00:00:00+05:00", "2023-03-11T00:00:00+06:00"):
            result = local_timestamps(pd.Series([value]))
            self.assertEqual(result.iloc[0].hour, 0)
            self.assertIsNone(result.dt.tz)
        with self.assertRaisesRegex(ValueError, "Offset does not match"):
            local_timestamps(pd.Series(["2026-02-01T00:00:00+06:00"]))

    def test_backend_aware_and_source_naive_features_match(self):
        weather = pd.DataFrame({"timestamp": pd.to_datetime(["2023-03-11 00:00", "2026-01-01 00:00"]),
                                "wind_speed": [6., 7.], "temperature": [15., 1.4]})
        expected = build_features(weather)
        weather["timestamp"] = weather.timestamp.dt.tz_localize(TIMEZONE)
        self.assertEqual(weather.timestamp.iloc[0].utcoffset().total_seconds(), 6 * 3600)
        self.assertEqual(weather.timestamp.iloc[1].utcoffset().total_seconds(), 5 * 3600)
        pd.testing.assert_frame_equal(expected, build_features(weather))
        self.assertEqual(build_features(weather).hour.tolist(), [0, 0])

    def test_wrong_timezone_is_rejected_not_shifted(self):
        for zone in ("UTC", "Asia/Tokyo"):
            with self.assertRaisesRegex(ValueError, "Expected Asia/Almaty"):
                local_timestamps(pd.Series(pd.date_range("2026-01-01", periods=2, freq="h", tz=zone)))

    def test_ambiguous_local_hour_is_preserved_without_inventing_utc(self):
        times = pd.Series(pd.to_datetime(["2024-02-29 23:00", "2024-03-01 00:00"]))
        pd.testing.assert_series_equal(times, local_timestamps(times))

    def test_aware_aggregation_and_origin_keep_same_hours(self):
        times = pd.date_range("2026-01-31", periods=6, freq="10min", tz=TIMEZONE)
        source = pd.DataFrame({"timestamp": times, "wind_speed": 6., "power": .3, "temperature": 1.4})
        hourly, summary = aggregate_hourly(source, 1, start="2026-01-31 00:00", end="2026-01-31 00:50")
        self.assertEqual(summary["timezone"], TIMEZONE)
        self.assertEqual(hourly.timestamp.iloc[0], pd.Timestamp("2026-01-31 00:00"))
        self.assertAlmostEqual(hourly.temperature_mean.iloc[0], 1.4)
        selected = training_before(hourly, pd.Timestamp("2026-01-31 01:00", tz=TIMEZONE))
        self.assertEqual(len(selected), 1)
        with self.assertRaisesRegex(ValueError, "Expected Asia/Almaty"):
            training_before(hourly, pd.Timestamp("2026-01-31 01:00", tz="UTC"))
