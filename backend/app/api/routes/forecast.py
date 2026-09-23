from fastapi import APIRouter

from app.api.deps import ForecastServiceDep
from app.schemas.forecast import ForecastRequest, ForecastResponse

router = APIRouter(tags=["forecast"])


@router.post("/forecast")
async def create_forecast(request: ForecastRequest, forecast_service: ForecastServiceDep) -> ForecastResponse:
    """Run the forecasting agent for the selected date, turbines and horizon."""
    return await forecast_service.create_forecast(request)
