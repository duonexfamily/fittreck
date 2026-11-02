# TECH_SPEC — техническая спецификация

> Как реализуем проект технически. Продукт и функции — в `PROJECT_IDEA.md`, краткие правила — в `CLAUDE.md`.
> При изменении архитектуры, инфраструктуры или API — обновлять этот файл.

---

## 1. Инфраструктура

| Компонент | Где | Зачем |
|---|---|---|
| Код | GitHub, ветка `main` | Хранение кода, CI, источник деплоя |
| Хостинг | Railway, 1 сервис | Бот + API + статика Mini App, HTTPS-домен |
| База данных | PostgreSQL в том же проекте Railway | Хранение всех данных |
| CI | GitHub Actions | Линт и тесты на каждый PR и push |

### 1.1. Ключевые решения
- **Один сервис на Railway, один домен.** FastAPI одновременно:
  - принимает webhook Telegram на `/telegram/webhook`;
  - отдаёт REST API на `/api/v1/...`;
  - отдаёт собранный Mini App (статика) на `/`.
  Плюсы: один деплой, один HTTPS-домен, нет CORS (frontend и API на одном origin).
- **БД — PostgreSQL от Railway** (решение от 2026-11-02 вместо Supabase: одна платформа,
  один аккаунт, бэкапы, подключение по приватной сети). Авторизация — через Telegram `initData`.
  Supabase не используется.
- **Redis не используем на старте.** Сложный ввод идёт в Mini App, FSM бота минимальна → `MemoryStorage`.
  Напоминания считаются из БД, состояние в памяти не нужно. Redis добавим, только если понадобится.
- **Бот в продакшене — webhook, локально — polling.**
- **Строго 1 реплика** на Railway: планировщик напоминаний работает внутри процесса.
  При масштабировании нужна блокировка (Postgres advisory lock), иначе напоминания задвоятся.

### 1.2. Окружения

| | Локально (dev) | Продакшен (prod) |
|---|---|---|
| Бот | отдельный dev-бот из BotFather, polling | основной бот, webhook |
| БД | Supabase `fittrack-dev`, Session pooler (eu-west-1). Регистрация в Railway закрыта с 21.10.2026 | PostgreSQL Railway по приватной сети (или другой хостинг, если Railway не откроется) |
| Mini App | `npm run dev` (Vite) + HTTPS-туннель (cloudflared) | статика из FastAPI на домене Railway |
| Секреты | файл `.env` (не в git) | Railway → Variables |

Docker локально не нужен: Railway собирает образ по `Dockerfile` в облаке.

---

## 2. Деплой (CI/CD)

```
feature-ветка → Pull Request → GitHub Actions (lint + tests) → merge в main
→ Railway автоматически собирает Dockerfile → pre-deploy: alembic upgrade head
→ healthcheck /health → переключение трафика на новую версию
```

- Railway подключён к GitHub-репозиторию, авто-деплой ветки `main`.
- В Railway включить опцию **Wait for CI**: деплой только при зелёном CI.
- Конфиг Railway в репозитории: `railway.toml`
  - builder: Dockerfile;
  - `preDeployCommand = "alembic upgrade head"`;
  - `healthcheckPath = "/health"`;
  - `numReplicas = 1`.
- **Dockerfile — multi-stage:**
  1. стадия `node:22-alpine`: `npm ci && npm run build` в `webapp/` → `dist/`;
  2. стадия `python:3.12-slim`: установка backend, копия `dist/` в `backend/static/`, запуск `uvicorn`.
- Webhook регистрируется при старте приложения: `setWebhook(url, secret_token)`.
- Откат — кнопка Redeploy предыдущего деплоя в Railway. Миграции пишем обратимыми (`downgrade`).

---

## 3. Backend

### 3.1. Стек
Python 3.12, FastAPI, uvicorn, aiogram 3.x, SQLAlchemy 2.x async + asyncpg, Alembic,
pydantic v2 + pydantic-settings, APScheduler. Менеджер зависимостей — `uv` (`pyproject.toml` + `uv.lock`).

