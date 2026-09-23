from fastapi import APIRouter

from app.api.routes import forecast, health, metrics

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(forecast.router)
api_router.include_router(metrics.router)
