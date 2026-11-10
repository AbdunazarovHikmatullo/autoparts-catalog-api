# AutoParts Catalog API

REST API каталога автозапчастей на **FastAPI** с асинхронным **SQLAlchemy 2.0** и **PostgreSQL**.
Сервис хранит бренды, категории, модели автомобилей и запчасти, поддерживает поиск, фильтрацию,
сортировку, пагинацию, проверку совместимости запчасти с автомобилем и JWT-аутентификацию.

> Учебно-портфолийный проект: показывает типичную архитектуру backend-сервиса на FastAPI —
> слои схем, моделей, репозиториев и роутеров, миграции, тесты и запуск в Docker.

## Возможности

- CRUD для брендов, категорий, автомобилей и запчастей
- Совместимость «запчасть ↔ автомобиль» (связь многие-ко-многим)
- Поиск по названию, артикулу (SKU) и описанию
- Фильтры: бренд (один или несколько), категория, автомобиль, диапазон цен, наличие на складе
- Сортировка по названию, цене и дате добавления
- Пагинация с метаданными (`total`, `page`, `size`, `pages`)
- JWT-аутентификация: регистрация, вход (OAuth2 password flow), профиль `/auth/me`
- Чтение каталога — публичное, изменение — только для авторизованных пользователей
- Валидация данных через Pydantic v2, понятные ошибки (404 / 409 / 422)
- Миграции Alembic, автоматически применяются при старте контейнера
- Эндпоинт `/health` с проверкой подключения к БД
- Swagger UI (`/docs`) и ReDoc (`/redoc`)

## Стек

| Область | Технологии |
|---|---|
| Язык | Python 3.12 |
| Фреймворк | FastAPI, Uvicorn |
| Валидация | Pydantic v2, pydantic-settings |
| БД и ORM | PostgreSQL 16, SQLAlchemy 2.0 (async), asyncpg |
| Миграции | Alembic |
| Аутентификация | JWT (PyJWT), bcrypt |
| Тесты | pytest, pytest-asyncio, httpx AsyncClient, aiosqlite |
| Инфраструктура | Docker, Docker Compose |

## Структура проекта

```
autoparts-catalog-api/
├── app/
│   ├── api/
│   │   ├── deps.py            # зависимости: сессия БД, текущий пользователь, пагинация
│   │   └── routers/           # auth, brands, categories, vehicles, parts, health
│   ├── core/
│   │   ├── config.py          # настройки из переменных окружения
│   │   └── security.py        # bcrypt и JWT
│   ├── crud/base.py           # универсальный CRUD-репозиторий
│   ├── db/                    # Base, миксин дат, async engine и сессии
│   ├── models/                # модели SQLAlchemy
│   ├── schemas/               # Pydantic-схемы
│   └── main.py                # фабрика приложения
├── alembic/                   # миграции
├── tests/                     # pytest-тесты
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh              # alembic upgrade head + запуск uvicorn
├── requirements.txt
└── requirements-dev.txt
```

## Быстрый старт через Docker

```bash
git clone https://github.com/AbdunazarovHikmatullo/autoparts-catalog-api.git
cd autoparts-catalog-api
cp .env.example .env          # задайте свой JWT_SECRET_KEY
docker compose up --build -d
```

После запуска:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Проверка здоровья: http://localhost:8000/health

Остановить и удалить данные БД: `docker compose down -v`.

## Локальный запуск без Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# по умолчанию используется SQLite (sqlite+aiosqlite:///./autoparts.db)
alembic upgrade head
uvicorn app.main:app --reload
```

## Тесты

```bash
pip install -r requirements-dev.txt
pytest -v
```

Тесты используют отдельную SQLite-базу для каждого теста и не требуют PostgreSQL.

## Примеры запросов

```bash
API=http://localhost:8000/api/v1

# Регистрация
curl -X POST $API/auth/register -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "supersecret", "full_name": "Admin"}'

# Вход — получаем JWT (в поле username передаётся email)
TOKEN=$(curl -s -X POST $API/auth/login \
  -d "username=admin@example.com&password=supersecret" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Создание бренда, категории и автомобиля
curl -X POST $API/brands -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Bosch", "country": "Германия"}'
curl -X POST $API/categories -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Тормозная система", "slug": "brakes"}'
curl -X POST $API/vehicles -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"make": "Toyota", "model": "Camry", "year_from": 2017, "year_to": 2023}'

# Создание запчасти, совместимой с автомобилем id=1
curl -X POST $API/parts -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"sku": "BOSCH-0986494524", "name": "Тормозные колодки передние", "price": "3490.00",
       "quantity": 12, "brand_id": 1, "category_id": 1, "vehicle_ids": [1]}'

# Поиск и фильтры (публично)
curl "$API/parts?q=колодки&in_stock=true&min_price=1000&max_price=5000&ordering=-price&page=1&size=20"
curl "$API/parts?vehicle_id=1&brand_id=1"
curl "$API/vehicles?make=Toyota&year=2020"

# Частичное обновление и удаление
curl -X PATCH $API/parts/1 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"price": "3190.00", "quantity": 5}'
curl -X DELETE $API/parts/1 -H "Authorization: Bearer $TOKEN"
```

Пример ответа списка:

```json
{
  "items": [
    {
      "id": 1,
      "sku": "BOSCH-0986494524",
      "name": "Тормозные колодки передние",
      "price": 3490.0,
      "quantity": 12,
      "in_stock": true,
      "brand": {"id": 1, "name": "Bosch", "country": "Германия", "description": null},
      "category": {"id": 1, "name": "Тормозная система", "slug": "brakes", "description": null},
      "vehicles": [{"id": 1, "make": "Toyota", "model": "Camry", "year_from": 2017, "year_to": 2023, "engine": null}],
      "created_at": "2026-11-11T10:00:00Z",
      "updated_at": "2026-11-11T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

## Эндпоинты

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/health` | публичный | Статус сервиса и БД |
| POST | `/api/v1/auth/register` | публичный | Регистрация |
| POST | `/api/v1/auth/login` | публичный | Получение JWT |
| GET | `/api/v1/auth/me` | JWT | Текущий пользователь |
| GET | `/api/v1/{brands,categories,vehicles,parts}` | публичный | Список с фильтрами и пагинацией |
| GET | `/api/v1/{resource}/{id}` | публичный | Детальная информация |
| POST | `/api/v1/{resource}` | JWT | Создание |
| PATCH | `/api/v1/{resource}/{id}` | JWT | Частичное обновление |
| DELETE | `/api/v1/{resource}/{id}` | JWT | Удаление |

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Автор

Hikmatullo Abdunazarov — Python backend-разработчик.