### 3.2. Запуск приложения (lifespan FastAPI)
1. Чтение конфига, создание engine БД.
2. Создание `Bot` и `Dispatcher`, подключение роутеров.
3. prod: `set_webhook`; dev: запуск polling в фоновой задаче.
4. Старт APScheduler.
5. На остановке: закрытие сессии бота, scheduler, engine.

### 3.3. Структура
```
backend/
  app/
    main.py              # FastAPI app, lifespan, монтирование статики
    core/
      config.py          # Settings (pydantic-settings)
      security.py        # проверка initData
      logging.py
    bot/
      routers/           # start, settings, checkin_quick, admin
      keyboards.py       # кнопки, в т.ч. WebApp-кнопки на экраны
      middlewares.py     # сессия БД, пользователь, троттлинг
      webhook.py         # эндпоинт /telegram/webhook
    api/
      deps.py            # get_session, get_current_user (из initData)
      v1/                # profile, foods, meals, water, weight, exercises,
                         # workouts, templates, checkins, stats, settings
      schemas/           # pydantic-модели запросов и ответов
    services/            # бизнес-логика: nutrition_calc, stats, streaks, reminders
    db/
      base.py  session.py
      models/            # SQLAlchemy-модели
      repositories/      # запросы к БД
    scheduler/jobs.py    # задача рассылки напоминаний
  migrations/            # Alembic
  seeds/                 # тестовые данные для dev (системные справочники — data-миграции)
  tests/
  pyproject.toml
```

### 3.4. Подключение к БД
- В Railway сервис приложения получает `DATABASE_URL=${{Postgres.DATABASE_URL}}` (приватная сеть).
- Локально — `DATABASE_PUBLIC_URL` из сервиса Postgres в Railway, вставляется в `backend/.env`.
- Схему `postgresql://` код сам меняет на `postgresql+asyncpg://` (`core/config.py`).
- Спецсимволы пароля в URL кодируются: `%` → `%25`, `@` → `%40`, `/` → `%2F` и т.д.
- Пул SQLAlchemy небольшой: `pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`.
- Схема БД создаётся **только миграциями Alembic**, не руками через UI.
- `ENABLE ROW LEVEL SECURITY` в миграциях оставлен как защита на случай переезда на Supabase; на работу backend (владелец таблиц) не влияет.

---

## 4. Авторизация Mini App

1. Mini App при запуске берёт `initData` из Telegram SDK.
2. Каждый запрос к API: заголовок `Authorization: tma <initData>`.
3. Backend (`core/security.py`):
   - вычисляет `secret_key = HMAC_SHA256("WebAppData", BOT_TOKEN)`;
   - проверяет `hash` из `initData` через `hmac.compare_digest`;
   - проверяет `auth_date`: не старше 24 часов;
   - достаёт `user.id` → находит или создаёт пользователя.
4. Ошибка проверки → `401`. `user_id` из тела запроса или query **никогда** не используется.
5. Все запросы репозиториев фильтруются по `user_id` текущего пользователя.

Для тестов: фикстура генерирует корректно подписанный `initData` тестовым токеном. Обхода проверки в коде нет ни в каком режиме.

---

## 5. REST API (v1)

Префикс `/api/v1`, JSON, даты — ISO 8601, время в ответах — UTC.

| Метод и путь | Назначение |
|---|---|
| `GET /me` | Профиль, цели, настройки, флаг «анкета пройдена» |
| `PUT /me/profile` | Анкета: пол, дата рождения, рост, цель, активность, часовой пояс |
| `GET /me/targets` | Рассчитанная норма ккал и БЖУ |
| `PUT /me/settings` | Напоминания, время, тихие часы |
| `DELETE /me` | Удалить все данные пользователя |
| `GET /foods?query=` | Поиск по справочнику продуктов |
| `POST /foods` | Свой продукт |
| `GET /meals?date=` | Все 4 приёма пищи за день (включая пустые) + итоги; без `date` — сегодня в поясе пользователя |
| `POST /meals/{meal_type}/items` | Добавить продукт в приём пищи |
| `PATCH/DELETE /meal-items/{id}` | Изменить граммовку (КБЖУ пересчитывается из снимка) / удалить |
| `GET /water?date=`, `POST /water` | Вода |
| `GET /weight?from=&to=`, `POST /weight` | Вес |
| `GET /exercises?query=&muscle=` | Каталог упражнений |
| `POST /exercises` | Своё упражнение |
| `GET /workouts?from=&to=` | Тренировки за период (для календаря) |
| `POST /workouts`, `GET/PATCH/DELETE /workouts/{id}` | Тренировка с подходами |
| `GET/POST /templates`, `POST /templates/{id}/start` | Шаблоны тренировок |
| `GET /checkins?from=&to=`, `PUT /checkins/{date}` | Чек-ин: сон, энергия, стресс, настроение |
| `GET /stats/summary?period=` | Данные для графиков: вес, ккал, сон, энергия, объём тренировок |
| `GET /stats/streaks` | Серии и достижения |

