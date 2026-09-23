"""Replay the complete agent for every origin, with auditable forecasts and step logs.

python -m backend.scripts.replay_agent --output reports/agent_backtest
Use --weather open_meteo to fetch runs online; --llm explicitly enables paid explanations.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agent.forecast_agent import ForecastAgent
from app.api.deps import get_explainer
from app.core.config import get_settings
from app.core.constants import FORECAST_DATE_MAX, FORECAST_DATE_MIN, SITE_TIMEZONE
from app.ml.real_model import RealModelAdapter
from app.schemas.forecast import ForecastRequest
from app.services.weather_service import ArchivedWeatherProvider, OpenMeteoWeatherProvider, WeatherService


async def replay(agent: ForecastAgent, output: Path, start: date, end: date) -> dict[str, object]:
    if not FORECAST_DATE_MIN <= start <= end <= FORECAST_DATE_MAX:
        raise ValueError("Диапазон запуска: 31 января - 28 февраля 2026 года.")
    output.mkdir(parents=True, exist_ok=False)
    fields = ["forecast_origin", "target_timestamp", "horizon_hours", "turbine_id",
              "predicted_power", "wind_speed_forecast", "temperature_forecast", "model_version"]
    counts = {24: 0, 48: 0}
    failures = []
    sources = set()
    recomputations = 0
    runs = 0
    with (output / "runs.jsonl").open("w", encoding="utf-8") as logs:
        for horizon in (24, 48):
            with (output / f"predictions_{horizon}h.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                day = start
                while day <= end:
                    result = await agent.run(ForecastRequest(forecast_date=day, horizon_hours=horizon, turbine_ids=[1, 2]))
                    logs.write(result.model_dump_json() + "\n")
                    logs.flush()
                    runs += 1
                    sources.add(result.weather_source)
                    if result.status != "completed" or not result.weather_provenance or result.weather_source == "mock":
                        failures.append({"origin": day.isoformat(), "horizon": horizon, "status": result.status})
                    else:
                        for turbine in result.turbines:
                            for lead, point in enumerate(turbine.points, 1):
                                writer.writerow({
                                    "forecast_origin": datetime.combine(day, datetime.min.time()).isoformat(),
                                    "target_timestamp": point.timestamp.isoformat(), "horizon_hours": lead,
                                    "turbine_id": turbine.turbine_id, "predicted_power": point.predicted_power,
                                    "wind_speed_forecast": point.wind_speed, "temperature_forecast": point.temperature,
                                    "model_version": result.model_version,
                                })
                                counts[horizon] += 1
                    recomputations += any(s.id == "recompute" and s.status == "completed" for s in result.agent_steps)
                    print(f"{day} {horizon}h: {result.status} ({result.weather_source})", flush=True)
                    day += timedelta(days=1)
    manifest = {
        "origin_start": start.isoformat(), "origin_end": end.isoformat(), "timezone": SITE_TIMEZONE,
        "runs": runs, "prediction_rows": counts, "weather_sources": sorted(s for s in sources if s),
        "recomputations": recomputations, "failures": failures,
        "horizon_definition": "target_timestamp = forecast_origin + (horizon_hours - 1) hours",
        "explanation_sources": "See each run in runs.jsonl; templates are used unless --llm is set.",
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, default=FORECAST_DATE_MIN)
    parser.add_argument("--end", type=date.fromisoformat, default=FORECAST_DATE_MAX)
    parser.add_argument("--weather", choices=("archive", "open_meteo"), default="archive")
    parser.add_argument("--llm", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    archive = ArchivedWeatherProvider(settings.weather_archive_path)
    service = WeatherService(archive)
    if args.weather == "open_meteo":
        service = WeatherService(OpenMeteoWeatherProvider(settings.open_meteo_url, settings.open_meteo_timeout_s), archive)
    agent = ForecastAgent(service, RealModelAdapter(settings.turbine_model_dir, settings.ml_package_dir),
                          get_explainer() if args.llm else None, explanation_language="ru")
    manifest = asyncio.run(replay(agent, args.output, args.start, args.end))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if manifest["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
