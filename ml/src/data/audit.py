"""Run with python -m src.data.audit --turbine-1 PATH --turbine-2 PATH."""
import argparse
import json
from pathlib import Path
from src.config import RAW_DIR, REPORT_DIR, EXPECTED_START, EXPECTED_END
from src.data.validate import audit_file


def render_report(summaries: list[dict]) -> str:
    lines = ["# Turbine data quality audit", "",
             "Stage 1: read-only diagnostics. No rows were deleted, imputed or clipped.", "",
             "Timestamps have no timezone in the CSV. Confirm the source timezone with the data provider before weather joins.", "",
             "## Overview", "",
             "| Metric | Turbine 1 | Turbine 2 |", "| --- | ---: | ---: |"]
    for key in ("rows", "period_start", "period_end", "exact_duplicate_rows_extra",
                "duplicate_timestamps_extra", "conflicting_timestamp_groups", "invalid_or_missing_timestamps",
                "expected_observations", "missing_observations", "gap_count", "off_grid_rows",
                "outside_expected_period_rows", "backward_timestamp_steps", "power_outside_0_1", "negative_wind_speed"):
        lines.append(f"| {key} | {summaries[0][key]} | {summaries[1][key]} |")
    for s in summaries:
        lines += ["", f"## Turbine {s['turbine_id']}", "", f"Source: `{s['source_file']}`. SHA-256: `{s['sha256']}`.", "",
                  f"Missing expected samples: {s['missing_fraction']:.2%}. Missing coverage includes leading and trailing intervals in the configured study period.", "",
                  "| Variable | Min | Max | NaN | Invalid numeric | Infinity | IQR flags | Constant runs |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for col, v in s["numeric"].items():
            lines.append(f"| {col} | {v['min']} | {v['max']} | {v['nan_count']} | {v['invalid_numeric_count']} | {v['infinity_count']} | {v['iqr_outlier_count']} | {len(v['constant_runs'])} |")
        lines += ["", "### Largest missing intervals", "", "| First missing sample | Last missing sample | Missing samples |", "| --- | --- | ---: |"]
        for gap in sorted(s["gaps"], key=lambda g: g["missing_observations"], reverse=True)[:10]:
            lines.append(f"| {gap['start']} | {gap['end']} | {gap['missing_observations']} |")
        if not s["gaps"]:
            lines.append("| None | None | 0 |")
        lines += ["", "### Timestamp spacing", "", "Minutes between sorted unique valid timestamps: " +
                  ", ".join(f"{k}: {v}" for k, v in s["timestamp_delta_minutes_distribution"].items()) + ".", "",
                  "### Source missing values", "", json.dumps(s["source_missing_counts"], ensure_ascii=False), "",
                  "### Parsed types", "", ", ".join(f"{k}: {v}" for k, v in s["parsed_dtypes"].items()), "."]
    lines += ["", "## Interpretation and next stage", "",
              "- Gaps are absent slots on the configured 10-minute grid, not fabricated measurements. Full intervals and monthly counts are in data_quality.json.",
              "- Duplicate counts are extra occurrences. Conflicting timestamp groups have different parsed sensor values at the same timestamp.",
              "- NaN counts include missing tokens and unparseable numbers; infinities are counted separately. Finite values alone determine ranges and IQR fences.",
              "- Outlier flags use Q1 - 3 IQR and Q3 + 3 IQR over the complete historical dataset for diagnostics only. Do not reuse these full-history thresholds in validation-fold cleaning.",
              "- Constant runs require at least 36 equal finite samples at consecutive 10-minute timestamps. Gaps, invalid readings and duplicate timestamps break runs. Zero-power runs may reflect calm wind or shutdowns, so flags alone do not justify deletion.",
              "- The next stage is visual EDA and hourly aggregation, with explicit coverage counts and a documented cleaning policy. Keep future wind standard deviation and other observed-only diagnostics out of production predictors.",
              "- Training and backtesting are not implemented in this stage. Historical weather forecasts and February 2026 power labels were not supplied; the CSVs cannot establish genuine February forecast performance.",
              "- The later predict_power interface will consume backend-supplied weather. This package will not fetch weather.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turbine-1", type=Path, default=RAW_DIR / "turbine 1.csv")
    parser.add_argument("--turbine-2", type=Path, default=RAW_DIR / "turbine 2.csv")
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--expected-start", default=EXPECTED_START)
    parser.add_argument("--expected-end", default=EXPECTED_END)
    args = parser.parse_args()
    results = [audit_file(path, i, expected_start=args.expected_start, expected_end=args.expected_end)
               for i, path in enumerate((args.turbine_1, args.turbine_2), 1)]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "data_quality.json").write_text(
        json.dumps({"schema_version": 1, "turbines": results}, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (args.output_dir / "data_quality.md").write_text(render_report(results), encoding="utf-8")
    for result in results:
        print(f"Turbine {result['turbine_id']}: {result['rows']} rows, {result['missing_observations']} missing slots, {result['gap_count']} gaps")


if __name__ == "__main__":
    main()
