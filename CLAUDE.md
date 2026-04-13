# CLAUDE.md — WindChaserSecurity

## О проекте

WindChaserSecurity — образовательная платформа для обучения безопасности AI-систем. Студенты практикуются на чат-боте кайтсёрфинг-клуба "WindChaser", развёрнутом на LangFlow.

---

## Архитектура

```
nginx (80) → frontend (React/Vite) + backend (FastAPI) + langflow (7860)
                                         ↓
                              postgres (5432) + minio (S3)
```

**Сервисы:**
- `frontend/` — React 18, Vite, TanStack Query, Zustand, Tailwind CSS, Radix UI
- `backend/` — FastAPI, SQLAlchemy async, Alembic, Python 3.13, uv
- `langflow/` — LLM flows с custom компонентами (guardrails, RAG)
- `postgres/` — PostgreSQL 16 (отдельные БД для backend и langflow)
- `minio/` — S3-хранилище для файлов

---

## Backend

### Структура (domain-driven)
```
backend/src/
├── main.py                 # FastAPI app, роутеры
├── database.py             # async engine, session
├── core_config.py          # глобальные настройки
├── dependencies.py         # общие зависимости
├── exceptions.py           # глобальные исключения
├── schemas.py              # общие Pydantic-схемы
│
├── users/                  # Каждый домен содержит:
│   ├── router.py           #   - эндпоинты
│   ├── schemas.py          #   - Pydantic-модели
│   ├── models.py           #   - SQLAlchemy-модели
│   ├── service.py          #   - бизнес-логика
│   ├── dependencies.py     #   - зависимости роутера
│   └── config.py           #   - локальные настройки
│
├── modules/, missions/, flows/, lessons/, tasks/
├── progress/, chat/, assistants/, roles/
│
├── agents/                 # AI-агенты
│   ├── evaluator/          #   - оценка заданий
│   └── tutor/              #   - помощь студентам
│
└── langflow/               # клиент для LangFlow API
```

### Команды
```bash
cd backend

# Зависимости (uv)
uv sync
uv sync --group dev        # с dev-зависимостями

# Запуск
uv run uvicorn src.main:app --reload --port 8000

# Миграции
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "описание"

# Линтер/форматтер
uv run ruff check .
uv run ruff format .

# Тесты
uv run pytest tests_integrational/
```

### Конвенции Backend
- **Python 3.13**, строгая типизация, `ruff` для линтинга
- **Async везде**: роутеры, сервисы, зависимости — всё `async def`
- **Pydantic v2**: схемы с валидацией, `model_validate()` для ORM-моделей
- **Импорты между доменами**: явные, `from src.auth import service as auth_service`
- **Кавычки**: одинарные `'строка'`
- **Длина строки**: 120 символов
- **Не блокируй event loop**: никогда `time.sleep()` в async-функциях

### Паттерн роутера
```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.modules import service
from src.modules.schemas import Module, ModuleCreate

router = APIRouter(prefix='/modules', tags=['Modules'])

@router.get('', response_model=list[Module])
async def get_modules(db: AsyncSession = Depends(get_db)) -> list[Module]:
    modules = await service.get_all_modules(db)
    return [Module.model_validate(m) for m in modules]

@router.post('', response_model=Module, status_code=status.HTTP_201_CREATED)
async def create_module(
    data: ModuleCreate,
    db: AsyncSession = Depends(get_db),
) -> Module:
    module = await service.create_module(db, data)
    return Module.model_validate(module)
```

---

## Frontend

### Структура
```
frontend/src/
├── main.tsx                # точка входа
├── app/
│   ├── App.tsx
│   ├── router.tsx          # react-router конфигурация
│   ├── providers.tsx       # QueryClient
│   └── ProtectedRoute.tsx
│
├── api/
│   ├── client.ts           # ApiClient класс
│   ├── endpoints.ts        # все API-вызовы
│   └── types.ts            # типы DTO
│
├── features/               # feature-slices
│   ├── auth/               #   store.ts (zustand), hooks.ts
│   ├── modules/
│   ├── progress/
│   └── chat/
│
├── pages/                  # страницы по роутам
│   ├── login/
│   ├── modules/
│   ├── progress/
│   ├── chat/
│   └── admin/
│
├── shared/
│   ├── ui/                 # UI-компоненты (button, card, input...)
│   ├── lib/                # утилиты
│   └── constants/
│
├── components/             # бизнес-компоненты
│   ├── TutorChat.tsx
│   ├── AttackSubmission.tsx
│   └── EvaluationResult.tsx
│
└── styles/
    └── globals.css         # Tailwind + кастомные стили
```

