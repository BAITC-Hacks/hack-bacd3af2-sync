import tempfile
import unittest
from pathlib import Path
import pandas as pd
from src.data.load import COLUMNS, load_raw
from src.data.validate import audit_file


class AuditTests(unittest.TestCase):
    def audit(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "turbine.csv"
            pd.DataFrame(rows, columns=list(COLUMNS)).to_csv(path, index=False)
            return audit_file(path, 1, expected_start="2023-01-01 00:00:00",
                              expected_end="2023-01-01 01:00:00", constant_min_observations=2)

    def test_missing_slots_include_edges_and_duplicate_does_not_fill_gap(self):
        result = self.audit([[1, "2023-01-01 00:10:00", 5, .2, 10],
                             [1, "2023-01-01 00:10:00", 5, .2, 10],
                             [2, "2023-01-01 00:30:00", 5, .2, 10]])
        self.assertEqual(result["missing_observations"], 5)
        self.assertEqual(result["gap_count"], 3)
        self.assertEqual(result["exact_duplicate_rows_extra"], 1)
        self.assertEqual(result["duplicate_timestamps_extra"], 1)
        self.assertEqual(result["numeric"]["power"]["constant_runs"], [])

    def test_invalid_and_physical_values_are_reported_not_removed(self):
        result = self.audit([[1, "bad", "bad", 1.2, "inf"],
                             [2, "2023-01-01 00:00:00", -1, "", -5],
                             [3, "2023-01-01 00:00:00", 2, .3, -5]])
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["invalid_or_missing_timestamps"], 1)
        self.assertEqual(result["numeric"]["wind_speed"]["invalid_numeric_count"], 1)
        self.assertEqual(result["numeric"]["temperature"]["infinity_count"], 1)
        self.assertEqual(result["numeric"]["power"]["nan_count"], 1)
        self.assertEqual(result["negative_wind_speed"], 1)
        self.assertEqual(result["power_outside_0_1"], 1)
        self.assertEqual(result["conflicting_timestamp_groups"], 1)

    def test_constant_runs_break_at_gaps(self):
        result = self.audit([[i, f"2023-01-01 00:{minute}:00", 5, 0, 10]
                             for i, minute in enumerate(("00", "10", "30", "40"))])
        runs = result["numeric"]["power"]["constant_runs"]
        self.assertEqual([run["observations"] for run in runs], [2, 2])

    def test_all_invalid_and_empty_inputs(self):
        for rows in ([], [[1, "bad", "bad", "bad", "bad"]]):
            result = self.audit(rows)
            self.assertIsNone(result["period_start"])
            self.assertEqual(result["missing_observations"], 7)
            self.assertIsNone(result["numeric"]["power"]["min"])

    def test_schema_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            path.write_text("timestamp,power\n2023-01-01,0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unexpected CSV schema"):
                load_raw(path)

    def test_off_grid_and_out_of_order(self):
        result = self.audit([[1, "2023-01-01 00:15:00", 5, .2, 10],
                             [2, "2022-12-31 23:50:00", 5, .2, 10]])
        self.assertEqual(result["off_grid_rows"], 1)
        self.assertEqual(result["outside_expected_period_rows"], 1)
        self.assertEqual(result["backward_timestamp_steps"], 1)
        self.assertEqual(result["missing_observations"], 7)


if __name__ == "__main__":
    unittest.main()
