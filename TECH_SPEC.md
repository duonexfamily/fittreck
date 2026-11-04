# TECH_SPEC — техническая спецификация

> Как реализуем проект технически. Продукт и функции — в `PROJECT_IDEA.md`, краткие правила — в `CLAUDE.md`.
> При изменении архитектуры, инфраструктуры или API — обновлять этот файл.

---

## 1. Инфраструктура

| Компонент | Где | Зачем |
|---|---|---|
| Код | GitHub, ветка `main` | Хранение кода, CI, источник деплоя |
| Хостинг | Railway, 1 сервис (`railway.toml`) | Бот + API + статика Mini App, HTTPS-домен |
| База данных | PostgreSQL в том же проекте Railway | Хранение всех данных |
| CI | GitHub Actions | Линт и тесты на каждый PR и push |

### 1.1. Ключевые решения
- **Хостинг — Railway** (2026-11-03 регистрация снова открылась). Запасной вариант — Render + Supabase
  (`render.yaml`), но адреса Render из РФ недоступны. Ниже — ограничения запасного варианта.
  `WEBAPP_URL` на Railway берётся из `RAILWAY_PUBLIC_DOMAIN`, на Render — из `RENDER_EXTERNAL_URL`.
- Render free + Supabase (запасной, бесплатно и без карты): Render засыпает через 15 мин без
  запросов, Supabase ставит базу на паузу после недели без активности. Решение — самопинг
  (`KEEPALIVE_MINUTES`, `app/core/keepalive.py`): раз в 10 мин `GET {WEBAPP_URL}/health` и `SELECT 1`.
  На Railway самопинг не нужен.
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
- **1 реплика** на Railway: планировщик напоминаний работает внутри процесса.
  Дублей не будет и при двух процессах (например, во время деплоя): отметка в `reminder_log`
  ставится до отправки, её получает только один.

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
- **Render:** Blueprint `render.yaml` — Docker, `plan: free`, `healthCheckPath: /health`, авто-деплой `main`.
  Pre-deploy на free нет, поэтому миграции запускает CMD контейнера перед `app.main`.
  `WEBAPP_URL` не задаётся: берётся из `RENDER_EXTERNAL_URL`. `WEBHOOK_SECRET` генерирует Render;
  в Telegram уходит SHA-256 от него (hex), потому что `secret_token` допускает только `A-Za-z0-9_-`.
- Откат — кнопка Redeploy предыдущего деплоя в Railway/Render. Миграции пишем обратимыми (`downgrade`).

---

## 3. Backend

### 3.1. Стек
Python 3.12, FastAPI, uvicorn, aiogram 3.x, SQLAlchemy 2.x async + asyncpg, Alembic,
pydantic v2 + pydantic-settings. Напоминания — фоновый asyncio-цикл, без APScheduler. Менеджер зависимостей — `uv` (`pyproject.toml` + `uv.lock`).

