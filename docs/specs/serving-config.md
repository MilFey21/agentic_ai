# Spec: Serving / Config

**Модули**: `docker-compose.yml`, `backend/src/config.py`, `backend/pyproject.toml`  
**Версия**: 1.0  
**Статус**: PoC / Готов к реализации

---

## Назначение

Определяет, как система запускается, конфигурируется и управляется — от локальной разработки до production-деплоя.

---

## 1. Стек и версии

| Компонент | Технология | Версия |
|---|---|---|
| Язык | Python | 3.13 |
| Backend framework | FastAPI | ≥ 0.115 |
| Async event bus | FastStream + Redis Streams | ≥ 0.5 |
| LLM SDK | anthropic | ≥ 0.40 |
| Валидация данных | Pydantic v2 | ≥ 2.0 |
| Dependency management | uv + pyproject.toml | latest |
| База данных | PostgreSQL | 16 |
| ORM | SQLAlchemy | ≥ 2.0 |
| Миграции | Alembic | latest |
| Кэш / брокер | Redis | 7 |
| Контейнеризация | Docker + Docker Compose | latest |
| Линтинг | ruff | latest |
| Frontend | TypeScript + ESLint + Prettier | latest |

---

## 2. Конфигурация (переменные окружения)

Все настройки задаются через `.env`. Нет hardcoded значений в коде.

### Обязательные переменные

```dotenv
# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/windchaser

# Redis
REDIS_URL=redis://localhost:6379/0

# Windchaser Platform
WINDCHASER_API_URL=https://platform.windchaser.example.com
WINDCHASER_SERVICE_TOKEN=...

# Environment
ENVIRONMENT=development   # development | staging | production
```

### Опциональные переменные (с дефолтами)

```dotenv
# Agentные параметры
TUTOR_MAX_HISTORY_TURNS=10         # сколько реплик в LLM-запросе
TUTOR_MAX_TOKENS=512
TUTOR_TEMPERATURE=0.7
EVALUATOR_SUBMISSION_DELAY_S=30    # задержка после task.submitted
EVALUATOR_MAX_TOKENS=1024
EVALUATOR_TEMPERATURE=0.3

# Retriever
THEORY_DIR=backend/course/theory
THEORY_INDEX_PATH=backend/course/theory_index.json
THEORY_MAX_CONTEXT_CHARS=2000

# Circuit breaker
CIRCUIT_BREAKER_THRESHOLD=3        # ошибок за 60 с → аварийный режим
CIRCUIT_BREAKER_WINDOW_S=60
CIRCUIT_BREAKER_PROBE_S=60         # через сколько секунд probe-запрос

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO
```

### Секреты

В PoC: переменные окружения из `.env` (не коммитится в git).  
В production: Kubernetes Secrets, монтируются как env.

---

## 3. Запуск

### Локальная разработка

```bash
# Зависимости
uv sync

# Инфраструктура (Redis, PostgreSQL)
docker compose up redis postgres -d

# Миграции
alembic upgrade head

# Backend
uvicorn backend.src.main:app --reload --port 8000

# Агенты (отдельные процессы)
python -m backend.src.agents.tutor_agent
python -m backend.src.agents.evaluator_agent
python -m backend.src.agents.programmatic_validator
```

### PoC / пилот (Docker Compose)

```bash
# Полный стек одной командой
docker compose up --build

# Переиндексация теории
curl -X POST http://localhost:8000/theory/reindex
```

### Docker Compose сервисы

```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [redis, postgres]

  tutor-agent:
    build: ./backend
    command: python -m src.agents.tutor_agent
    env_file: .env
    depends_on: [redis]
    deploy:
      replicas: 2

  evaluator-agent:
    build: ./backend
    command: python -m src.agents.evaluator_agent
    env_file: .env
    depends_on: [redis]

  validator:
    build: ./backend
    command: python -m src.agents.programmatic_validator
    env_file: .env
    depends_on: [redis]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: windchaser
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data
```

---

## 4. Модели (сводка)

| Агент | Модель ID | Температура | max_tokens | Назначение |
|---|---|---|---|---|
| Tutor — генерация вопроса | claude-3-5-sonnet-20241022 | 0.7 | 512 | Направляющий вопрос |
| Tutor — Stage Classifier | claude-3-5-sonnet-20241022 | 0.1 | 128 | Классификация этапа |
| Evaluator — LLMAnalyzer | claude-3-5-sonnet-20241022 | 0.3 | 1024 | Рубрика + обратная связь |
| Validator — Jailbreak Judge | claude-3-5-sonnet-20241022 | 0.0 | 64 | Детекция jailbreak |

Версии моделей фиксированы явным ID в конфигурации — не используются алиасы (`latest`).

---

## 5. CI/CD и качество кода

| Инструмент | Назначение |
|---|---|
| `ruff check .` | Линтинг Python |
| `ruff format .` | Форматирование Python |
| `pre-commit` | Автоматические проверки перед коммитом |
| `pytest` | Unit + интеграционные тесты |
| `alembic upgrade head` | Миграции при деплое |
| `mypy` | Статическая типизация (опционально) |

**Критерии ready**: все тесты проходят, ruff не выдаёт ошибок, система разворачивается из чистого состояния без ручных действий.

---

## 6. Production (Kubernetes, planned)

- HPA по метрике «длина очереди Redis Streams» (tutor-agent: `queue_length > 20` → scale up)
- Минимальная ёмкость: 50 одновременных студентов
- Resource limits: `cpu: 500m, memory: 512Mi` на pod тьютора; `cpu: 1, memory: 1Gi` на pod оценщика
- Readiness probe: `GET /health` → 200 OK
- Liveness probe: `GET /health/live` → 200 OK (проверяет связь с Redis)
