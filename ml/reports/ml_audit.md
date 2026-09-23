# ML audit — 2026-09-23

This audit checks the delivered implementation against the supplied task. It
does not claim that observed-weather validation measures operational forecast
accuracy. Existing models and saved predictions were not overwritten.

## Reproduction evidence

`audit_verification.json` records the measured results. The audit script is
`../scripts/verify_audit.py`. In the training environment, from the repository root:

```text
python ml/scripts/verify_audit.py --raw-dir <directory-containing-original-turbine-CSVs>
python -m unittest discover -s ml/tests
```

For unittest, include the absolute `ml/` directory in `PYTHONPATH` as documented
in the ML README. Raw files must be named `turbine 1.csv` and `turbine 2.csv`.
The audit refits models in memory and replays forecasts in a temporary directory.
Its only persistent output is the audit JSON; existing production artifacts
are not changed. Run without Python's `-O` option so audit assertions remain active.

- Reaggregated the original 142,360 / 149,499 rows and matched the hourly datasets.
- Verified dataset and binary SHA-256 against metadata.
- Loaded all four native CatBoost artifacts: each has 500 trees and features
  `wind_speed`, `temperature`.
- Refit all four models on their declared training subsets: maximum absolute
  prediction difference on those subsets was **0.0**.
- Independently recalculated saved selection and holdout metrics and matched
  the target values to the hourly source. Maximum metric difference: 1.11e-16.
- Refit holdout CatBoost and power curve and regenerated both persistence
  baselines. Maximum prediction difference against saved results: 1.11e-16.
- Replayed the real backend archive CSV: 1,392 rows for 24h and 2,784 for 48h,
  with maximum prediction difference 1.11e-16. Verified saved output/input hashes.
- Confirmed identical wind and temperature between turbines in the archive.
- Test suite: **58 tests passed**.
- Actual backend adapter and output validator: **4 in-memory cases passed**,
  using pandas 2.2.3 / numpy 2.2.5. This is not an HTTP/container deployment test.

## Native model artifacts

All training periods begin 2023-03-11 00:00, in Asia/Almaty.

| Path under models/ | Bytes | Training rows | Last target hour |
| --- | ---: | ---: | --- |
| turbine_1/model.cbm | 562408 | 23667 | 2026-01-31 23:00 |
| turbine_2/model.cbm | 562472 | 24785 | 2026-01-31 23:00 |
| asof_2026-01-31/turbine_1/model.cbm | 562424 | 23643 | 2026-01-30 23:00 |
| asof_2026-01-31/turbine_2/model.cbm | 562456 | 24761 | 2026-01-30 23:00 |

`src/inference/predict.py` calls artifact loading and native model prediction;
`src/inference/artifacts.py` checks hashes and feature schema;
`src/training/models.py` calls `CatBoostRegressor.load_model` and `model.predict`.
No constant/mock prediction fallback exists in this ML path.

## Leakage and archive boundaries

- `src/training/validation.py`: training requires eligible rows with
  `timestamp < origin` and `available_at <= origin`. Availability equals the
  hourly interval end. February data in the training input is rejected.
- `src/config.py`, `src/training/train.py`: chronological June, September,
  November 2025 selection windows; December–January holdout. Selection is
  frozen before holdout. Each model stays frozen within its evaluation window.
- `src/backtesting/csv_replay.py`: January 31 uses the early snapshot; subsequent
  origins use the final model. Inference independently rejects a model whose
  training observations were not yet available at the requested origin.
- `src/features/build_features.py`: no target power, future within-hour sensor
  statistics or power lags enter model features.
- `src/backtesting/evaluate.py`: labels are read only after saved predictions;
  this separate step does not train or infer.
- The default runner reads `data/weather/february_backtest.csv`. It checks
  `weather_valid_time = run_init + 6h <= forecast_origin`, one run per batch,
  48 consecutive hours and complete origin/turbine coverage. True weather lead
  is 7–54h, calculated from `run=`; output horizon is the one-based interval index.
- Provider provenance is supplied by backend's
  `reports/weather_backtest_export.md`. ML verifies internal consistency, not
  independent delivery history at Open-Meteo. No weather API was called.

Relevant passing tests include `test_february_is_rejected_even_when_ineligible`,
`test_train_cutoff_excludes_future_targets`,
`test_features_ignore_target_and_diagnostics`,
`test_first_origin_rejects_final_models`,
`test_future_run_and_false_availability_rejected`, and
`test_both_windows_format_overlaps_model_switch_and_no_network`.

## Holdout comparison: observed-weather proxy only

| Turbine | Model | MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: |
| 1 | Persistence | .352035 | .475009 | -.686434 |
| 1 | Seasonal persistence | .373868 | .489056 | -.787656 |
| 1 | Power curve | .034566 | .056440 | .976191 |
| 1 | CatBoost | .024389 | .052239 | .979604 |
| 2 | Persistence | .351315 | .474582 | -.705607 |
| 2 | Seasonal persistence | .372024 | .487851 | -.802314 |
| 2 | Power curve | .039945 | .083068 | .947746 |
| 2 | CatBoost | .028126 | .079774 | .951808 |

MAE improvement against the empirical curve: 29.44% / 29.59%.
These are normalized power units. Actual target-hour weather is supplied to
weather-based models, but not persistence; this comparison does not establish
the same advantage under uncertain forecast weather. Holdout models train only
through November 30. Final saved models subsequently include holdout history;
the scores above are not their training-set scores.

Holdout has 2,920 / 2,908 origin–target pairs and 1,484 / 1,478 unique target
hours. Overlapping origins count separately; only complete eligible hours are
scored. Full results are in `model_comparison.md`, model `metrics.json` files
and `turbine_*_validation_predictions.csv.gz`.

## Incomplete, partial and deliberately omitted work

1. **Full-chain forecast accuracy is unmeasured.** February actual power is
   absent. Frozen forecasts exist; genuine February MAE/RMSE/R² do not.
2. **Deployment is not verified.** The real adapter passes in-memory integration
   checks with the handoff module injected into the process. Backend runtime
   wiring and HTTP/container end-to-end validation remain the backend owner's work.
3. **Separate versus pooled model superiority is unproven (§13).** Separate
   models beat baselines; no pooled-model comparison was performed.
4. **Lag benefit was not experimentally measured (§9).** Omitting lags is
   documented and permitted by the task; the weather-only contract lacks power history.
5. **Early snapshots lack separate evaluation/metrics.json (§20).** Their
   metadata explicitly states no snapshot holdout evaluation. Main bundles
   contain metrics.json and validation metrics.
6. **Metadata wording is stale.** Existing bundles name Previous Runs/Historical
   Forecast API. Main metadata says no archived forecasts, which applies to
   training validation but is misleading after the Single Runs replay was added.
   Audit records this discrepancy without rewriting historical artifacts.
7. **Config centralization is partial (§24).** Paths, dates, timezone and seed
   are centralized. Model parameters live in training/models.py, and the archive
   availability rule of six hours lives in csv_replay.py.
8. **Optional LightGBM/XGBoost experiments were not run (§12).**
   HistGradientBoosting and calendar-feature CatBoost were compared.

The implementation has real trained models and reproducible proxy metrics.
Those facts do not replace missing full-chain evaluation or deployment evidence.
