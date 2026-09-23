import logging

from app.agent.forecast_agent import ForecastAgent
from app.schemas.forecast import ForecastRequest, ForecastResponse

logger = logging.getLogger(__name__)


class ForecastService:
    """Application entry point for forecasts; delegates the pipeline to the agent."""

    def __init__(self, agent: ForecastAgent) -> None:
        self._agent = agent

    async def create_forecast(self, request: ForecastRequest) -> ForecastResponse:
        response = await self._agent.run(request)
        logger.info(
            "Forecast %s | date=%s horizon=%sh turbines=%s warnings=%d",
            response.status,
            request.forecast_date,
            request.horizon_hours,
            request.turbine_ids,
            len(response.warnings),
        )
        return response
