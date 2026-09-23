"""Forecast analytics: summary statistics, operational anomaly detection and the
natural-language explanation produced by the agent's final step."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.constants import (
    CUT_OUT_WIND_SPEED,
    EXTREME_COLD_C,
    LOW_GENERATION_AVG,
    POWER_RAMP_ALERT,
    TURBINES,
)
from app.schemas.forecast import ForecastSummary

_STRONG_WIND_FOR_OUTPUT = 10.0  # m/s — a healthy turbine should generate well above this
_NEAR_ZERO_OUTPUT = 0.05
_LOW_OUTPUT_HOUR = 0.10


def _fmt_time(value: pd.Timestamp) -> str:
    return value.strftime("%b %d, %H:%M")


def _turbine_name(turbine_id: int) -> str:
    return TURBINES[turbine_id].name


def _fleet_series(predictions: dict[int, pd.DataFrame]) -> pd.Series:
    """Average predicted power across selected turbines, indexed by timestamp."""
    stacked = pd.concat(predictions.values(), ignore_index=True)
    return stacked.groupby("timestamp")["predicted_power"].mean().sort_index()


def build_summary(predictions: dict[int, pd.DataFrame]) -> ForecastSummary:
    """average/max/min over every predicted point; peak_hour is the best fleet-average hour."""
    power = pd.concat(predictions.values(), ignore_index=True)["predicted_power"]
    fleet = _fleet_series(predictions)
    return ForecastSummary(
        average_power=round(float(power.mean()), 4),
        max_power=round(float(power.max()), 4),
        min_power=round(float(power.min()), 4),
        peak_hour=pd.Timestamp(fleet.idxmax()).to_pydatetime(),
    )


def detect_weather_anomalies(turbine_id: int, weather: pd.DataFrame) -> list[str]:
    name = _turbine_name(turbine_id)
    warnings: list[str] = []

    storm = weather[weather["wind_speed"] >= CUT_OUT_WIND_SPEED]
    if not storm.empty:
        worst = storm.loc[storm["wind_speed"].idxmax()]
        warnings.append(
            f"{name}: wind reaches {worst['wind_speed']:.1f} m/s at {_fmt_time(worst['timestamp'])}, "
            f"above the {CUT_OUT_WIND_SPEED:g} m/s cut-out speed — protective shutdown is likely "
            f"({len(storm)} h affected)."
        )

    cold = weather[weather["temperature"] <= EXTREME_COLD_C]
    if not cold.empty:
        coldest = cold.loc[cold["temperature"].idxmin()]
        warnings.append(
            f"{name}: temperature drops to {coldest['temperature']:.1f} °C at "
            f"{_fmt_time(coldest['timestamp'])} — outside standard cold-climate operating limits."
        )
    return warnings


def detect_power_anomalies(turbine_id: int, prediction: pd.DataFrame) -> list[str]:
    name = _turbine_name(turbine_id)
    warnings: list[str] = []
    ordered = prediction.sort_values("timestamp").reset_index(drop=True)

    ramps = ordered["predicted_power"].diff().abs()
    if (ramps >= POWER_RAMP_ALERT).any():
        idx = int(ramps.idxmax())
        delta = ordered.loc[idx, "predicted_power"] - ordered.loc[idx - 1, "predicted_power"]
        warnings.append(
            f"{name}: sharp ramp of {delta:+.2f} within one hour at "
            f"{_fmt_time(ordered.loc[idx, 'timestamp'])} — plan balancing reserve."
        )

    suspicious = ordered[
        (ordered["wind_speed"] >= _STRONG_WIND_FOR_OUTPUT)
        & (ordered["wind_speed"] < CUT_OUT_WIND_SPEED)
        & (ordered["predicted_power"] < _NEAR_ZERO_OUTPUT)
    ]
    if not suspicious.empty:
        warnings.append(
            f"{name}: near-zero output predicted for {len(suspicious)} h despite wind above "
            f"{_STRONG_WIND_FOR_OUTPUT:g} m/s — check for curtailment or model drift."
        )

    if ordered["predicted_power"].mean() < LOW_GENERATION_AVG:
        warnings.append(
            f"{name}: average output below {LOW_GENERATION_AVG:.0%} of rated capacity — "
            "a calm period is expected."
        )
    return warnings


@dataclass(frozen=True, slots=True)
class ExplanationInput:
    predictions: dict[int, pd.DataFrame]
    summary: ForecastSummary
    horizon_hours: int
    warning_count: int


def _level(average: float) -> str:
    if average >= 0.6:
        return "high"
    if average >= 0.3:
        return "moderate"
    return "low"


def _low_output_window(fleet: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """Longest continuous run of hours with fleet output below the low-output threshold."""
    is_low = (fleet < _LOW_OUTPUT_HOUR).to_numpy()
    best: tuple[int, int] | None = None
    start: int | None = None
    for i, low in enumerate([*is_low, False]):
        if low and start is None:
            start = i
        elif not low and start is not None:
            if best is None or i - start > best[1] - best[0]:
                best = (start, i)
            start = None
    if best is None or best[1] - best[0] < 3:
        return None
    return fleet.index[best[0]], fleet.index[best[1] - 1]


def build_explanation(data: ExplanationInput) -> tuple[str, int]:
    """Return (explanation, number_of_signals_used)."""
    frames = pd.concat(data.predictions.values(), ignore_index=True)
    fleet = _fleet_series(data.predictions)
    summary = data.summary
    sentences: list[str] = []

    sentences.append(
        f"Over the next {data.horizon_hours} hours the agent expects {_level(summary.average_power)} "
        f"generation, averaging {summary.average_power:.0%} of rated capacity "
        f"(range {summary.min_power:.0%}–{summary.max_power:.0%})."
    )

    if frames["wind_speed"].std() > 0 and frames["predicted_power"].std() > 0:
        correlation = float(np.corrcoef(frames["wind_speed"], frames["predicted_power"])[0, 1])
        peak_wind = frames.loc[frames["timestamp"] == summary.peak_hour, "wind_speed"].mean()
        sentences.append(
            f"Output follows wind speed closely (r = {correlation:.2f}); the peak is forecast for "
            f"{_fmt_time(pd.Timestamp(summary.peak_hour))} when wind reaches about {peak_wind:.1f} m/s."
        )

    low_window = _low_output_window(fleet)
    if low_window is not None:
        sentences.append(
            f"A low-output window is expected from {_fmt_time(low_window[0])} to "
            f"{_fmt_time(low_window[1])} as wind drops toward the cut-in range."
        )

    if len(data.predictions) == 2:
        first, second = (data.predictions[i]["predicted_power"].mean() for i in (1, 2))
        if first > 0 and abs(second - first) / first >= 0.03:
            leader, lagger = ("Turbine 1", "Turbine 2") if first > second else ("Turbine 2", "Turbine 1")
            gap = abs(second - first) / min(first, second)
            sentences.append(f"{leader} is expected to out-produce {lagger} by about {gap:.0%}.")
        else:
            sentences.append("Both turbines are expected to perform almost identically.")

    mean_temperature = float(frames["temperature"].mean())
    if mean_temperature <= -5:
        sentences.append(
            f"Cold air (mean {mean_temperature:.0f} °C) is denser, which slightly lifts output at a given wind speed."
        )

    if data.warning_count:
        sentences.append(
            f"{data.warning_count} operational warning(s) were raised — review them before dispatch planning."
        )
    else:
        sentences.append("All values stay within normalized physical bounds and no operational anomalies were found.")

    return " ".join(sentences), len(sentences)
