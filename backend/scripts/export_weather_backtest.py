"""Export archived weather *forecasts* for the February backtest of the ML part.

For every forecast_origin (local midnight, Asia/Almaty) the script fetches the model
run that had already been PUBLISHED at that moment and keeps the next 48 hours of it.
No observed weather, no reanalysis and no synthetic values are used.

Source: Open-Meteo Single Runs API (one archived model run, identified by its init time).
The Historical Forecast API is deliberately NOT used: it stitches the first hours of
successive runs into one series, so a +30 h target would come from a run issued long
after the origin (look-ahead).

Leakage rule, enforced for every row:
    run_init + PUBLICATION_DELAY <= forecast_origin <= timestamp
`weather_valid_time` is that conservative availability moment (run_init + delay).

Run from the repository root:
    python -m backend.scripts.export_weather_backtest
"""

import argparse
import csv
import logging
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

try:
    from backend.app.core.constants import SITE_TIMEZONE, TURBINES, Turbine
except ModuleNotFoundError:  # executed with backend/ as the working directory
    from app.core.constants import SITE_TIMEZONE, TURBINES, Turbine

logger = logging.getLogger("export_weather_backtest")

REPO_ROOT = Path(__file__).resolve().parents[2]

SINGLE_RUNS_URL = "https://single-runs-api.open-meteo.com/v1/forecast"
DEFAULT_MODEL = "ecmwf_ifs"  # ECMWF IFS HRES 9 km — archived single runs available since 2024-03-14
RUN_CYCLE_HOURS = 6  # IFS runs at 00/06/12/18 UTC
# Open-Meteo docs: "typically 4–6 hours for global models" — use the upper bound.
PUBLICATION_DELAY = timedelta(hours=6)
HORIZON_HOURS = 48

OUTPUT_COLUMNS = (
    "forecast_origin",
    "timestamp",
    "turbine_id",
    "wind_speed",
    "temperature",
    "latitude",
    "longitude",
    "weather_valid_time",
    "weather_source",
)
SKIPPED_COLUMNS = ("forecast_origin", "turbine_id", "reason")


class RunNotAvailableError(RuntimeError):
    """Open-Meteo has no archived data for the requested run."""


@dataclass(frozen=True, slots=True)
class ForecastRow:
    forecast_origin: datetime
    timestamp: datetime
    turbine_id: int
    wind_speed: float
    temperature: float
    latitude: float
    longitude: float
    weather_valid_time: datetime
    weather_source: str


@dataclass(frozen=True, slots=True)
class BlockResult:
    """Outcome for one (forecast_origin, turbine)."""

    origin: datetime
    turbine_id: int
    rows: list[ForecastRow]
    run_init: datetime | None
    grid: tuple[float, float] | None
    wind_fallback_hours: int
    reason: str | None  # set when the block was skipped


# --- Run selection ----------------------------------------------------------------------


def origin_for(day: date, tz: ZoneInfo) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=tz)


def candidate_runs(origin: datetime, max_runs: int) -> list[datetime]:
    """Most recent run cycles (UTC) already published at `origin`, newest first."""
    latest_allowed = (origin - PUBLICATION_DELAY).astimezone(UTC)
    newest = latest_allowed.replace(
        hour=latest_allowed.hour - latest_allowed.hour % RUN_CYCLE_HOURS, minute=0, second=0, microsecond=0
    )
    return [newest - timedelta(hours=RUN_CYCLE_HOURS * i) for i in range(max_runs)]


# --- Fetching ---------------------------------------------------------------------------


