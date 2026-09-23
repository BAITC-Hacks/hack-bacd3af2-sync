from dataclasses import dataclass
from datetime import date
from typing import Final, Literal

SERVICE_NAME: Final = "wind-ai-backend"

HorizonHours = Literal[24, 48]
TurbineId = Literal[1, 2]

ALLOWED_HORIZONS: Final[tuple[int, ...]] = (24, 48)
ALLOWED_TURBINE_SETS: Final[tuple[tuple[int, ...], ...]] = ((1,), (2,), (1, 2))

FORECAST_DATE_MIN: Final = date(2026, 2, 1)
FORECAST_DATE_MAX: Final = date(2026, 2, 28)


@dataclass(frozen=True, slots=True)
class Turbine:
    turbine_id: int
    name: str
    latitude: float
    longitude: float


# NOTE: coordinates must match the ones provided in the case materials.
# They are forwarded to the weather provider and to the ML model via the weather DataFrame.
TURBINES: Final[dict[int, Turbine]] = {
    1: Turbine(turbine_id=1, name="Turbine 1", latitude=51.6240, longitude=73.1020),
    2: Turbine(turbine_id=2, name="Turbine 2", latitude=51.6315, longitude=73.1185),
}

# --- Contract with the ML part (see README → "ML integration contract") -----------------

WEATHER_COLUMNS: Final[tuple[str, ...]] = (
    "timestamp",
    "wind_speed",
    "temperature",
    "forecast_origin",
    "latitude",
    "longitude",
)

PREDICTION_COLUMNS: Final[tuple[str, ...]] = (
    "forecast_origin",
    "timestamp",
    "turbine_id",
    "horizon_hour",
    "wind_speed",
    "temperature",
    "predicted_power",
    "model_version",
)

# --- Physical sanity bounds -------------------------------------------------------------

POWER_MIN: Final = 0.0
POWER_MAX: Final = 1.0
WIND_SPEED_MAX_PLAUSIBLE: Final = 60.0  # m/s, anything above is a data error
TEMPERATURE_RANGE_PLAUSIBLE: Final = (-60.0, 60.0)  # °C

# --- Operational anomaly thresholds -----------------------------------------------------

CUT_OUT_WIND_SPEED: Final = 25.0  # m/s, turbines shut down above this
CUT_IN_WIND_SPEED: Final = 3.0  # m/s, turbines do not generate below this
EXTREME_COLD_C: Final = -30.0  # °C, cold-weather operating limits
POWER_RAMP_ALERT: Final = 0.45  # normalized power change within one hour
LOW_GENERATION_AVG: Final = 0.10  # average normalized power considered "calm period"