Служебные: `GET /health` (без авторизации), `POST /telegram/webhook` (проверка заголовка `X-Telegram-Bot-Api-Secret-Token`).

---

## 6. База данных

Все таблицы: `id` (bigint identity), `created_at`, `updated_at` (`timestamptz`). Связи с `ON DELETE CASCADE` от `users`.

| Таблица | Ключевые поля |
|---|---|
| `users` | `telegram_id` (unique), `first_name`, `username`, `sex`, `birth_date`, `height_cm`, `goal`, `activity_level`, `timezone`, `onboarded_at` |
| `user_settings` | `user_id`, `reminders` (jsonb: тип → время, вкл/выкл), `quiet_from`, `quiet_to` |
| `foods` | `name`, `kcal`, `protein`, `fat`, `carbs` (на 100 г), `owner_id` (null = системный) |
| `meals` | `user_id`, `date`, `meal_type` (breakfast/lunch/dinner/snack) |
| `meal_items` | `meal_id`, `food_id` (nullable), `name`, `grams`, `kcal`, `protein`, `fat`, `carbs` (снимок значений) |
| `water_logs` | `user_id`, `amount_ml`, `logged_at` |
| `body_metrics` | `user_id`, `date`, `weight_kg`, `waist_cm`… |
| `exercises` | `name`, `muscle_group`, `kind` (strength/cardio/stretch), `owner_id` |
| `workouts` | `user_id`, `date`, `status` (planned/done), `started_at`, `finished_at`, `rpe`, `note` |
| `workout_sets` | `workout_id`, `exercise_id`, `set_no`, `reps`, `weight_kg`, `duration_s`, `distance_m` |
| `workout_templates`, `template_exercises` | шаблоны программ |
| `checkins` | `user_id`, `date` (unique вместе), `bed_time`, `wake_time`, `sleep_quality`, `energy`, `stress`, `mood`, `note` |
| `reminder_log` | `user_id`, `type`, `sent_on` — защита от повторной отправки |

- Индексы: `(user_id, date)` на всех дневниковых таблицах, поиск по `foods.name` — `pg_trgm`.
- Системные справочники (`foods`, позже `exercises`) заполняются data-миграцией Alembic: попадают в
  прод через pre-deploy `alembic upgrade head`, откат удаляет только системные записи (`owner_id IS NULL`).
  КБЖУ — усреднённые табличные значения, тест сверяет их с формулой Этуотера (±15%).
- В `meal_items` КБЖУ хранится снимком, чтобы правка справочника не меняла историю.

---

## 7. Бот

- `/start` — регистрация, приветствие, кнопка «Открыть приложение». Установка Menu Button с Mini App.
- `/settings` — краткие настройки напоминаний (полные — в Mini App).
- Быстрый чек-ин кнопками прямо в чате (сон, энергия 1–5) — пишет в ту же таблицу `checkins`.
- **Переход в нужный экран:** inline-кнопка `WebAppInfo(url=f"{WEBAPP_URL}/nutrition?meal=lunch")`.
  Mini App читает путь и параметры через react-router. Для ссылок вне чата — `startapp` у Mini App из BotFather.
- Троттлинг входящих апдейтов middleware.