### Команды
```bash
cd frontend

npm install

npm run dev             # dev-сервер :5173
npm run build           # production build
npm run lint            # ESLint
npm run format          # Prettier
npm run test            # Vitest unit tests
npm run test:e2e        # Playwright e2e
```

### Конвенции Frontend
- **React 18** + TypeScript строгий
- **TanStack Query** для серверного состояния
- **Zustand** для клиентского состояния (auth store)
- **Tailwind CSS** + **Radix UI** для компонентов
- **Именование**: PascalCase для компонентов, camelCase для функций/переменных

### API-паттерн
```typescript
// api/endpoints.ts
export const modulesApi = {
  getAll: () => apiClient.get<Module[]>('/api/modules'),
  getById: (id: string) => apiClient.get<Module>(`/api/modules/${id}`),
  create: (data: CreateModuleRequest) => apiClient.post<Module>('/api/modules', data),
};

// features/modules/hooks.ts
export const useModules = () => {
  return useQuery({
    queryKey: ['modules'],
    queryFn: () => modulesApi.getAll(),
  });
};
```

### Zustand store
```typescript
// features/auth/store.ts
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    { name: LOCAL_STORAGE_KEYS.CURRENT_USER }
  )
);
```

---

## Docker

```bash
# Полный запуск
docker compose --env-file .env up -d --build

# Отдельные сервисы
docker compose up -d postgres minio
docker compose up -d backend
docker compose up -d frontend

# Логи
docker compose logs -f backend
docker compose logs -f langflow
```

**Переменные .env** (обязательные, уже есть в .env):
- `POSTGRES_ADMIN_USER`, `POSTGRES_ADMIN_PASSWORD`
- `BACKEND_DB_NAME`, `BACKEND_DB_USER`, `BACKEND_DB_PASSWORD`
- `LANGFLOW_DB_NAME`, `LANGFLOW_DB_USER`, `LANGFLOW_DB_PASSWORD`
- `LANGFLOW_SUPERUSER`, `LANGFLOW_SUPERUSER_PASSWORD`, `LANGFLOW_SECRET_KEY`
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`
- `OPENAI_API_KEY`

---

## AI-агенты

### EvaluatorAgent (оценка заданий)
Расположение: `backend/src/agents/evaluator/`

Типы заданий:
- `system_prompt_extraction` — извлечение системного промпта
- `knowledge_base_secret_extraction` — извлечение секретов из RAG
- `token_limit_bypass` — обход лимита токенов

Использует tool-calling для валидации решений студентов.

### TutorAgent (помощь студентам)
Расположение: `backend/src/agents/tutor/`

Определяет этап работы студента (initial/developing/reviewing) и адаптирует помощь.

---

## Критичные правила

### ЗАПРЕЩЕНО
- `time.sleep()` в async-функциях → используй `await asyncio.sleep()`
- Блокирующие вызовы в event loop
- Готовые решения в TutorAgent (только направляющие вопросы)
- Прямые SQL-запросы без SQLAlchemy

### ОБЯЗАТЕЛЬНО
- Все новые эндпоинты — `async def`
- Все миграции через Alembic
- Типизация параметров и возвратов
- `response_model` в роутерах FastAPI
- Проверять `ruff check .` и прохождение тестов `uv run pytest tests_integrational` перед коммитом
---

## Частые задачи

### Добавить новый домен (backend)
1. Создать папку `src/новый_домен/`
2. Добавить `models.py`, `schemas.py`, `service.py`, `router.py`
3. Импортировать router в `src/main.py`
4. Создать миграцию: `alembic revision --autogenerate -m "add новый_домен"`

### Добавить новую страницу (frontend)
1. Создать `pages/новая_страница/НоваяСтраницаPage.tsx`
2. Добавить роут в `app/router.tsx`
3. Если нужно состояние — создать hooks в `features/`

### Добавить API-эндпоинт (frontend)
1. Добавить типы в `api/types.ts`
2. Добавить вызов в `api/endpoints.ts`
3. Создать hook в соответствующем `features/*/hooks.ts`

