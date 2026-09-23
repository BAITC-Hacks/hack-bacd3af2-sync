"""Data-quality checks for the weather input and the model output.

Checks never raise: they return a `ValidationReport` so the agent can decide whether
to repair the data, continue with a warning, or stop the pipeline.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from app.core.constants import (
    POWER_MAX,
    POWER_MIN,
    PREDICTION_COLUMNS,
    TEMPERATURE_RANGE_PLAUSIBLE,
    WEATHER_COLUMNS,
    WIND_SPEED_MAX_PLAUSIBLE,
)

Severity = Literal["error", "warning"]
IssueCode = Literal[
    "missing_columns",
    "wrong_row_count",
    "non_hourly_timestamps",
    "missing_values",
    "implausible_values",
    "out_of_bounds",
]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: Severity
    code: IssueCode
    message: str


@dataclass(slots=True)
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def has(self, code: IssueCode) -> bool:
        return any(issue.code == code for issue in self.issues)

    def extend(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues.extend(issues)


def _missing_columns(frame: pd.DataFrame, expected: Sequence[str]) -> list[ValidationIssue]:
    missing = [column for column in expected if column not in frame.columns]
    if not missing:
        return []
    return [
        ValidationIssue("error", "missing_columns", f"Missing contract columns: {', '.join(missing)}.")
    ]


def _row_count(frame: pd.DataFrame, expected_rows: int) -> list[ValidationIssue]:
    if len(frame) == expected_rows:
        return []
    return [
        ValidationIssue(
            "error",
            "wrong_row_count",
            f"Expected {expected_rows} hourly rows, got {len(frame)}.",
        )
    ]


def _hourly_timestamps(frame: pd.DataFrame) -> list[ValidationIssue]:
    timestamps = pd.to_datetime(frame["timestamp"], errors="coerce")
    if timestamps.isna().any():
        return [ValidationIssue("error", "non_hourly_timestamps", "Some timestamps cannot be parsed.")]
    steps = timestamps.diff().dropna()
    if (steps != pd.Timedelta(hours=1)).any() or (timestamps.dt.minute != 0).any():
        return [
            ValidationIssue(
                "error",
                "non_hourly_timestamps",
                "Timestamps are not a continuous hourly sequence aligned to the hour.",
            )
        ]
    return []


def _missing_values(frame: pd.DataFrame, columns: Sequence[str], severity: Severity) -> list[ValidationIssue]:
    counts = {column: int(frame[column].isna().sum()) for column in columns}
    missing = {column: count for column, count in counts.items() if count}
    if not missing:
        return []
    details = ", ".join(f"{column}: {count}" for column, count in missing.items())
    return [ValidationIssue(severity, "missing_values", f"Missing values detected ({details}).")]


def validate_weather_frame(frame: pd.DataFrame, horizon_hours: int) -> ValidationReport:
    """Validate a weather DataFrame against the ML contract.

    NaNs are reported as warnings because short gaps can be interpolated by the agent.
    """
    report = ValidationReport()
    report.extend(_missing_columns(frame, WEATHER_COLUMNS))
    if not report.is_valid:
        return report

    report.extend(_row_count(frame, horizon_hours))
    report.extend(_hourly_timestamps(frame))
    report.extend(_missing_values(frame, ("wind_speed", "temperature"), severity="warning"))

    wind = frame["wind_speed"].dropna()
    temperature = frame["temperature"].dropna()
    t_min, t_max = TEMPERATURE_RANGE_PLAUSIBLE
    if (wind < 0).any() or (wind > WIND_SPEED_MAX_PLAUSIBLE).any():
        report.extend(
            [ValidationIssue("error", "implausible_values", "Wind speed is outside the physical range.")]
        )
    if (temperature < t_min).any() or (temperature > t_max).any():
        report.extend(
            [ValidationIssue("error", "implausible_values", "Temperature is outside the physical range.")]
        )
    return report


def validate_prediction_frame(frame: pd.DataFrame, horizon_hours: int) -> ValidationReport:
    """Validate a model output DataFrame against the ML contract and physical bounds.

    Out-of-bounds values are warnings (the agent clips them); NaNs are errors.
    """
    report = ValidationReport()
    report.extend(_missing_columns(frame, PREDICTION_COLUMNS))
    if not report.is_valid:
        return report

    report.extend(_row_count(frame, horizon_hours))
    report.extend(_hourly_timestamps(frame))
    report.extend(_missing_values(frame, ("predicted_power",), severity="error"))

    power = frame["predicted_power"].dropna()
    below = int((power < POWER_MIN).sum())
    above = int((power > POWER_MAX).sum())
    if below or above:
        report.extend(
            [
                ValidationIssue(
                    "warning",
                    "out_of_bounds",
                    f"{below + above} predicted value(s) outside [{POWER_MIN:g}, {POWER_MAX:g}] "
                    f"({below} below, {above} above).",
                )
            ]
        )
    return report
