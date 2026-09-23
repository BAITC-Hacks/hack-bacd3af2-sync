"""Weather acquisition.

WeatherService is the single owner of weather data: it fetches hourly weather for each
turbine and shapes it into the contract DataFrame
(timestamp, wind_speed, temperature, forecast_origin, latitude, longitude)
that is handed to the ModelAdapter. The ML part never fetches weather itself.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import httpx
import numpy as np
import pandas as pd

from app.core.constants import SITE_TIMEZONE, TURBINES, WEATHER_COLUMNS, Turbine
from app.utils.datetime import horizon_end, hourly_range

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
    """Open-Meteo Historical Forecast API, for the interactive demo.

    The series is stitched from the first hours of successive model runs, so it is close to
    analysis, not the forecast issued at forecast_origin (look-ahead). Leakage-free backtest
    weather comes from backend/scripts/export_weather_backtest.py (Single Runs API).
    """

    source = "open_meteo"

    def __init__(self, base_url: str, timeout_s: float) -> None:
        self._base_url = base_url
        self._timeout_s = timeout_s

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        end = horizon_end(start, hours)
        params: dict[str, str | float] = {
            "latitude": turbine.latitude,
            "longitude": turbine.longitude,
            "hourly": "wind_speed_100m,temperature_2m",
            "wind_speed_unit": "ms",
            "timezone": SITE_TIMEZONE,
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.get(self._base_url, params=params)
                response.raise_for_status()
                hourly = response.json()["hourly"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise WeatherProviderError(f"Open-Meteo request failed: {exc}") from exc

        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(hourly["time"]),
                "wind_speed": pd.to_numeric(hourly["wind_speed_100m"], errors="coerce"),
                "temperature": pd.to_numeric(hourly["temperature_2m"], errors="coerce"),
            }
        )
        window = frame[(frame["timestamp"] >= start) & (frame["timestamp"] <= end)]
        return window.reset_index(drop=True)


@dataclass(frozen=True, slots=True)
class WeatherBatch:
    frames: dict[int, pd.DataFrame]
    source: str
    fallback_reason: str | None = None


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
