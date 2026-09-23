"""Weather acquisition.

WeatherService is the single owner of weather data: it fetches hourly weather for each
turbine and shapes it into the contract DataFrame
(timestamp, wind_speed, temperature, forecast_origin, latitude, longitude)
that is handed to the ModelAdapter. The ML part never fetches weather itself.
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import pandas as pd

from app.core.constants import SITE_TIMEZONE, TURBINES, WEATHER_COLUMNS, Turbine
from app.utils.datetime import hourly_range
from scripts.export_weather_backtest import DEFAULT_MODEL, PUBLICATION_DELAY, candidate_runs, extract_block

logger = logging.getLogger(__name__)


class WeatherProviderError(RuntimeError):
    """Raised when a provider cannot deliver weather for the requested window."""


class WeatherProvider(ABC):
    source: str

    @abstractmethod
    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        """Return `hours` rows with columns: timestamp, wind_speed (m/s), temperature (°C)."""


class MockWeatherProvider(WeatherProvider):
    """Deterministic synthetic February weather for a steppe wind farm.

    The same date always yields the same weather; nearby turbines share the synoptic
    pattern with small site-specific deviations.
    """

    source = "mock"

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        timestamps = hourly_range(start, hours)
        t = np.arange(hours, dtype=float)
        hour_of_day = timestamps.hour.to_numpy(dtype=float)

        synoptic = np.random.default_rng(start.toordinal())
        mean_wind = synoptic.uniform(5.0, 10.5)
        swing = synoptic.uniform(2.0, 4.5)
        period = synoptic.uniform(20.0, 40.0)
        phase = synoptic.uniform(0.0, 2 * np.pi)
        storm = synoptic.uniform(8.0, 14.0) if synoptic.random() < 0.2 else 0.0
        storm_center = synoptic.uniform(0.2, 0.8) * hours
        base_temp = synoptic.normal(-11.0, 5.0)
        temp_drift = synoptic.normal(0.0, 4.0) / 24.0

        site = np.random.default_rng(start.toordinal() * 10 + turbine.turbine_id)
        wind_noise = np.convolve(site.normal(0.0, 0.9, hours + 4), np.ones(5) / 5, mode="valid")

        wind = (
            mean_wind
            + swing * np.sin(2 * np.pi * t / period + phase)
            + 0.8 * np.sin(2 * np.pi * (hour_of_day - 9.0) / 24.0)
            + storm * np.exp(-(((t - storm_center) / 5.0) ** 2))
            + wind_noise
            + 0.3 * (turbine.turbine_id - 1.5)
        )
        temperature = (
            base_temp
            + 4.0 * np.sin(2 * np.pi * (hour_of_day - 8.0) / 24.0)
            + temp_drift * t
            + site.normal(0.0, 0.4, hours)
        )

        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "wind_speed": np.clip(wind, 0.2, None).round(2),
                "temperature": temperature.round(2),
            }
        )


class OpenMeteoWeatherProvider(WeatherProvider):
    """An individual archived run published no later than the simulated origin."""

    source = "open_meteo"

    def __init__(self, base_url: str, timeout_s: float) -> None:
        self._base_url = base_url
        self._timeout_s = timeout_s

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        tz = ZoneInfo(SITE_TIMEZONE)
        origin = local_origin(start)
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                for run in candidate_runs(origin, 3):
                    response = await client.get(self._base_url, params={
                        "latitude": turbine.latitude, "longitude": turbine.longitude,
                        "hourly": "wind_speed_100m,wind_speed_10m,temperature_2m",
                        "wind_speed_unit": "ms", "timezone": SITE_TIMEZONE,
                        "models": DEFAULT_MODEL, "run": run.strftime("%Y-%m-%dT%H:%M"),
                    })
                    if response.status_code == 400:
                        continue
                    response.raise_for_status()
                    rows, _, problem = extract_block(response.json(), turbine, origin, run, DEFAULT_MODEL, tz)
                    if problem:
                        continue
                    frame = pd.DataFrame([
                        {"timestamp": r.timestamp, "wind_speed": r.wind_speed, "temperature": r.temperature,
                         "forecast_origin": r.forecast_origin, "weather_valid_time": r.weather_valid_time,
                         "weather_source": r.weather_source, "latitude": r.latitude, "longitude": r.longitude}
                        for r in rows[:hours]
                    ])
                    return validated_archive_block(frame, turbine, start, hours)
        except (httpx.HTTPError, KeyError, ValueError, TypeError, IndexError) as exc:
            raise WeatherProviderError(f"Архив Open-Meteo недоступен: {type(exc).__name__}") from exc
        raise WeatherProviderError("Не найден доступный на момент прогноза погодный запуск.")


def local_origin(start: datetime) -> datetime:
    tz = ZoneInfo(SITE_TIMEZONE)
    return start.replace(tzinfo=tz) if start.tzinfo is None else start.astimezone(tz)


def validated_archive_block(frame: pd.DataFrame, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
    """Validate provenance before discarding archive columns for the model contract."""
    frame = frame.copy()
    origin = pd.Timestamp(local_origin(start))
    for column in ("timestamp", "forecast_origin", "weather_valid_time"):
        frame[column] = pd.to_datetime(frame[column], utc=True, errors="raise").dt.tz_convert(SITE_TIMEZONE)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    expected = pd.date_range(origin, periods=hours, freq="h")
    if len(frame) != hours or not (pd.DatetimeIndex(frame.timestamp) == expected).all():
        raise ValueError("Неполное или повторяющееся почасовое покрытие архива.")
    if not frame.forecast_origin.eq(origin).all() or not frame.weather_valid_time.le(origin).all():
        raise ValueError("Погода не была доступна на момент выпуска прогноза.")
    sources = frame.weather_source.astype(str).unique()
    # A 10 m wind fallback may be annotated per hour; all rows must still share one run.
    runs = {source.split(";", 1)[0] for source in sources}
    if len(runs) != 1 or not next(iter(runs)).startswith(f"open-meteo:single-runs:{DEFAULT_MODEL}:run="):
        raise ValueError("Ожидается один архивный запуск ECMWF IFS.")
    source = next(iter(runs))
    run = pd.Timestamp(source.split("run=", 1)[1])
    if run.tzinfo is None or run.utcoffset() != timedelta(0):
        raise ValueError("Время запуска погоды должно быть указано в UTC.")
    available = run + PUBLICATION_DELAY
    if not frame.weather_valid_time.eq(available).all():
        raise ValueError("Время доступности погоды не соответствует её запуску.")
    values = frame[["wind_speed", "temperature", "latitude", "longitude"]].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError("Архив содержит пропуски или бесконечные значения.")
    if not np.allclose(values.latitude, turbine.latitude) or not np.allclose(values.longitude, turbine.longitude):
        raise ValueError("Координаты архива не соответствуют турбине.")
    frame[["wind_speed", "temperature"]] = values[["wind_speed", "temperature"]]
    frame["timestamp"] = frame.timestamp.dt.tz_localize(None)
    result = frame[["timestamp", "wind_speed", "temperature"]].copy()
    result.attrs["provenance"] = {
        "source": source, "run_init": run.isoformat(), "available_at": available.isoformat(),
        "sha256": hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest(),
    }
    return result


class ArchivedWeatherProvider(WeatherProvider):
    """Local copy of real Single Runs forecasts; never synthesizes missing data."""

    source = "archive"

    def __init__(self, path: Path) -> None:
        self.path = path

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        return await asyncio.to_thread(self._read, turbine, start, hours)

    def _read(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        try:
            frame = pd.read_csv(self.path)
            origins = pd.to_datetime(frame.forecast_origin, utc=True, errors="raise")
            targets = pd.to_datetime(frame.timestamp, utc=True, errors="raise")
            origin = pd.Timestamp(local_origin(start))
            block = frame.loc[origins.eq(origin) & frame.turbine_id.eq(turbine.turbine_id)
                              & targets.ge(origin) & targets.lt(origin + timedelta(hours=hours))]
            return validated_archive_block(block, turbine, start, hours)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise WeatherProviderError(f"Сохранённый архив погоды непригоден: {exc}") from exc


@dataclass(frozen=True, slots=True)
class WeatherBatch:
    frames: dict[int, pd.DataFrame]
    source: str
    fallback_reason: str | None = None

    @property
    def provenance(self) -> dict[int, dict[str, str]]:
        return {key: frame.attrs["provenance"] for key, frame in self.frames.items() if "provenance" in frame.attrs}


class WeatherService:
    def __init__(self, provider: WeatherProvider, fallback: WeatherProvider | None = None) -> None:
        self._provider = provider
        self._fallback = fallback

    async def get_weather(
        self,
        turbine_ids: list[int],
        forecast_origin: datetime,
        horizon_hours: int,
    ) -> WeatherBatch:
        """Fetch weather for all turbines and return contract-shaped DataFrames."""
        try:
            frames = await self._fetch_all(self._provider, turbine_ids, forecast_origin, horizon_hours)
            return WeatherBatch(frames=frames, source=self._provider.source)
        except WeatherProviderError as exc:
            if self._fallback is None:
                raise
            logger.warning("Primary weather provider failed, using fallback: %s", exc)
            frames = await self._fetch_all(self._fallback, turbine_ids, forecast_origin, horizon_hours)
            return WeatherBatch(frames=frames, source=self._fallback.source, fallback_reason=str(exc))

    @property
    def has_fallback(self) -> bool:
        return self._fallback is not None

    @property
    def primary_source(self) -> str:
        return self._provider.source

    @staticmethod
    def inputs_changed(current: dict[int, pd.DataFrame], refreshed: WeatherBatch) -> bool:
        if current.keys() != refreshed.frames.keys():
            return True
        for key, previous in current.items():
            latest = refreshed.frames[key]
            if not previous.equals(latest):
                return True
            old = previous.attrs.get("provenance", {})
            new = latest.attrs.get("provenance", {})
            if old.get("source") != new.get("source"):
                return True
        return False

    async def get_primary_weather(
        self,
        turbine_ids: list[int],
        forecast_origin: datetime,
        horizon_hours: int,
    ) -> WeatherBatch:
        """Fetch from the primary provider only (no fallback). Raises WeatherProviderError."""
        frames = await self._fetch_all(self._provider, turbine_ids, forecast_origin, horizon_hours)
        return WeatherBatch(frames=frames, source=self._provider.source)

    @staticmethod
    def fill_gaps(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """Interpolate missing wind/temperature values in time. Returns (frame, filled_count)."""
        columns = ["wind_speed", "temperature"]
        missing = int(frame[columns].isna().sum().sum())
        if not missing:
            return frame, 0
        repaired = frame.copy()
        repaired[columns] = repaired[columns].interpolate(limit_direction="both")
        return repaired, missing

    async def _fetch_all(
        self,
        provider: WeatherProvider,
        turbine_ids: list[int],
        forecast_origin: datetime,
        horizon_hours: int,
    ) -> dict[int, pd.DataFrame]:
        turbines = [TURBINES[turbine_id] for turbine_id in turbine_ids]
        raw_frames = await asyncio.gather(
            *(provider.fetch_hourly(turbine, forecast_origin, horizon_hours) for turbine in turbines)
        )
        return {
            turbine.turbine_id: self._to_contract(raw, turbine, forecast_origin)
            for turbine, raw in zip(turbines, raw_frames, strict=True)
        }

    @staticmethod
    def _to_contract(raw: pd.DataFrame, turbine: Turbine, forecast_origin: datetime) -> pd.DataFrame:
        frame = raw.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        frame["forecast_origin"] = pd.Timestamp(forecast_origin)
        frame["latitude"] = turbine.latitude
        frame["longitude"] = turbine.longitude
        return frame.loc[:, list(WEATHER_COLUMNS)].sort_values("timestamp").reset_index(drop=True)
