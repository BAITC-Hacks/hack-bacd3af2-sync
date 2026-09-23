"""Forecast analytics: summary statistics, operational anomaly detection and the
natural-language explanation produced by the agent's final step."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.core.constants import (
    CALM_POWER_MAX,
    CALM_WIND_MAX,
    CUT_OUT_WIND_SPEED,
    EXTREME_COLD_C,
    LOW_GENERATION_AVG,
    POWER_RAMP_ALERT,
    TURBINES,
    WINDY_POWER_MIN,
    WINDY_WIND_MIN,
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
class ConsistencyCheck:
    """Hours where predicted power contradicts the wind that drives it."""

    calm_but_producing: int
    windy_but_idle: int
    total_hours: int

    @property
    def inconsistent_hours(self) -> int:
        return self.calm_but_producing + self.windy_but_idle

    @property
    def share(self) -> float:
        return self.inconsistent_hours / self.total_hours if self.total_hours else 0.0


def check_physical_consistency(predictions: dict[int, pd.DataFrame]) -> ConsistencyCheck:
    frames = pd.concat(predictions.values(), ignore_index=True)
    wind, power = frames["wind_speed"], frames["predicted_power"]
    calm = (wind < CALM_WIND_MAX) & (power > CALM_POWER_MAX)
    windy = (wind >= WINDY_WIND_MIN) & (wind < CUT_OUT_WIND_SPEED) & (power < WINDY_POWER_MIN)
    return ConsistencyCheck(int(calm.sum()), int(windy.sum()), len(frames))


@dataclass(frozen=True, slots=True)
class RecomputeInfo:
    """What the agent's analysis decided, for the explanation step."""

    performed: bool
    reasons: list[str] = field(default_factory=list)
    outcome: str = ""


@dataclass(frozen=True, slots=True)
class ExplanationInput:
    predictions: dict[int, pd.DataFrame]
    summary: ForecastSummary
    horizon_hours: int
    warning_count: int
    recompute: RecomputeInfo = field(default_factory=lambda: RecomputeInfo(performed=False))


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

    sentences.append(_recompute_sentence(data.recompute))

    if data.warning_count:
        sentences.append(
            f"{data.warning_count} operational warning(s) were raised — review them before dispatch planning."
        )
    else:
        sentences.append("All values stay within normalized physical bounds and no operational anomalies were found.")

    return " ".join(sentences), len(sentences)


def _recompute_sentence(recompute: RecomputeInfo) -> str:
    if not recompute.performed:
        return (
            "The agent's self-check found no reason to recompute: no out-of-range values, "
            "no fallback weather and no physically inconsistent hours."
        )
    reasons = "; ".join(recompute.reasons) or "the analysis flagged the first result"
    return f"The agent recomputed the forecast once because {reasons} — {recompute.outcome}"


def build_explanation_facts(
    data: ExplanationInput,
    *,
    forecast_date: str,
    weather_source: str | None,
    model_version: str | None,
    warnings: list[str],
) -> dict[str, object]:
    """Numbers the LLM is allowed to talk about — nothing else is sent."""
    frames = pd.concat(data.predictions.values(), ignore_index=True)
    fleet = _fleet_series(data.predictions)
    top_hours = fleet.sort_values(ascending=False).head(3)
    wind_by_time = frames.groupby("timestamp")["wind_speed"].mean()
    low_window = _low_output_window(fleet)
    correlation: float | None = None
    if frames["wind_speed"].std() > 0 and frames["predicted_power"].std() > 0:
        correlation = round(float(np.corrcoef(frames["wind_speed"], frames["predicted_power"])[0, 1]), 2)

    return {
        "forecast_date": forecast_date,
        "horizon_hours": data.horizon_hours,
        "power_unit": "normalized active power, 0..1 = share of rated capacity",
        "fleet_average_power": round(data.summary.average_power, 3),
        "min_power": round(data.summary.min_power, 3),
        "max_power": round(data.summary.max_power, 3),
        "peak_hours": [
            {
                "timestamp": pd.Timestamp(ts).isoformat(),
                "fleet_power": round(float(value), 3),
                "wind_speed_ms": round(float(wind_by_time[ts]), 1),
            }
            for ts, value in top_hours.items()
        ],
        "low_output_window": (
            {"from": low_window[0].isoformat(), "to": low_window[1].isoformat()} if low_window else None
        ),
        "wind_speed_ms": {
            "min": round(float(frames["wind_speed"].min()), 1),
            "max": round(float(frames["wind_speed"].max()), 1),
            "mean": round(float(frames["wind_speed"].mean()), 1),
        },
        "temperature_c": {
            "min": round(float(frames["temperature"].min()), 1),
            "max": round(float(frames["temperature"].max()), 1),
        },
        "wind_power_correlation": correlation,
        "turbines": [
            {"turbine": _turbine_name(turbine_id), "average_power": round(float(frame["predicted_power"].mean()), 3)}
            for turbine_id, frame in sorted(data.predictions.items())
        ],
        "warnings": warnings,
        "recompute": {
            "performed": data.recompute.performed,
            "reasons": data.recompute.reasons,
            "outcome": data.recompute.outcome,
        },
        "weather_source": weather_source,
        "model_version": model_version,
    }