def fetch_run(
    client: httpx.Client, turbine: Turbine, run_init: datetime, model: str, retries: int = 3
) -> dict[str, object]:
    params: dict[str, str | float] = {
        "latitude": turbine.latitude,
        "longitude": turbine.longitude,
        "hourly": "wind_speed_100m,wind_speed_10m,temperature_2m",
        "wind_speed_unit": "ms",
        "models": model,
        "run": run_init.strftime("%Y-%m-%dT%H:%M"),
        "timezone": SITE_TIMEZONE,
    }
    for attempt in range(1, retries + 1):
        try:
            response = client.get(SINGLE_RUNS_URL, params=params)
        except httpx.TransportError as exc:
            if attempt == retries:
                raise
            logger.warning("Network error (%s), retry %d/%d", exc, attempt, retries)
            time.sleep(2**attempt)
            continue
        if response.status_code == 400:
            reason = response.json().get("reason", response.text)
            raise RunNotAvailableError(str(reason))
        if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            logger.warning("HTTP %d, retry %d/%d", response.status_code, attempt, retries)
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        payload: dict[str, object] = response.json()
        return payload
    raise RuntimeError("unreachable")


def extract_block(
    payload: dict[str, object],
    turbine: Turbine,
    origin: datetime,
    run_init: datetime,
    model: str,
    tz: ZoneInfo,
) -> tuple[list[ForecastRow], int, str | None]:
    """Rows for origin..origin+47h from one run. Returns (rows, wind_fallback_hours, problem)."""
    if payload.get("timezone") != SITE_TIMEZONE:
        return [], 0, f"API answered in timezone {payload.get('timezone')!r}, expected {SITE_TIMEZONE}"

    hourly = payload["hourly"]
    assert isinstance(hourly, dict)
    by_time = {
        datetime.fromisoformat(stamp).replace(tzinfo=tz): index for index, stamp in enumerate(hourly["time"])
    }
    valid_time = run_init + PUBLICATION_DELAY
    source = f"open-meteo:single-runs:{model}:run={run_init:%Y-%m-%dT%H:%MZ}"

    rows: list[ForecastRow] = []
    fallback_hours = 0
    for hour in range(HORIZON_HOURS):
        target = origin + timedelta(hours=hour)
        index = by_time.get(target)
        if index is None:
            return [], 0, f"run does not cover {target.isoformat()}"
        wind = hourly["wind_speed_100m"][index]
        wind_source = "wind_speed_100m"
        if wind is None:
            wind = hourly["wind_speed_10m"][index]
            wind_source = "wind_speed_10m"
            fallback_hours += 1
        temperature = hourly["temperature_2m"][index]
        if wind is None or temperature is None:
            return [], 0, f"missing wind/temperature at {target.isoformat()}"
        rows.append(
            ForecastRow(
                forecast_origin=origin,
                timestamp=target,
                turbine_id=turbine.turbine_id,
                wind_speed=float(wind),
                temperature=float(temperature),
                latitude=turbine.latitude,
                longitude=turbine.longitude,
                weather_valid_time=valid_time.astimezone(tz),
                weather_source=source if wind_source == "wind_speed_100m" else f"{source};wind=10m",
            )
        )
    return rows, fallback_hours, None


def export_block(
    client: httpx.Client, turbine: Turbine, origin: datetime, model: str, max_runs: int, tz: ZoneInfo
) -> BlockResult:
    attempts: list[str] = []
    for run_init in candidate_runs(origin, max_runs):
        try:
            payload = fetch_run(client, turbine, run_init, model)
        except RunNotAvailableError as exc:
            attempts.append(f"{run_init:%Y-%m-%dT%H:%MZ}: {exc}")
            continue
        except httpx.HTTPError as exc:
            attempts.append(f"{run_init:%Y-%m-%dT%H:%MZ}: request failed: {exc}")
            continue
        rows, fallback_hours, problem = extract_block(payload, turbine, origin, run_init, model, tz)
        if problem:
            attempts.append(f"{run_init:%Y-%m-%dT%H:%MZ}: {problem}")
            continue
        grid = (float(payload["latitude"]), float(payload["longitude"]))  # type: ignore[arg-type]
        return BlockResult(origin, turbine.turbine_id, rows, run_init, grid, fallback_hours, None)
    return BlockResult(origin, turbine.turbine_id, [], None, None, 0, " | ".join(attempts))


