# WindAI — Backend

FastAPI-сервис с агентом прогнозирования выработки ВЭС. Общее описание, API и контракт с ML-частью — в [корневом README](../README.md).

## Запуск

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API: http://localhost:8000/api
- Swagger UI: http://localhost:8000/docs

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

Тесты проверяют API и поведение агента на «сломанных» данных: выход за `[0, 1]` (clip + warning), NaN в прогнозе (стоп + `skipped`), падение модели, пропуски в погоде (интерполяция), недоступный погодный API (фолбэк).

## Слои

| Слой | Путь | Ответственность |
|---|---|---|
| API | `app/api/` | Тонкие роуты, DI в `deps.py` — единственное место выбора реализаций |
| Schemas | `app/schemas/` | Pydantic-модели запросов и ответов |
| Services | `app/services/` | Погода, аналитика прогноза, метрики, точка входа прогноза |
| Agent | `app/agent/` | `ForecastAgent` и примитивы шагов (контекст, таймер, skipped) |
| ML | `app/ml/` | `ModelAdapter` (контракт), `MockModelAdapter`, `RealModelAdapter` |
| Config | `app/core/` | Настройки из env, константы, колонки контракта, пороги аномалий |
| Utils | `app/utils/` | Валидация DataFrame, работа со временем |

## Переменные окружения

См. [`.env.example`](.env.example): `APP_NAME`, `ENV`, `CORS_ORIGINS`, `MODEL_ADAPTER` (`mock` | `real`), `WEATHER_PROVIDER` (`mock` | `open_meteo`).

> Координаты турбин задаются в `app/core/constants.py` (`TURBINES`) — сверьте их с координатами из материалов кейса: они уходят в погодный API и в weather DataFrame для модели.
