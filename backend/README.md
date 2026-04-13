# WindChaserSecurity Backend

Backend API для платформы AI Security Training.

## Структура проекта

```
backend/
├── src/
│   ├── __init__.py
│   ├── main.py          # Главный файл FastAPI приложения
│   ├── config.py        # Конфигурация и настройки
│   └── schemas.py       # Pydantic схемы
├── pyproject.toml       # Зависимости проекта
├── ruff.toml            # Настройки линтера
├── Dockerfile           # Docker образ
└── .env.example         # Пример переменных окружения
```

## Установка и запуск

### С помощью uv

```bash
# Установка зависимостей
uv sync

# Применение миграций
uv run alembic upgrade head

# Запуск сервера разработки
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### С помощью Docker

```bash
docker build -t windchaser-backend .
docker run -p 8000:8000 windchaser-backend
```

## База данных

Проект использует PostgreSQL с asyncpg драйвером и SQLAlchemy 2.0.

### Миграции

```bash
# Создать новую миграцию
uv run alembic revision --autogenerate -m "описание_изменений"

# Применить миграции
uv run alembic upgrade head

# Откатить последнюю миграцию
uv run alembic downgrade -1

# История миграций
uv run alembic history
```

## Линтинг и форматирование

```bash
# Проверка кода
uv run ruff check src/

# Автоматическое исправление
uv run ruff check --fix src/

# Форматирование
uv run ruff format src/
```

## API Endpoints

- `GET /` - Информация о API
- `GET /health` - Проверка состояния сервера
- `GET /docs` - Swagger документация (только в local/staging окружении)

