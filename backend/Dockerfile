# Build context: repository root (see docker-compose.yml) — the image needs both backend/ and ml/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Backend + ML inference stack (catboost), so MODEL_ADAPTER=real works in the container.
COPY backend/requirements.txt backend/requirements-ml.txt backend/
COPY ml/requirements-inference.txt ml/
RUN pip install -r backend/requirements-ml.txt

# Layout mirrors the repository: /srv/backend and /srv/ml (default ML_PACKAGE_DIR / TURBINE_MODEL_DIR).
COPY ml/src ml/src
COPY ml/models ml/models
COPY backend/app backend/app
COPY backend/models backend/models
COPY backend/scripts backend/scripts
COPY data/weather data/weather

WORKDIR /srv/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
