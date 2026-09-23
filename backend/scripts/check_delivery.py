"""Check the running Docker application without reading or printing any credentials.

python -m backend.scripts.check_delivery --require-llm --output reports/delivery_checks.json
"""

import argparse
import json
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def get_json(url: str, payload: dict | None = None) -> dict:
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=90) as response:
        return json.load(response)


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.paths.append(attrs["src"])
        elif tag == "link" and attrs.get("rel") == "stylesheet":
            self.paths.append(attrs["href"])


def check(api: str, frontend: str, require_llm: bool) -> dict:
    health = get_json(f"{api}/health")
    assert health["status"] == "ok", health
    metrics = get_json(f"{api}/metrics")
    assert metrics["source"] == "holdout", "Real hold-out metrics are required"
    parser = Assets()
    with urlopen(frontend, timeout=10) as response:
        parser.feed(response.read().decode())
    assert parser.paths, "Frontend has no assets"
    for path in parser.paths:
        with urlopen(urljoin(frontend, path), timeout=10) as response:
            assert response.status == 200 and len(response.read()) > 0
    checks = []
    for day, horizon in [("2026-01-31", 48), ("2026-02-01", 24), ("2026-02-12", 24), ("2026-02-20", 48)]:
        start = time.monotonic()
        result = get_json(f"{api}/forecast", {"forecast_date": day, "horizon_hours": horizon, "turbine_ids": [1, 2]})
        assert result["status"] == "completed", result["agent_steps"]
        assert result["weather_source"] in {"open_meteo", "archive"}
        assert "catboost" in result["model_version"].lower()
        assert {t["turbine_id"] for t in result["turbines"]} == {1, 2}
        assert all(len(t["points"]) == horizon for t in result["turbines"])
        assert all(0 <= p["predicted_power"] <= 1 for t in result["turbines"] for p in t["points"])
        origin = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo("Asia/Almaty"))
        provenance = result["weather_provenance"]
        assert set(provenance) == {"1", "2"}
        assert all(datetime.fromisoformat(p["available_at"]) <= origin for p in provenance.values())
        if require_llm:
            assert result["explanation_source"] == "llm", result["agent_steps"][-1]
        assert any("\u0400" <= c <= "\u04ff" for c in result["explanation"]), "Expected Russian explanation"
        checks.append({
            "forecast_date": day, "horizon_hours": horizon, "status": result["status"],
            "duration_seconds": round(time.monotonic() - start, 2), "weather_source": result["weather_source"],
            "weather_provenance": provenance, "model_version": result["model_version"],
            "explanation_source": result["explanation_source"], "explanation": result["explanation"],
            "agent_steps": result["agent_steps"], "point_counts": [len(t["points"]) for t in result["turbines"]],
        })
        print(f"{day} {horizon}h: passed, {result['weather_source']}, {result['explanation_source']}", flush=True)
    return {"checked_at": datetime.now(UTC).isoformat(), "health": health, "metrics_source": metrics["source"],
            "frontend_assets_checked": len(parser.paths), "forecasts": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000/api")
    parser.add_argument("--frontend", default="http://localhost:5173")
    parser.add_argument("--require-llm", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = check(args.api.rstrip("/"), args.frontend, args.require_llm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
