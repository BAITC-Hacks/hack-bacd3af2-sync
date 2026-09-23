from fastapi import APIRouter

from app.core.constants import SERVICE_NAME
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)
