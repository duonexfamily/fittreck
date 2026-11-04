# CLAUDE.md — памятка проекта

Связка **Telegram-бот + Mini App** для контроля здоровья: **тренировки, питание, состояние, сон**.
Бот — помощник: регистрация, напоминания, чек-ины, мотивация, кнопки в нужный экран Mini App.
Mini App — веб-приложение внутри Telegram: графики, календарь тренировок, дневник питания.
Проект **некоммерческий и полностью бесплатный**: без рекламы, подписок и платных функций.

Документы (источники истины):
- `PROJECT_IDEA.md` — продукт, функции, риски, план.
- `TECH_SPEC.md` — архитектура, инфраструктура, API, БД, деплой.

## Язык и общение
- Отвечать пользователю на русском.
- Тексты бота и интерфейса — на русском, дружелюбно, кратко.
- Комментарии в коде — на русском. Имена переменных, функций, таблиц — на английском.

## Инфраструктура
- Прод: **Railway** (регистрация снова открыта, решение 03.11.2026) + **PostgreSQL в Railway**.
  Код: GitHub, `main` → авто-деплой по `railway.toml` (Wait for CI, pre-deploy `alembic upgrade head`).
- Один сервис, одна реплика. FastAPI отдаёт webhook бота, `/api/v1` и статику Mini App.
- Railway Variables: `ENV=prod`, `BOT_TOKEN` (prod-бот), `WEBHOOK_SECRET`,
  `DATABASE_URL=${{Postgres.DATABASE_URL}}`. `WEBAPP_URL` не нужен: берётся из `RAILWAY_PUBLIC_DOMAIN`.
- Префикс `postgresql://` код сам меняет на `+asyncpg`.
- Окружения: dev (dev-бот, polling, туннель, Supabase `fittrack-dev`) и prod (prod-бот, webhook, Railway).
- Запасной вариант — Render free + Supabase (`render.yaml`, самопинг `KEEPALIVE_MINUTES`). Адреса Render
  из РФ недоступны (03.11.2026), поэтому не основной. Миграции также запускает CMD Dockerfile.
- Docker локально не установлен и не нужен: образ собирает хостинг по `Dockerfile`.
- Redis на старте нет: FSM бота — `MemoryStorage`, напоминания считаются из БД.

## Стек
- Backend: Python 3.12, FastAPI, uvicorn, aiogram 3.x, SQLAlchemy 2.x async + asyncpg,
  Alembic, pydantic v2, pydantic-settings. Напоминания — asyncio-цикл без APScheduler. Зависимости — `uv`.
- Mini App: React 18 + TypeScript + Vite, react-router 7, TanStack Query, Tailwind CSS 4,
  официальный `telegram-web-app.js` через обёртку `src/lib/telegram.ts`. Позже: Recharts, Zod.
- Тесты и линт: pytest, ruff, mypy; Vitest, ESLint, Prettier. CI — GitHub Actions.

## Структура
```
backend/app/  main.py, core/, bot/, api/v1/, services/, db/models, db/repositories, scheduler/
backend/      migrations/, seeds/, tests/, pyproject.toml
webapp/src/   pages/, components/, api/, hooks/, lib/telegram.ts
Dockerfile, railway.toml, .github/workflows/ci.yml, .env.example
```

## Архитектурные правила
- Слои backend: `bot`/`api` → `services` → `repositories` → `models`. Зависимости только вниз.
- В хендлерах и роутерах нет SQL и расчётов: только вызов сервиса.
- Бот и API используют одни и те же сервисы, логику не дублировать.
- Mini App общается только с нашим API (`/api/v1`, тот же origin).
- Сложный ввод — в Mini App. В чате бота — короткие действия кнопками.
- Напоминания содержат WebApp-кнопку на конкретный экран (`{WEBAPP_URL}/nutrition?meal=lunch`).
- Все времена в БД — UTC (`timestamptz`). Показ — в часовом поясе пользователя.
- Схема БД — только миграциями Alembic, не руками через UI. Миграции обратимые.
- В `meal_items` КБЖУ хранится снимком.

## Mini App: правила UI
- Цвета только из темы Telegram (`--tg-theme-*`), светлая и тёмная тема.
- `MainButton`, `BackButton`, haptic feedback. Mobile-first, iOS и Android.
- Ввод — слайдеры, чекбоксы, поиск. Ленивые загрузки экранов.

## Безопасность
- Каждый запрос API: `Authorization: tma <initData>`, проверка HMAC-подписи и `auth_date` ≤ 24 ч.
  Ошибка — 401. `user_id` только из проверенного `initData`. Обхода проверки нет ни в каком режиме.
- Все запросы к данным фильтруются по `user_id` текущего пользователя.
- Webhook проверяет заголовок `X-Telegram-Bot-Api-Secret-Token`.
- RLS включается в миграции на каждой таблице (защита на случай переезда на Supabase).
- Секреты — только в `.env` (локально) и Railway → Variables. В git — только `.env.example`.
- Секреты не просить в чат и не вставлять в код. Не логировать токены и данные о здоровье.

## Расчёты и дисклеймер
- Норма калорий — Миффлин — Сан Жеор. Все расчёты покрыты unit-тестами.
- Дисклеймер обязателен: приложение информационное, не заменяет врача.

## Команды (после создания каркаса)
```
cd backend; uv sync; uv run alembic upgrade head; uv run python -m app.main   # uv не в PATH → python -m uv
uv run alembic revision --autogenerate -m "msg"
uv run pytest; uv run ruff check .; uv run ruff format .; uv run mypy app
cd webapp; npm ci; npm run dev; npm run build; npm run lint; npm test
```
Mini App в Telegram локально: `npm run dev -- --host 127.0.0.1` в `webapp/`, затем пользователь сам запускает
`tools/cloudflared.exe tunnel --no-autoupdate --url http://127.0.0.1:5173` (туннель запускает только он),
адрес `https://*.trycloudflare.com` → `WEBAPP_URL` в `backend/.env` → перезапуск бота. Адрес меняется при каждом запуске.

## Этапы
0. Памятки, спецификация, каркас — ✅ готово.
1. MVP: бот `/start`, скелет Mini App, проверка `initData` — ✅ работает локально (02.11.2026).
   Деплой на Railway — ✅ (04.11.2026). Напоминания и `/settings` — ✅ (04.11.2026).
2. Mini App: питание, вода, вес, цели по калориям — ✅ (04.11.2026): быстрая запись КБЖУ, избранное, «Профиль и цели».
3. Mini App: каталог упражнений и трекинг тренировок с RPE — ✅ (04.11.2026).
   Шаблоны и календарь тренировок — ✅ (05.11.2026). Чек-ины сна и самочувствия — ✅ (05.11.2026).
   Дальше: быстрый чек-ин кнопками в боте.
4. Графики, умные напоминания, стрики, полировка, релиз.

## Правила работы ИИ-ассистента
- Перед крупной задачей сверяться с `PROJECT_IDEA.md` и `TECH_SPEC.md`.
- Изменил функционал — обнови `PROJECT_IDEA.md`; архитектуру или API — `TECH_SPEC.md`.
- Не предлагать монетизацию, рекламу, платные функции.
- Новые зависимости согласовывать с пользователем.
- Работа через ветки и PR, в `main` напрямую не пушить. Коммит и пуш — по просьбе пользователя.
- Маленькие проверяемые шаги. После изменений — тесты и линтеры.
