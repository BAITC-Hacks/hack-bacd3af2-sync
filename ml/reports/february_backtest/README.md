# Real archived-weather February replay

The imported backend CSV contains 2,784 rows: 29 origins, two turbines and
48 target hours. It was read locally; ML made no weather API requests and did
not load February actual-power labels. Source files match `origin/backend`.

| Forecast window | Saved rows | Weather lead from source run | Normalized power range |
| --- | ---: | --- | --- |
| [24h predictions](24h/predictions.csv) | 1,392 | 7–30 hours | 0.008232–0.990205 |
| [48h predictions](48h/predictions.csv) | 2,784 | 7–54 hours | 0.008041–0.990767 |

All 58 batches satisfy `run_init + 6h = weather_valid_time <= forecast_origin`.
The `run=` timestamp in weather_source is explicit UTC metadata, converted
explicitly to Asia/Almaty to calculate weather lead. The input's +05:00 offsets
were checked against Asia/Almaty, preserving all local clock hours.

Weather values are identical for both turbines, as expected for their shared
Open-Meteo grid cell. Separate CatBoost models use wind and temperature only;
weather lead is not a model feature. The output `horizon_hours` indexes the
power-forecast intervals from origin, 1–24 or 1–48, not NWP weather lead.

January 31 uses models last trained on January 30 at 23:00, available at
January 31 midnight. February origins use models last trained on January 31
at 23:00. Every model version and training availability boundary was verified.
No February observations enter training or features.

Each run.json stores input/output hashes, weather sources, availability, true
weather lead bounds, model versions and diagnostics. All forecasts are finite
and within [0,1]; no clipping or low-wind/high-power warnings occurred. Forecast
keys are unique per origin/target/turbine; overlapping targets across origins
remain separate. Saved file hashes were independently reconciled.

**These are forecasts, not accuracy metrics.** MAE/RMSE/R² remain unavailable
until actual February power labels are supplied. Evaluation is a separate
command documented in [the CSV backtest guide](../../integration/csv_backtesting.md).
