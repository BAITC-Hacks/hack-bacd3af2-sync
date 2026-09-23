# Wind turbine ML

Stage 1 implements reproducible ingestion and data auditing for both turbines.
The supplied task requests staged delivery with an audit before model training.

## Setup and run

Python 3.11 or newer. From the repository root:

```powershell
py -m venv .venv
.venv/Scripts/python -m pip install -r ml/requirements.txt
cd ml
../.venv/Scripts/python -m src.data.audit --turbine-1 "C:/Users/User/Downloads/turbine 1.csv" --turbine-2 "C:/Users/User/Downloads/turbine 2.csv"
../.venv/Scripts/python -m unittest discover -s tests -v
```

On other platforms use `python3` and `.venv/bin/python`. Alternatively place the
two files in `ml/data/raw/` and omit the file arguments. Raw data is ignored by Git.
Paths are CLI parameters; defaults and diagnostic thresholds live in `src/config.py`.

Outputs:

- `reports/data_quality.json`: complete gaps, constant runs, missing values,
  parse errors, duplicates, physical range flags, spacing and monthly counts.
- `reports/data_quality.md`: human-readable summary and largest missing intervals.

Original CSVs are read only. UTF-8 headers are mapped explicitly, ID stays out
of numeric features, and invalid parsed values remain visible in audit counts.
SHA-256 fingerprints identify the input files. Output is deterministic for the
same input bytes and settings. Grid coverage includes missing boundary samples
within the configured study period. Source timestamps have no known timezone;
do not assume UTC or use the workstation timezone for weather joins.

## Delivery stages

1. **Complete:** input loading, automated data audit, reports and audit tests.
2. Visual EDA, documented cleaning rules and hourly aggregation with coverage counts.
3. Reusable features, chronological validation, persistence and power-curve baselines,
   candidate models, selection metrics and saved artifacts for each turbine.
4. Validated inference and backend integration, then historical forecast backtesting.

The planned backend API is
`predict_power(turbine_id, weather, horizon_hours, forecast_origin)`.
Weather input columns: `timestamp`, `wind_speed`, `temperature`,
`forecast_origin`, `latitude`, `longitude`. Output columns: `forecast_origin`,
`timestamp`, `turbine_id`, `horizon_hour`, `wind_speed`, `temperature`,
`predicted_power`, `model_version`. Only 24- and 48-hour horizons are intended.
This API is not implemented yet. Weather retrieval belongs to the backend.

No February 2026 labels or archived weather forecasts were provided. Future
observed weather cannot substitute for forecasts available at each historical
origin. Model training, honest forecast evaluation and deployment are later stages.
