import asyncio
from datetime import date, datetime

import httpx
import pandas as pd
import pytest

from app.agent.forecast_agent import ForecastAgent
from app.core.config import REPO_ROOT
from app.core.constants import TURBINES
from app.ml.mock_model import MockModelAdapter
from app.schemas.forecast import ForecastRequest
from app.services.weather_service import (
    ArchivedWeatherProvider, OpenMeteoWeatherProvider, WeatherProviderError, WeatherService,
)

ARCHIVE = REPO_ROOT / "data/weather/february_backtest.csv"
ORIGIN = datetime(2026, 1, 31)


@pytest.mark.parametrize("hours", [24, 48])
def test_saved_archive_has_full_coverage_and_asof_provenance(hours):
    provider = ArchivedWeatherProvider(ARCHIVE)
    for origin in pd.date_range("2026-01-31", "2026-02-28", freq="D"):
        for turbine in TURBINES.values():
            frame = asyncio.run(provider.fetch_hourly(turbine, origin.to_pydatetime(), hours))
            assert len(frame) == hours
            assert frame.timestamp.iloc[0] == origin
            provenance = frame.attrs["provenance"]
            assert pd.Timestamp(provenance["available_at"]) <= origin.tz_localize("Asia/Almaty")


@pytest.mark.parametrize("tamper", ["future", "gap", "duplicate", "wrong_site", "observations"])
def test_archive_rejects_invalid_inputs(tmp_path, tamper):
    frame = pd.read_csv(ARCHIVE)
    selected = frame.forecast_origin.str.startswith("2026-01-31") & frame.turbine_id.eq(1)
    index = frame.index[selected][0]
    if tamper == "future":
        frame.loc[selected, "weather_valid_time"] = "2026-02-01T00:00:00+05:00"
    elif tamper == "gap":
        frame = frame.drop(index)
    elif tamper == "duplicate":
        frame = pd.concat([frame, frame.loc[[index]]])
    elif tamper == "wrong_site":
        frame.loc[selected, "latitude"] = 1.0
    else:
        frame.loc[selected, "weather_source"] = "observations"
    path = tmp_path / "weather.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(WeatherProviderError):
        asyncio.run(ArchivedWeatherProvider(path).fetch_hourly(TURBINES[1], ORIGIN, 24))


def test_online_selects_published_single_run(monkeypatch):
    frame = pd.read_csv(ARCHIVE)
    block = frame[frame.forecast_origin.str.startswith("2026-01-31") & frame.turbine_id.eq(1)]
    calls = []

    def respond(request):
        calls.append(dict(request.url.params))
        assert request.url.params["run"] == "2026-01-30T12:00"
        return httpx.Response(200, json={"timezone": "Asia/Almaty", "hourly": {
            "time": [t[:19] for t in block.timestamp],
            "wind_speed_100m": block.wind_speed.tolist(), "wind_speed_10m": block.wind_speed.tolist(),
            "temperature_2m": block.temperature.tolist(),
        }})

    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(respond), **kwargs))
    result = asyncio.run(OpenMeteoWeatherProvider("https://example.test", 1).fetch_hourly(TURBINES[1], ORIGIN, 48))
    assert len(result) == 48 and len(calls) == 1
    assert result.attrs["provenance"]["available_at"] == "2026-01-30T18:00:00+00:00"


def test_network_failure_uses_real_archive_without_synthetic_weather(monkeypatch, tmp_path):
    async def fail(*args, **kwargs):
        raise WeatherProviderError("network down")

    primary = OpenMeteoWeatherProvider("https://example.test", 1)
    monkeypatch.setattr(primary, "fetch_hourly", fail)
    service = WeatherService(primary, ArchivedWeatherProvider(ARCHIVE))
    batch = asyncio.run(service.get_weather([1, 2], ORIGIN, 48))
    assert batch.source == "archive" and len(batch.provenance) == 2
    broken = WeatherService(primary, ArchivedWeatherProvider(tmp_path / "missing.csv"))
    with pytest.raises(WeatherProviderError):
        asyncio.run(broken.get_weather([1], ORIGIN, 24))


def test_changed_archive_causes_one_recompute_with_updated_predictions(tmp_path):
    path = tmp_path / "weather.csv"
    original = pd.read_csv(ARCHIVE)
    original.to_csv(path, index=False)

    class UpdatingArchive(ArchivedWeatherProvider):
        calls = 0

        async def fetch_hourly(self, turbine, start, hours):
            self.calls += 1
            if self.calls == 2:
                updated = original.copy()
                updated["wind_speed"] = 5.0
                updated.to_csv(self.path, index=False)
            return await super().fetch_hourly(turbine, start, hours)

    request = ForecastRequest(forecast_date=date(2026, 1, 31), horizon_hours=24, turbine_ids=[1])
    result = asyncio.run(ForecastAgent(WeatherService(UpdatingArchive(path)), MockModelAdapter()).run(request))
    assert result.status == "completed"
    assert next(s for s in result.agent_steps if s.id == "recompute").status == "completed"
    assert "updated weather" in next(s for s in result.agent_steps if s.id == "analyze_result").message
    assert all(p.wind_speed == 5.0 for p in result.turbines[0].points)
    assert result.weather_provenance[1].sha256
