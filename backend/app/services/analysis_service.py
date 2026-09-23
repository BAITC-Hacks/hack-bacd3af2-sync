"""Forecast analytics: summary statistics, operational anomaly detection and the
natural-language explanation produced by the agent's final step."""

from dataclasses import dataclass, field
from typing import Literal

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
            f"above the {CUT_OUT_WIND_SPEED:g} m/s cut-out speed; protective shutdown is likely "
            f"({len(storm)} h affected)."
        )

    cold = weather[weather["temperature"] <= EXTREME_COLD_C]
    if not cold.empty:
        coldest = cold.loc[cold["temperature"].idxmin()]
        warnings.append(
            f"{name}: temperature drops to {coldest['temperature']:.1f} °C at "
            f"{_fmt_time(coldest['timestamp'])}, outside standard cold-climate operating limits."
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
            f"{_fmt_time(ordered.loc[idx, 'timestamp'])}; plan balancing reserve."
        )

    suspicious = ordered[
        (ordered["wind_speed"] >= _STRONG_WIND_FOR_OUTPUT)
        & (ordered["wind_speed"] < CUT_OUT_WIND_SPEED)
        & (ordered["predicted_power"] < _NEAR_ZERO_OUTPUT)
    ]
    if not suspicious.empty:
        warnings.append(
            f"{name}: near-zero output predicted for {len(suspicious)} h despite wind above "
            f"{_STRONG_WIND_FOR_OUTPUT:g} m/s; check for curtailment or model drift."
        )

    if ordered["predicted_power"].mean() < LOW_GENERATION_AVG:
        warnings.append(
            f"{name}: average output below {LOW_GENERATION_AVG:.0%} of rated capacity: "
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


RecomputeReason = Literal["clipped", "fallback_weather", "inconsistent"]
RecomputeOutcome = Literal["resolved", "persisted", "failed"]


@dataclass(frozen=True, slots=True)
class RecomputeInfo:
    """What the agent's analysis decided, for the explanation step.

    `reasons`/`outcome` are English prose (LLM facts, English template); the codes let the
    Russian template phrase the same decision without translating free text.
    """

    performed: bool
    reasons: list[str] = field(default_factory=list)
    outcome: str = ""
    reason_codes: list[RecomputeReason] = field(default_factory=list)
    outcome_code: RecomputeOutcome | None = None


@dataclass(frozen=True, slots=True)
class ExplanationInput:
    predictions: dict[int, pd.DataFrame]
    summary: ForecastSummary
    horizon_hours: int
    warning_count: int
    recompute: RecomputeInfo = field(default_factory=lambda: RecomputeInfo(performed=False))
    language: Literal["en", "ru"] = "en"


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


@dataclass(frozen=True, slots=True)
class _Signals:
    """Language-neutral facts the template explanation is written from."""

    level: Literal["high", "moderate", "low"]
    average: float
    minimum: float
    maximum: float
    correlation: float | None
    peak_time: pd.Timestamp
    peak_wind: float | None
    low_window: tuple[pd.Timestamp, pd.Timestamp] | None
    comparison: tuple[int, int, float] | None  # (leader, lagger, gap) when the turbines differ
    turbines_equal: bool
    cold_mean_temperature: float | None
    recompute: RecomputeInfo
    warning_count: int


def _signals(data: ExplanationInput) -> _Signals:
    frames = pd.concat(data.predictions.values(), ignore_index=True)
    summary = data.summary
    correlation: float | None = None
    peak_wind: float | None = None
    if frames["wind_speed"].std() > 0 and frames["predicted_power"].std() > 0:
        correlation = float(np.corrcoef(frames["wind_speed"], frames["predicted_power"])[0, 1])
        peak_wind = float(frames.loc[frames["timestamp"] == summary.peak_hour, "wind_speed"].mean())

    comparison: tuple[int, int, float] | None = None
    turbines_equal = False
    if len(data.predictions) == 2:
        first, second = (float(data.predictions[i]["predicted_power"].mean()) for i in (1, 2))
        if first > 0 and abs(second - first) / first >= 0.03:
            leader, lagger = (1, 2) if first > second else (2, 1)
            comparison = (leader, lagger, abs(second - first) / min(first, second))
        else:
            turbines_equal = True

    mean_temperature = float(frames["temperature"].mean())
    return _Signals(
        level=_level(summary.average_power),  # type: ignore[arg-type]
        average=summary.average_power,
        minimum=summary.min_power,
        maximum=summary.max_power,
        correlation=correlation,
        peak_time=pd.Timestamp(summary.peak_hour),
        peak_wind=peak_wind,
        low_window=_low_output_window(_fleet_series(data.predictions)),
        comparison=comparison,
        turbines_equal=turbines_equal,
        cold_mean_temperature=mean_temperature if mean_temperature <= -5 else None,
        recompute=data.recompute,
        warning_count=data.warning_count,
    )


def build_explanation(data: ExplanationInput) -> tuple[str, int]:
    """Return (explanation, number_of_signals_used) in the requested language."""
    signals = _signals(data)
    sentences = _sentences_ru(signals, data.horizon_hours) if data.language == "ru" else _sentences_en(signals, data.horizon_hours)
    return " ".join(sentences), len(sentences)


def _sentences_en(sig: _Signals, horizon_hours: int) -> list[str]:
    sentences = [
        f"Over the next {horizon_hours} hours the agent expects {sig.level} generation, averaging "
        f"{sig.average:.0%} of rated capacity (range {sig.minimum:.0%}–{sig.maximum:.0%})."
    ]
    if sig.correlation is not None and sig.peak_wind is not None:
        sentences.append(
            f"Output follows wind speed closely (r = {sig.correlation:.2f}); the peak is forecast for "
            f"{_fmt_time(sig.peak_time)} when wind reaches about {sig.peak_wind:.1f} m/s."
        )
    if sig.low_window is not None:
        sentences.append(
            f"A low-output window is expected from {_fmt_time(sig.low_window[0])} to "
            f"{_fmt_time(sig.low_window[1])} as wind drops toward the cut-in range."
        )
    if sig.comparison is not None:
        leader, lagger, gap = sig.comparison
        sentences.append(f"Turbine {leader} is expected to out-produce Turbine {lagger} by about {gap:.0%}.")
    elif sig.turbines_equal:
        sentences.append("Both turbines are expected to perform almost identically.")
    if sig.cold_mean_temperature is not None:
        sentences.append(
            f"Cold air (mean {sig.cold_mean_temperature:.0f} °C) is denser, which slightly lifts output at a given wind speed."
        )
    sentences.append(_recompute_sentence(sig.recompute))
    if sig.warning_count:
        sentences.append(
            f"{sig.warning_count} operational warning(s) were raised; review them before dispatch planning."
        )
    else:
        sentences.append("All values stay within normalized physical bounds and no operational anomalies were found.")
    return sentences


_RU_MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря")
_RU_LEVELS = {"high": "высокую", "moderate": "умеренную", "low": "низкую"}
_RU_REASONS: dict[str, str] = {
    "clipped": "часть значений вышла за пределы [0, 1] и была обрезана",
    "fallback_weather": "прогноз строился на резервной погоде, а основной источник снова стал доступен",
    "inconsistent": "заметная доля часов противоречила скорости ветра",
}
_RU_OUTCOMES: dict[str, str] = {
    "resolved": "пересчитанный прогноз прошёл все проверки и заменил первый.",
    "persisted": "после пересчёта причина сохранилась, поэтому к прогнозу стоит отнестись с осторожностью.",
    "failed": "пересчёт не удался, поэтому сохранён исходный проверенный прогноз.",
}


def _ru_time(value: pd.Timestamp) -> str:
    return f"{value.day} {_RU_MONTHS[value.month - 1]}, {value:%H:%M}"


def _ru_num(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",").replace("-", "−")


def _ru_pct(value: float) -> str:
    return f"{round(value * 100)}%"


def _ru_plural(count: int, one: str, few: str, many: str) -> str:
    mod10, mod100 = count % 10, count % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        return few
    return many


def _sentences_ru(sig: _Signals, horizon_hours: int) -> list[str]:
    sentences = [
        f"На ближайшие {horizon_hours} ч агент ожидает {_RU_LEVELS[sig.level]} выработку: в среднем "
        f"{_ru_pct(sig.average)} от номинальной мощности (диапазон {_ru_pct(sig.minimum)}–{_ru_pct(sig.maximum)})."
    ]
    if sig.correlation is not None and sig.peak_wind is not None:
        sentences.append(
            f"Выработка тесно следует за скоростью ветра (r = {_ru_num(sig.correlation, 2)}); пик ожидается "
            f"{_ru_time(sig.peak_time)}, при ветре около {_ru_num(sig.peak_wind, 1)} м/с."
        )
    if sig.low_window is not None:
        sentences.append(
            f"Окно низкой выработки ожидается с {_ru_time(sig.low_window[0])} до {_ru_time(sig.low_window[1])}: "
            "ветер ослабевает до порога включения турбин."
        )
    if sig.comparison is not None:
        leader, lagger, gap = sig.comparison
        sentences.append(f"Турбина {leader}, по прогнозу, выработает примерно на {_ru_pct(gap)} больше, чем турбина {lagger}.")
    elif sig.turbines_equal:
        sentences.append("Обе турбины, по прогнозу, будут работать практически одинаково.")
    if sig.cold_mean_temperature is not None:
        sentences.append(
            f"Холодный воздух (в среднем {_ru_num(sig.cold_mean_temperature, 0)} °C) плотнее, что немного повышает "
            "выработку при той же скорости ветра."
        )
    if not sig.recompute.performed:
        sentences.append(
            "Самопроверка агента не нашла причин для пересчёта: нет значений вне диапазона, резервной погоды "
            "и физически противоречивых часов."
        )
    else:
        reasons = "; ".join(_RU_REASONS[code] for code in sig.recompute.reason_codes) or "самопроверка выявила проблему"
        outcome = _RU_OUTCOMES.get(sig.recompute.outcome_code or "", "")
        sentences.append(f"Агент один раз пересчитал прогноз, потому что {reasons}: {outcome}")
    if sig.warning_count:
        noun = _ru_plural(sig.warning_count, "эксплуатационное предупреждение", "эксплуатационных предупреждения",
                          "эксплуатационных предупреждений")
        sentences.append(f"Выявлено {sig.warning_count} {noun}, проверьте их перед планированием диспетчеризации.")
    else:
        sentences.append("Все значения в пределах физических границ, эксплуатационных аномалий не обнаружено.")
    return sentences


def _recompute_sentence(recompute: RecomputeInfo) -> str:
    if not recompute.performed:
        return (
            "The agent's self-check found no reason to recompute: no out-of-range values, "
            "no fallback weather and no physically inconsistent hours."
        )
    reasons = "; ".join(recompute.reasons) or "the analysis flagged the first result"
    return f"The agent recomputed the forecast once because {reasons}: {recompute.outcome}"


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