### 3.2. Запуск приложения (lifespan FastAPI)
1. Чтение конфига, создание engine БД.
2. Создание `Bot` и `Dispatcher`, подключение роутеров.
3. prod: `set_webhook`; dev: запуск polling в фоновой задаче.
4. Старт цикла напоминаний (только при HTTPS-адресе Mini App — в сообщениях кнопка на экран).
5. На остановке: отмена фоновых задач, закрытие сессии бота, engine.

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
| `GET /foods?query=` | Поиск по справочнику продуктов; пустой запрос — недавние. У продукта флаг `favorite` |
| `GET /foods/favorites` | Избранные продукты, последние отмеченные сверху |
| `PUT/DELETE /foods/{id}/favorite` | Отметить избранным / снять отметку (204, повтор ничего не меняет) |
| `POST /foods` | Свой продукт |
| `GET /meals?date=` | Все 4 приёма пищи за день (включая пустые) + итоги; без `date` — сегодня в поясе пользователя |
| `POST /meals/{meal_type}/items` | Добавить продукт в приём пищи |
| `POST /meals/{meal_type}/quick-items` | Быстрая запись: `{date?, name?, kcal, protein, fat, carbs}` порции без продукта |
| `PATCH/DELETE /meal-items/{id}` | `PATCH {grams}` — граммовка продукта (КБЖУ из снимка), `PATCH {quick}` — КБЖУ быстрой записи; не тот вид — 409. `DELETE` — удалить |
| `GET /water?date=`, `POST /water` | Вода за день и ориентир (30 мл/кг, 1,5–3,5 л). `POST {date?, delta_ml}`: прибавить, отрицательное — отмена, ниже 0 не опускается |
| `GET /weight?days=90`, `PUT /weight`, `DELETE /weight/{date}` | Журнал веса. `PUT {date?, weight_kg}` — одна запись в день, перезапись; дата в будущем — 422. Единственную запись удалить нельзя — 409 (по ней считается норма) |
| `GET /exercises?query=&muscle=&kind=` | Каталог: системные и свои, свои выше; фильтр по группе мышц и виду |
| `POST /exercises` | Своё упражнение `{name, muscle_group, kind}` |
| `GET /workouts?from=&to=` | Сводки тренировок за период (по умолчанию 30 дней, максимум 366): упражнения, число подходов, объём |
| `POST /workouts` | Новая тренировка `{date?}`, статус `planned`; начатая сегодня получает `started_at` |
| `GET/PATCH/DELETE /workouts/{id}` | Тренировка с подходами по упражнениям и объёмом. `PATCH {status?, rpe?, note?}` — только переданные поля, `null` очищает; `done` ставит `finished_at`, возврат в `planned` сбрасывает |
| `POST /workouts/{id}/sets` | Подход `{exercise_id, reps?, weight_kg?, duration_s?, distance_m?}` в конец упражнения. Поля по виду: strength — `reps` (+`weight_kg`), cardio — `duration_s` и/или `distance_m`, stretch — `duration_s`; иначе 422 |
| `PATCH/DELETE /workout-sets/{id}` | `PATCH {…значения, done=true}` заменяет значения подхода целиком (те же правила) и отмечает выполненным. `DELETE` — подходы упражнения перенумеровываются без пропусков |
| `GET /templates`, `DELETE /templates/{id}` | Шаблоны пользователя по алфавиту: упражнения, число подходов |
| `POST /templates` | Шаблон из тренировки `{name, workout_id}`: все подходы со значениями. Нет подходов — 422, больше 50 шаблонов — 409 |
| `POST /templates/{id}/start` | Тренировка по шаблону `{date?}`: подходы копируются с `done=false` |
| `GET /checkins?from=&to=` | Чек-ины за период (по умолчанию 30 дней, максимум 366), от старых к новым, с `sleep_minutes` |
| `PUT /checkins/{date}` | Чек-ин за день целиком `{bed_time?, wake_time?, sleep_quality?, energy?, stress?, mood?, note?}`: оценки 1–5, время сна — оба поля или ни одного, пустой чек-ин и дата в будущем — 422 |
| `GET /stats/summary?days=7\|30\|90` | Данные для графиков, по строке на каждый день периода (по умолчанию 30): `weight_kg`, `kcal`, `sleep_minutes`, `sleep_quality`, `energy`, `stress`, `mood` (null — нет данных), `workouts` и `volume_kg` (повторы × вес по выполненным подходам выполненных тренировок) |
| `GET /stats/streaks` | Серия дней подряд с записями `{current, best, today_done, week}`: активный день — еда с продуктами, вода > 0, вес, чек-ин или выполненная тренировка; пока сегодня пусто, серия считается по вчера; рекорд — за последние 365 дней; `week` — 7 дней, последний — сегодня |

Служебные: `GET /health` (без авторизации), `POST /telegram/webhook` (проверка заголовка `X-Telegram-Bot-Api-Secret-Token`).

---

## 6. База данных

Все таблицы: `id` (bigint identity), `created_at`, `updated_at` (`timestamptz`). Связи с `ON DELETE CASCADE` от `users`.

| Таблица | Ключевые поля |
|---|---|
| `users` | `telegram_id` (unique), `first_name`, `username`, `sex`, `birth_date`, `height_cm`, `goal`, `activity_level`, `timezone`, `onboarded_at` |
| `user_settings` | `user_id` (unique), `reminders` (jsonb: `{"lunch": {"on": true, "time": "13:30"}}`; нет ключа — по умолчанию). Строка создаётся при первом изменении |
| `foods` | `name`, `kcal`, `protein`, `fat`, `carbs` (на 100 г), `owner_id` (null = системный) |
| `meals` | `user_id`, `date`, `meal_type` (breakfast/lunch/dinner/snack) |
| `meal_items` | `meal_id`, `food_id` (nullable), `name`, `grams` (null — быстрая запись), `kcal`, `protein`, `fat`, `carbs` (снимок значений) |
| `food_favorites` | `user_id`, `food_id`, уникально `(user_id, food_id)` |
| `water_logs` | `user_id`, `date`, `ml` — сумма за день, уникально `(user_id, date)` |
| `body_metrics` | `user_id`, `date`, `weight_kg`, `waist_cm`… |
| `exercises` | `name`, `muscle_group` (chest/back/shoulders/arms/legs/core/full_body), `kind` (strength/cardio/stretch), `owner_id` (null = системное) |
| `workouts` | `user_id`, `date`, `status` (planned — не завершена, done), `started_at`, `finished_at`, `rpe` (1–10), `note`; индекс `(user_id, date)` |
| `workout_sets` | `workout_id`, `exercise_id`, `set_no` (с 1 внутри упражнения), `reps`, `weight_kg`, `duration_s`, `distance_m`, `done` (false — подход из шаблона не выполнен, в объём и счётчики не входит) |
| `workout_templates` | `user_id`, `name` |
| `template_sets` | `template_id`, `exercise_id`, `position` (порядок в шаблоне), `reps`, `weight_kg`, `duration_s`, `distance_m` |
| `checkins` | `user_id`, `date` (дата пробуждения, unique вместе), `bed_time`, `wake_time` (`time` — время на часах пользователя, не момент), `sleep_quality`, `energy`, `stress`, `mood` (1–5), `note` |
| `reminder_log` | `user_id`, `type`, `sent_on` (местная дата), unique — напоминание за день обработано (отправлено или не нужно) |

