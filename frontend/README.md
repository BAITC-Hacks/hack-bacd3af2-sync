# WindAI — Frontend

React-дашборд для агента прогнозирования. Общее описание — в [корневом README](../README.md).

## Запуск

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000/api
npm run dev            # http://localhost:5173
```

| Скрипт | Что делает |
|---|---|
| `npm run dev` | Dev-сервер Vite |
| `npm run typecheck` | Проверка типов (strict) |
| `npm run build` | Typecheck + production-сборка в `dist/` |
| `npm run preview` | Раздача собранного `dist/` на :5173 |

## Архитектура (FSD)

```
src/
├── app/        провайдеры (Query, Router, Motion), роутер, глобальные стили и токены
├── pages/      forecast, about — только композиция виджетов
├── widgets/    самостоятельные блоки дашборда (график, агент, погода, метрики, объяснение…)
├── features/   пользовательские действия: выбор даты / турбины / горизонта, запуск агента
├── entities/   forecast, turbine, agent, metrics — типы, API, маппинг DTO, доменные хелперы
└── shared/     UI-кит, API-клиент, утилиты форматирования, палитра, motion-пресеты
```

Правила:

- Импорты идут только вниз по слоям (`pages → widgets → features → entities → shared`).
- Бэкенд отдаёт snake_case: DTO-типы и `mapForecastResponseDto` живут только в `entities/*/api`; UI работает с доменными типами.
- Статусы шагов агента берутся из ответа бэкенда. `useStepReveal` проигрывает их по очереди ради плавности, но не выдумывает прогресс, сообщения или длительность.
- Цвета серий графиков (`shared/config/palette.ts`) проверены на различимость при дальтонизме на тёмном фоне; цвет закреплён за турбиной, а не за позицией в списке. Ветер и температура — два отдельных графика, без двойной оси Y.