# --- Leakage guard ----------------------------------------------------------------------


def assert_no_leakage(rows: list[ForecastRow]) -> None:
    for row in rows:
        if not row.weather_valid_time <= row.forecast_origin <= row.timestamp:
            raise AssertionError(
                f"Leakage: valid_time={row.weather_valid_time.isoformat()} origin={row.forecast_origin.isoformat()} "
                f"timestamp={row.timestamp.isoformat()} (turbine {row.turbine_id})"
            )


# --- Output -----------------------------------------------------------------------------


def display_path(path: Path) -> str:
    resolved = path.resolve()
    return str(resolved.relative_to(REPO_ROOT)) if resolved.is_relative_to(REPO_ROOT) else str(resolved)


def write_csv(path: Path, rows: list[ForecastRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(OUTPUT_COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    row.forecast_origin.isoformat(),
                    row.timestamp.isoformat(),
                    row.turbine_id,
                    f"{row.wind_speed:.2f}",
                    f"{row.temperature:.2f}",
                    f"{row.latitude:.6f}",
                    f"{row.longitude:.6f}",
                    row.weather_valid_time.isoformat(),
                    row.weather_source,
                ]
            )


def write_skipped(path: Path, blocks: list[BlockResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SKIPPED_COLUMNS)
        for block in blocks:
            if block.reason is not None:
                writer.writerow([block.origin.isoformat(), block.turbine_id, block.reason])


def write_report(
    path: Path, blocks: list[BlockResult], origins: list[datetime], model: str, csv_path: Path, skipped_path: Path
) -> None:
    covered = [o for o in origins if all(b.reason is None for b in blocks if b.origin == o)]
    partial = [o for o in origins if o not in covered and any(b.reason is None for b in blocks if b.origin == o)]
    missing = [o for o in origins if o not in covered and o not in partial]
    exported = [b for b in blocks if b.reason is None]
    fallback_total = sum(b.wind_fallback_hours for b in exported)
    grids = sorted({(b.turbine_id, b.grid) for b in exported if b.grid})
    older_runs = [b for b in exported if b.run_init != candidate_runs(b.origin, 1)[0]]

    lines = [
        "# Weather export for the February backtest",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `python -m backend.scripts.export_weather_backtest`.",
        "",
        "## Source",
        "",
        f"- Endpoint: `{SINGLE_RUNS_URL}` (Open-Meteo **Single Runs API**)",
        f"- Model: `{model}` (ECMWF IFS HRES 9 km), variables `wind_speed_100m` "
        "(fallback `wind_speed_10m`), `temperature_2m`, `wind_speed_unit=ms`",
        f"- Timezone: `timezone={SITE_TIMEZONE}` in every request; the API confirmed `{SITE_TIMEZONE}` "
        "(UTC+05:00) and every timestamp in the CSV carries the `+05:00` offset.",
        "- Not used: Historical Forecast API. It stitches the first hours of successive runs into one series, "
        "so a +30 h target would come from a run issued after the origin (look-ahead).",
        "",
        "## Leakage rule",
        "",
        f"For each origin (00:00 {SITE_TIMEZONE}) the newest run with "
        f"`run_init + {int(PUBLICATION_DELAY.total_seconds() // 3600)} h <= forecast_origin` is used "
        "(6 h = upper bound of the publication delay for global models per Open-Meteo docs). "
        "If it is not archived, earlier real runs are tried; nothing is ever interpolated or synthesised.",
        "",
        "`weather_valid_time = run_init + 6 h` — the conservative moment the forecast became available. "
        "The export asserts `weather_valid_time <= forecast_origin <= timestamp` for every row.",
        "",
        "## Coverage",
        "",
        f"- Origins requested: **{len(origins)}** ({origins[0].date()} .. {origins[-1].date()})",
        f"- Fully covered (both turbines): **{len(covered)}**",
        f"- Partially covered: **{len(partial)}**",
        f"- Missing: **{len(missing)}**",
        f"- Rows exported: **{sum(len(b.rows) for b in exported)}** "
        f"({HORIZON_HOURS} hourly targets × turbine × origin)",
        f"- Hours using the 10 m wind fallback: **{fallback_total}**",
        f"- Blocks served by an older run than the newest allowed: **{len(older_runs)}**",
        "",
        "Grid points returned by the API:",
        "",
        *[f"- Turbine {turbine_id}: {grid[0]:.4f}, {grid[1]:.4f}" for turbine_id, grid in grids if grid],
        "",
        "Both turbines are ~350 m apart and may fall into the same model grid cell, "
        "in which case their weather is identical.",
        "",
        "## Per origin",
        "",
        "| forecast_origin | run used (UTC) | weather_valid_time | lead time of targets | status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for origin in origins:
        origin_blocks = [b for b in blocks if b.origin == origin]
        ok = [b for b in origin_blocks if b.reason is None]
        if ok and ok[0].run_init:
            run_init = ok[0].run_init
            first_lead = int((origin - run_init).total_seconds() // 3600)
            lead = f"{first_lead}–{first_lead + HORIZON_HOURS - 1} h"
            valid = (run_init + PUBLICATION_DELAY).astimezone(origin.tzinfo).isoformat()
            status = "ok" if len(ok) == len(origin_blocks) else f"partial ({len(ok)}/{len(origin_blocks)} turbines)"
            lines.append(f"| {origin.isoformat()} | {run_init:%Y-%m-%d %H:%M} | {valid} | {lead} | {status} |")
        else:
            lines.append(f"| {origin.isoformat()} | — | — | — | missing |")
    lines += [
        "",
        "## Files",
        "",
        f"- Forecasts: `{display_path(csv_path)}`",
        f"- Skipped blocks log: `{display_path(skipped_path)}` (header only = nothing skipped)",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# --- CLI --------------------------------------------------------------------------------


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 31), help="first origin date")
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 2, 28), help="last origin date")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-runs", type=int, default=3, help="published runs to try per origin, newest first")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data/weather/february_backtest.csv")
    parser.add_argument("--skipped-log", type=Path, default=REPO_ROOT / "data/weather/february_backtest_skipped.csv")
    parser.add_argument("--report", type=Path, default=REPO_ROOT / "reports/weather_backtest_export.md")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    tz = ZoneInfo(SITE_TIMEZONE)

    days = [args.start + timedelta(days=i) for i in range((args.end - args.start).days + 1)]
    origins = [origin_for(day, tz) for day in days]
    turbines = [TURBINES[turbine_id] for turbine_id in sorted(TURBINES)]

    blocks: list[BlockResult] = []
    with httpx.Client(timeout=30) as client:
        for origin in origins:
            for turbine in turbines:
                block = export_block(client, turbine, origin, args.model, args.max_runs, tz)
                blocks.append(block)
                if block.reason:
                    logger.warning("SKIP origin=%s turbine=%d: %s", origin.isoformat(), turbine.turbine_id, block.reason)
                else:
                    logger.info(
                        "ok   origin=%s turbine=%d run=%s", origin.isoformat(), turbine.turbine_id,
                        f"{block.run_init:%Y-%m-%dT%H:%MZ}",
                    )

    rows = [row for block in blocks for row in block.rows]
    assert_no_leakage(rows)
    write_csv(args.output, rows)
    write_skipped(args.skipped_log, blocks)
    write_report(args.report, blocks, origins, args.model, args.output, args.skipped_log)

    skipped = sum(block.reason is not None for block in blocks)
    logger.info("Wrote %d rows to %s (%d block(s) skipped)", len(rows), args.output, skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
