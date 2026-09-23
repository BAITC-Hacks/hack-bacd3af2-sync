# Archived forecast replay

**Legacy manifest mode.** The agreed single-CSV workflow is documented in
[csv_backtesting.md](csv_backtesting.md). Use that workflow for the backend file
`data/weather/february_backtest.csv`; it does not require a manifest.

ML performs no weather requests. Backend supplies the six-column weather CSVs
already mapped to `wind_speed` and `temperature`, plus a batch manifest that
records forecast-run availability. The online `predict_power` contract is unchanged.

## Backend export

One CSV per turbine and forecast origin, containing exactly these columns:

```text
timestamp,wind_speed,temperature,forecast_origin,latitude,longitude
```

Every file contains exactly 24 or 48 consecutive local hours starting at the
origin. For a full run, provide both turbines for every midnight origin from
2026-01-31 through 2026-02-28 inclusive: **58 batches**. Files and manifest must
use local Asia/Almaty clock strings without fixed-offset suffixes. A 48-hour
February 28 batch extends through March 1 at 23:00; keep these predictions, then
filter evaluation by the target interval. January 31 also includes January targets
under the backend's agreed interval-start convention.

Place `manifest.json` beside the exported files. This is a schema example only,
not runnable forecast data; replace the hash and include all 58 batch entries:

```json
{
  "timezone": "Asia/Almaty",
  "data_kind": "archived_forecast",
  "source": "Open-Meteo archive selected by backend",
  "batches": [
    {
      "turbine_id": 1,
      "forecast_origin": "2026-01-31 00:00:00",
      "weather_run_available_at": "2026-01-30 18:00:00",
      "file": "turbine_1_2026-01-31.csv",
      "sha256": "REPLACE_WITH_SHA256_OF_EXPORTED_CSV_BYTES"
    }
  ]
}
```

`weather_run_available_at` means when that forecast run was actually available,
including any publication delay. It is not retrieval time and must not be copied
from the requested origin without checking the source. Backend is responsible
for verifying it against its archive. ML rejects runs available after origin,
wrong hashes, incomplete origin coverage and any extra CSV fields such as actual
power. These checks cannot independently certify the provider's provenance.

## As-of model bundles

Two snapshots already exist:

- `models/asof_2026-01-31/turbine_{1,2}/`: last training target January 30 at 23:00,
  available at January 31 midnight; used for the January 31 origin.
- `models/turbine_{1,2}/`: last training target January 31 at 23:00,
  available at February 1 midnight; used for subsequent origins.

Candidate selection is frozen from the June/September/November validation
windows. Preparing the earlier snapshot refits that candidate without changing
its parameters or looking at February. To reproduce into a **new** directory:

```text
python -m src.backtesting.prepare_snapshot --cutoff "2026-01-31 00:00:00" --output-dir models/reproduced_asof_2026-01-31
```

## Phase 1: freeze predictions

From `ml/` with dependencies installed:

```text
python -m src.backtesting.run --manifest data/weather/manifest.json --early-model-dir models/asof_2026-01-31 --horizon 48 --output-dir data/backtests/february_48h
```

The output directory must be new. All batches must validate and predict before
output is created. `predictions.csv` contains the eight-column forecast contract;
keys are `(forecast_origin, timestamp, turbine_id)`, so overlapping targets are
retained. `run.json` stores hashes, selected model versions, batch provenance
and prediction corrections. No actual-power path or labels are accepted by this
command. Nothing is trained during replay. For partial exports, set `--start`
and `--end` explicitly; there must still be both turbines for every requested day.

## Phase 2: evaluate after prediction

Only once predictions are frozen, provide a separate CSV with exactly
`timestamp,turbine_id,power_mean`. Labels must be complete hourly observations,
using the same Asia/Almaty interval-start convention. Do not fill missing labels
with zero. This command never fits models or invokes prediction:

```text
python -m src.backtesting.evaluate --run-dir data/backtests/february_48h --actuals data/actuals/february_hourly.csv --output data/backtests/february_48h/evaluation.json
```

Default target interval is `[2026-02-01, 2026-03-01)`. Earlier/later targets are
excluded and counted. Actuals join many-to-one onto prediction pairs; duplicate
labels fail. Missing labels are counted rather than imputed. Per-turbine MAE,
RMSE, R², normalized MAE, horizon and wind-bin metrics use matched pairs only.
Unmatched turbines have null metrics. No matching labels causes an explicit
failure. Overlapping origins have equal pair weight, not unique-target weighting.
The frozen prediction hash is checked before evaluation, and outputs are never
overwritten by default.

## Current status

Runner, evaluator and early model bundles are implemented and tested. Synthetic
fixtures test leakage guards and joins only. No real archive export or actual
February power has been supplied to ML; no real February backtest score is claimed.
