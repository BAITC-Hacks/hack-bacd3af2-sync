# Hourly preprocessing policy

Hours are left-closed intervals `[timestamp, timestamp + 1 hour)` in the
Asia/Almaty timezone, explicitly configured in `src/config.py`. Local wall-clock
hours are preserved without UTC conversion. `available_at` is the interval end:
an aggregate must not enter historical features before that time. Backend weather
uses the same hours and timezone. The study period covers complete hours only.

1. Preserve the source CSVs. Parse into a separate frame. Invalid timestamps,
   rows outside the configured period, and off-grid timestamps are excluded from
   aggregation and counted separately in `preprocessing.json`.
2. Fail on duplicate valid timestamps. Do not silently choose or average
   conflicting readings. Neither supplied dataset contains duplicates.
3. Mask nonfinite sensor values, negative wind and power outside [0, 1] only
   in the affected sensor column. Log masked cell counts. Do not clip or impute.
   Warm temperatures around +15°C in March and +1.4°C in January are normal
   regional values, not anomalies. Temperature IQR flags are disabled. Finite
   temperatures are retained without seasonal or regional cutoff rules.
4. Retain finite outliers and constant-value runs. The audit flags alone do not
   establish sensor failure, curtailment, shutdown or calm weather.
5. Average equally spaced samples within each hour. Standard deviations use
   `ddof=1` and are missing for fewer than two valid values. Include every hour
   on the timeline, including empty hours with zero counts and missing means.
6. `observation_count` counts timestamp rows. Each sensor has its own valid-value
   count. `coverage_fraction` is observation count / 6. `training_eligible`
   requires six observations and six valid values for all three sensors.
   Partial-hour means remain available for diagnostics, but are not silently
   treated as complete training targets. This conservative selection may bias
   coverage and should be evaluated during later model validation.

## Feature availability

| Field | Use |
| --- | --- |
| power_mean | Historical target; available after interval end |
| wind_speed_mean, temperature_mean | Historical weather inputs; production equivalents must come from forecast weather |
| wind_speed_std/min/max, temperature_std | Historical-only diagnostics; do not feed the forecast model |
| observation_count, sensor counts, coverage_fraction, training_eligible | Quality diagnostics and training selection, not future predictors |
| timestamp | Calendar features in Asia/Almaty, preserving source clock hours |
| available_at | Enforce historical feature availability at forecast origin |
| turbine_id | Dataset identity; keep separate turbine models in the next stage |

No learned outlier thresholds, future interpolation, model training or inference
are performed here. EDA uses complete historical hours for sensor plots and all
hours for coverage plots. Full-history descriptive curves are not fitted
baseline artifacts; baselines must be refit inside each chronological fold.