### 7.1. Напоминания
- APScheduler, задача раз в минуту.
- Выбирает пользователей, у которых в их часовом поясе наступило время напоминания и сегодня ещё нет записи в `reminder_log`.
- Пропускает, если данные уже внесены (например, обед уже записан) или идут тихие часы.
- Отправка с паузой ~30 сообщений/сек (лимиты Telegram). Ошибка `Forbidden` (бот заблокирован) → отключить напоминания пользователю.

---

## 8. Mini App (frontend)

### 8.1. Стек
React 18 + TypeScript + Vite, react-router 7, TanStack Query, Tailwind CSS 4.
Telegram API — официальный скрипт `telegram-web-app.js`, доступ только через обёртку `src/lib/telegram.ts`.
Добавляются по мере надобности: Recharts (графики), Zod (валидация форм), Vitest, ESLint.

### 8.2. Экраны
| Путь | Экран |
|---|---|
| `/` | Главная: сводка дня (ккал, вода, сон, тренировка), быстрые действия |
| `/onboarding` | Анкета и дисклеймер при первом входе |
| `/nutrition` | Дневник питания по приёмам, вода, прогресс ккал и БЖУ |
| `/nutrition/add` | Поиск продукта (пустой запрос — недавние), свой продукт, слайдер граммовки |
| `/nutrition/item/:id` | Изменить граммовку или удалить запись дневника |
| `/weight` | Ввод веса, график |
| `/workouts` | Календарь тренировок |
| `/workouts/:id` | Трекинг тренировки: упражнения, подходы, RPE |
| `/exercises` | Каталог упражнений |
| `/checkin` | Чек-ин: сон, энергия, стресс, настроение слайдерами |
| `/stats` | Графики прогресса |
| `/profile` | Профиль, цели, напоминания, удаление данных |

### 8.3. Правила
- Цвета только из `themeParams` Telegram (CSS-переменные `--tg-theme-*`), светлая и тёмная тема.
- Нативные элементы Telegram: `MainButton` для «Сохранить», `BackButton`, haptic feedback.
- Часовой пояс берётся при онбординге из `Intl.DateTimeFormat().resolvedOptions().timeZone`.
- Ленивые загрузки экранов, графики подгружаются отдельным чанком.
- Локально Vite проксирует `/api` на `localhost:8000`.

---

## 9. Переменные окружения

| Переменная | Пример / описание |
|---|---|
| `ENV` | `dev` или `prod` |
| `BOT_TOKEN` | токен бота из BotFather (dev и prod — разные боты) |
| `WEBHOOK_SECRET` | случайная строка для заголовка webhook |
| `DATABASE_URL` | Railway: `${{Postgres.DATABASE_URL}}`; локально — `DATABASE_PUBLIC_URL` из Railway |
| `WEBAPP_URL` | `https://<app>.up.railway.app` (prod) или адрес туннеля (dev) |
| `ADMIN_IDS` | Telegram ID администраторов через запятую |
| `LOG_LEVEL` | `INFO` |

В репозитории — только `backend/.env.example` без значений. Локально копия — `backend/.env` (в `.gitignore`).

---

## 10. Качество

- **Тесты backend:** unit на расчёты (калории, БЖУ, стрики), на проверку `initData`, интеграционные на API (отдельная тестовая БД).
- **Тесты frontend:** Vitest на утилиты и ключевые компоненты.
- **Линт:** ruff + mypy (backend), ESLint + Prettier + `tsc --noEmit` (frontend).
- **CI (`.github/workflows/ci.yml`):** на PR и push в `main` — линт и тесты обеих частей.
- **Логи:** структурированные, без токенов и данных о здоровье. Смотреть в Railway → Logs.

---

## 11. Ограничения и затраты

- Railway Hobby: $5 в месяц, в них входит $5 на ресурсы. Бот + PostgreSQL небольшого размера
  обычно в это укладываются; при росте нагрузки — доплата по факту. Следить в Railway → Usage.

## 12. Открытые вопросы
- Бэкапы БД: настроить в Railway (Postgres → Backups) перед приглашением пользователей.
- Свой домен или домен Railway `*.up.railway.app`.
- Источник данных для справочника продуктов.
