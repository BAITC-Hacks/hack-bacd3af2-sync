"""Leakage guarantees of the February weather export (no network)."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.constants import TURBINES
from scripts.export_weather_backtest import (
    PUBLICATION_DELAY,
    ForecastRow,
    assert_no_leakage,
    candidate_runs,
    extract_block,
    origin_for,
)

TZ = ZoneInfo("Asia/Almaty")
ORIGIN = origin_for(datetime(2026, 2, 1).date(), TZ)  # 2026-01-31 19:00 UTC


def _payload(run_init: datetime, hours: int = 72, drop_100m_at: int | None = None) -> dict[str, object]:
    start = run_init.astimezone(TZ).replace(tzinfo=None)
    times = [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(hours)]
    wind100: list[float | None] = [8.0] * hours
    if drop_100m_at is not None:
        wind100[drop_100m_at] = None
    return {
        "timezone": "Asia/Almaty",
        "latitude": 43.62,
        "longitude": 78.48,
        "hourly": {"time": times, "wind_speed_100m": wind100, "wind_speed_10m": [5.0] * hours,
                   "temperature_2m": [1.0] * hours},
    }


def test_origin_is_local_midnight_utc_plus_5() -> None:
    assert ORIGIN.astimezone(UTC) == datetime(2026, 1, 31, 19, tzinfo=UTC)


def test_newest_candidate_is_12z_previous_day_and_all_are_published_before_origin() -> None:
    runs = candidate_runs(ORIGIN, max_runs=3)
    assert runs == [datetime(2026, 1, 31, h, tzinfo=UTC) for h in (12, 6, 0)]
    assert all(run + PUBLICATION_DELAY <= ORIGIN for run in runs)
    # The 18Z run would only be published ~00Z — after the origin — so it must never be chosen.
    assert datetime(2026, 1, 31, 18, tzinfo=UTC) not in runs


def test_block_covers_48_hours_from_origin_and_passes_leakage_guard() -> None:
    run = datetime(2026, 1, 31, 12, tzinfo=UTC)
    rows, fallback, problem = extract_block(_payload(run), TURBINES[1], ORIGIN, run, "ecmwf_ifs", TZ)
    assert problem is None and fallback == 0
    assert len(rows) == 48
    assert rows[0].timestamp == ORIGIN and rows[-1].timestamp == ORIGIN + timedelta(hours=47)
    assert rows[0].weather_valid_time == (run + PUBLICATION_DELAY).astimezone(TZ)
    assert_no_leakage(rows)


def test_missing_100m_wind_falls_back_to_10m_and_is_labelled() -> None:
    run = datetime(2026, 1, 31, 12, tzinfo=UTC)
    rows, fallback, _ = extract_block(_payload(run, drop_100m_at=10), TURBINES[1], ORIGIN, run, "ecmwf_ifs", TZ)
    assert fallback == 1
    patched = [row for row in rows if row.weather_source.endswith(";wind=10m")]
    assert len(patched) == 1 and patched[0].wind_speed == 5.0


def test_run_not_covering_horizon_is_rejected_not_padded() -> None:
    run = datetime(2026, 1, 31, 12, tzinfo=UTC)
    rows, _, problem = extract_block(_payload(run, hours=30), TURBINES[1], ORIGIN, run, "ecmwf_ifs", TZ)
    assert rows == [] and problem is not None and "does not cover" in problem


def test_leakage_guard_rejects_forecast_published_after_origin() -> None:
    late = ForecastRow(ORIGIN, ORIGIN, 1, 8.0, 1.0, 43.6, 78.5, ORIGIN + timedelta(hours=1), "test")
    with pytest.raises(AssertionError, match="Leakage"):
        assert_no_leakage([late])
