# Keitaro wrapper

Обёртка над [Keitaro](https://keitaro.io) Admin API (тестовое задание Adrobot).

- [`backend/`](backend) — JSON-API на FastAPI, SQLAlchemy 2.0 (async), Alembic, httpx;
- `frontend/` — React-приложение (в разработке).

1. **Создание кампании.** Name, Geo (`MX,AU,RO`), оффер — в Keitaro создаётся кампания с доменом,
   группой и источником и двумя потоками: страны из Geo → редирект на Google, все остальные → оффер.
2. **Редактор офферов.** Загрузка потоков кампании из Keitaro, черновик изменений (Add, Remove,
   Bring back, Pin, ручная доля) с автоматическим пересчётом долей, Push в Keitaro и Cancel.
   Повторная загрузка сливается с черновиком: изменения из Keitaro помечаются, а если оффер изменён
   и у нас, и в Keitaro, — это конфликт, который решается по каждому офферу.

## Быстрый старт (Docker)

Нужны Docker с Compose и ключ Keitaro Admin API.

```bash
cp backend/.env.example backend/.env
```

Впишите в `backend/.env` ключ `KEITARO_ADMIN_TOKEN` (и при необходимости `KEITARO_URL`), затем:

```bash
docker compose up --build
```

API поднимется на <http://localhost:8000>, интерактивная документация — <http://localhost:8000/docs>.
Миграции применяются автоматически при каждом старте контейнера (Alembic накатывает только
недостающие). База — SQLite в томе `data`, данные переживают пересоздание контейнера;
`docker compose down -v` удаляет их.

## Локальный запуск

Нужны Python ≥ 3.12 и [uv](https://docs.astral.sh/uv/). Все команды бэкенда выполняются
из папки `backend/`.

```bash
cd backend
```

```bash
uv sync
```

```bash
cp .env.example .env
```

Заполните `.env`, затем примените миграции и запустите сервер:

```bash
uv run alembic upgrade head
```

```bash
uv run uvicorn app.main:app --reload
```

## Миграции

Схема БД ведётся только через Alembic (`backend/migrations/`), команды — из `backend/`.
Адрес базы берётся из `DATABASE_URL` (`backend/.env` или окружение); доступ к Keitaro для миграций
не нужен.

| Действие | Команда |
|---|---|
| Применить все миграции | `uv run alembic upgrade head` |
| Откатить последнюю | `uv run alembic downgrade -1` |
| Текущая версия БД | `uv run alembic current` |
| История | `uv run alembic history` |
| Новая миграция после изменения моделей | `uv run alembic revision --autogenerate -m "описание"` |

Автогенерированную миграцию нужно просмотреть перед применением. Тест `backend/tests/test_migrations.py`
проверяет, что миграции накатываются на пустую базу и совпадают с моделями.

## Настройки

Все настройки бэкенда — переменные окружения или `backend/.env`
(пример: [backend/.env.example](backend/.env.example)).

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `KEITARO_URL` | — (обязательна) | Адрес трекера, например `https://tlgk.host` |
| `KEITARO_ADMIN_TOKEN` | — (обязательна) | Ключ Admin API (заголовок `Api-Key`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./app.db` | Адрес БД SQLAlchemy (async-драйвер) |
| `KEITARO_DOMAIN` | `kylovoa.com` | Домен новых кампаний (ищется в Keitaro по имени) |
| `KEITARO_GROUP` | `FORTESTS` | Группа новых кампаний |
| `KEITARO_TRAFFIC_SOURCE` | `FORTESTS` | Источник трафика новых кампаний |
| `CORS_ORIGINS` | `http://localhost:5173` | Адреса фронтенда через запятую |

Для PostgreSQL добавьте драйвер (`uv add asyncpg`) и укажите
`DATABASE_URL=postgresql+asyncpg://user:pass@host/db`.

## API

Все пути — с префиксом `/api`. Полная схема с примерами — `/docs` (Swagger) на запущенном сервере.

**Кампании и офферы**

| Метод и путь | Что делает |
|---|---|
| `GET /health` | Проверка, что сервис жив |
| `GET /offers?q=` | Поиск офферов Keitaro для автокомплита (по названию или id, до 20) |
| `POST /campaigns` | Создать кампанию: `{"name", "geo": "MX,AU", "offer_id"}` → 201 со ссылкой |
| `GET /campaigns` | Кампании, созданные через обёртку, новые сверху |

**Редактор.** Поток адресуется своим id в Keitaro. Каждое действие возвращает поток целиком
с пересчитанными долями.

| Метод и путь | Кнопка / действие |
|---|---|
| `POST /campaigns/{id}/fetch` | Fetch streams from KT: загрузить потоки и слить с черновиком |
| `GET /campaigns/{id}/streams` | Текущее состояние редактора из БД, без запроса в Keitaro |
| `POST /streams/{id}/offers` | Add: `{"offer_id"}` |
| `POST /streams/{id}/offers/{offer_id}/remove` | Remove: оффер остаётся серым с долей 0% |
| `POST /streams/{id}/offers/{offer_id}/bring-back` | Bring back |
| `POST /streams/{id}/offers/{offer_id}/pin` · `/unpin` | Закрепить долю / снять пин |
| `PUT /streams/{id}/offers/{offer_id}/share` | Ручная доля `{"share": 0..100}`, закрепляется |
| `POST /streams/{id}/offers/{offer_id}/resolve` | Решить конфликт: `{"keep": "mine" \| "keitaro"}` |
| `POST /streams/{id}/resolve` | Решить все конфликты потока одинаково |
| `POST /streams/{id}/acknowledge` | Снять пометки об изменениях из Keitaro |
| `POST /streams/{id}/push` | Push to KT: опубликовать черновик |
| `POST /streams/{id}/cancel` | Cancel: вернуть опубликованное состояние |

**Ошибки** приходят как `{"detail": "сообщение"}`:
404 — нет потока или оффера (поток сначала нужно загрузить через Fetch);
409 — действие не подходит состоянию (например, Push при нерешённых конфликтах или если поток
изменили в Keitaro после загрузки); 400 — доли невозможно распределить; 422 — невалидный запрос;
502 — ошибка Keitaro; 503 — в Keitaro нет домена, группы или источника из настроек.

**Как считаются доли.** Активные незакреплённые офферы делят поровну то, что осталось после
закреплённых; остаток от деления получают верхние (3 оффера → 34/33/33). Удалённые — 0%.
Подробности и спорные моменты ТЗ — [docs/DISPUTED.md](docs/DISPUTED.md).

## Тесты и проверки

Из папки `backend/`:

```bash
uv run pytest
```

```bash
uv run ruff check . && uv run ruff format --check .
```

Тесты не ходят во внешний мир: Keitaro мокается через `respx`, БД — SQLite in-memory.

## Структура

```
backend/
  app/
    api/            HTTP-слой: роутеры, зависимости, маппинг ошибок
    services/       бизнес-логика: создание кампании, редактор, пересчёт долей
    clients/keitaro клиент Keitaro Admin API и его схемы
    models/         ORM-модели   repositories/  доступ к БД
    core/ db/       настройки, engine и сессии
  migrations/       миграции Alembic
  tests/            pytest
frontend/           React-приложение (в разработке)
docs/               план, принятые решения, спорные вопросы ТЗ
docker-compose.yml  запуск всего проекта
```

Решения и их причины — [docs/DECISIONS.md](docs/DECISIONS.md), ход работы — [docs/PLAN.md](docs/PLAN.md).
