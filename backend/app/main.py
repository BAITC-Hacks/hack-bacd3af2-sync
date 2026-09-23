import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.api.deps import get_model_adapter, get_weather_service
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Fail fast on misconfiguration (e.g. MODEL_ADAPTER=real without the ML package).
    get_model_adapter()
    get_weather_service()
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    description="Agentic AI for hourly wind farm power forecasting (24–48 h).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a readable message alongside the structured Pydantic errors."""
    messages: list[str] = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"] if part != "body")
        message = str(error["msg"]).removeprefix("Value error, ")
        messages.append(f"{field}: {message}" if field else message)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(messages), "errors": messages},
    )


app.include_router(api_router, prefix=settings.api_prefix)
