from fastapi import APIRouter

from app.api.deps import MetricsServiceDep
from app.schemas.metrics import MetricsResponse

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics(metrics_service: MetricsServiceDep) -> MetricsResponse:
    """Validation metrics of the forecasting model per turbine."""
    return metrics_service.get_metrics()