- Индексы: `(user_id, date)` на всех дневниковых таблицах, поиск по `foods.name` — `pg_trgm`.
- Системные справочники (`foods`, `exercises`) заполняются data-миграцией Alembic: попадают в
  прод через pre-deploy `alembic upgrade head`, откат удаляет только системные записи (`owner_id IS NULL`).
  КБЖУ — усреднённые табличные значения, тест сверяет их с формулой Этуотера (±15%).
- В `meal_items` КБЖУ хранится снимком, чтобы правка справочника не меняла историю.

---

## 7. Бот

- `/start` — регистрация, приветствие, кнопка «Открыть приложение». Установка Menu Button с Mini App.
- `/settings` — напоминания кнопками: список типов → карточка (вкл/выкл, время −1 ч / −15 / +15 / +1 ч).
  Только после анкеты. Данные кнопок (`rem:<action>:<kind>:<minutes>`) проверяются на сервере.
- `/checkin` и утреннее напоминание «Как спалось?» — быстрый чек-ин кнопками в чате
  (`routers/checkin_quick.py`): качество сна → энергия → настроение, по одному сообщению,
  которое редактируется после каждого ответа. Данные кнопок `chk:<дата>:<поле>:<1–5>`
  проверяются на сервере (поле из списка, оценка 1–5, дата не в будущем). Каждая оценка сразу
  пишется в `checkins` через `services/checkins.save_quick` — меняется только это поле, остальное,
  внесённое в Mini App, не затирается. Кнопка «Подробнее» → `/checkin?date=<дата>`.
- **Переход в нужный экран:** inline-кнопка `WebAppInfo(url=f"{WEBAPP_URL}/nutrition?meal=lunch")`.
  Mini App читает путь и параметры через react-router. Для ссылок вне чата — `startapp` у Mini App из BotFather.
- Троттлинг входящих апдейтов middleware.

### 7.1. Напоминания
- `app/scheduler/jobs.py`: asyncio-цикл, проход в начале каждой минуты. Логика — `services/reminders.py`.
- Типы и значения по умолчанию: сон 08:00 (выкл), вес 08:00 (выкл), завтрак 09:30 (выкл), обед 13:30, вода 16:00, ужин 19:30.
  Кнопка ведёт на экран: `/weight`, `/nutrition?meal=<тип>`, `/nutrition` (вода).
  Напоминание о сне вместо этого сразу показывает оценки быстрого чек-ина на дату пользователя.
- Получатели — прошедшие анкету. Время — в часовом поясе пользователя.
- Пора, если время наступило не дольше 60 минут назад (досылка после перезапуска) и нет записи в `reminder_log`.
- Данные уже внесены (чек-ин за день, приём пищи с продуктами, вода ≥ ориентира, вес за день) → только отметка, без сообщения.
- Отметка до отправки (`INSERT … ON CONFLICT DO NOTHING`), отправка с паузой 40 мс (~25 сообщений/с),
  `RetryAfter` → ждём и повторяем. `Forbidden` (бот заблокирован) → все напоминания пользователя выключаются.
- Тихих часов нет: время каждого напоминания задаёт сам пользователь.

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
| `/onboarding` | Анкета и дисклеймер при первом входе; позже — «Профиль и цели» с пересчётом нормы |
| `/nutrition` | Дневник питания по приёмам, вода, прогресс ккал и БЖУ |
| `/nutrition/add` | Поиск продукта (пустой запрос — избранное и недавние), свой продукт, быстрая запись КБЖУ, слайдер граммовки, ⭐ избранное |
| `/nutrition/item/:id` | Изменить граммовку (или КБЖУ быстрой записи), удалить запись дневника |
| `/weight` | Ввод веса, график |
| `/workouts` | Календарь месяца (выполнено / в плане), тренировки выбранного дня (`?day=`), шаблоны; «Начать» или «Запланировать» на выбранный день |
| `/workouts/:id` | Трекинг тренировки: упражнения, подходы (отметка подходов шаблона), завершение с RPE и заметкой, «Сохранить как шаблон», удаление |
| `/exercises` | Каталог упражнений, фильтры, своё упражнение; `?pick=<id тренировки>` — выбор для тренировки |
| `/checkin` | Чек-ин дня (`?date=`, не в будущем): время сна, оценки 1–5 кнопками, заметка; последние 7 дней |
| `/stats` | Прогресс: период неделя / месяц / 3 месяца; графики веса, калорий (с линией нормы), сна, оценок 1–5 и объёма тренировок — свои SVG, значение за день по касанию |
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
