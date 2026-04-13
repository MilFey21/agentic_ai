# WindChaser Security - Frontend

Тренажёр по информационной безопасности с AI-ассистентами.

## Технологический стек

- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **Routing**: React Router v6
- **State Management**: Zustand + TanStack Query
- **UI**: shadcn/ui + Tailwind CSS
- **Forms**: React Hook Form + Zod
- **Testing**: Vitest + React Testing Library + Playwright
- **API Mocking**: MSW (Mock Service Worker)

## Быстрый старт

```bash
# Установка зависимостей
npm install

# Запуск в режиме разработки (с моками)
npm run dev

# Сборка для продакшена
npm run build

# Запуск тестов
npm run test

# Запуск e2e тестов
npm run test:e2e
```

## Структура проекта

```
src/
├── api/              # API клиент, типы, эндпоинты
├── app/              # App компонент, роутинг, провайдеры
├── features/         # Бизнес-логика (хуки, сторы)
│   ├── auth/         # Авторизация
│   ├── chat/         # Чат с ассистентом
│   ├── modules/      # Модули и задания
│   └── progress/     # Прогресс пользователя
├── mocks/            # MSW хендлеры и мок-данные
│   ├── data/         # Seed данные
│   └── handlers.ts   # API хендлеры
├── pages/            # Страницы приложения
│   ├── admin/        # Админ-панель
│   ├── chat/         # Чат
│   ├── login/        # Авторизация
│   ├── modules/      # Модули
│   └── progress/     # Прогресс
├── shared/           # Переиспользуемые компоненты
│   ├── constants/    # Константы
│   ├── lib/          # Утилиты
│   └── ui/           # UI компоненты
├── styles/           # Глобальные стили
└── test/             # Тестовые утилиты
```

## Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```env
VITE_API_MODE=mock      # mock | real
VITE_API_BASE_URL=http://localhost:8000
```

## Роли пользователей

- **Admin** — управление контентом, просмотр прогресса всех пользователей
- **Student** — прохождение модулей, выполнение заданий, чат с ассистентом

## Основные сценарии

### Студент:
1. Вход в систему (выбор пользователя из списка)
2. Просмотр каталога модулей
3. Открытие модуля и изучение материалов
4. Выполнение заданий в плеере
5. Отслеживание прогресса
6. Чат с AI-ассистентом

### Админ:
1. Управление модулями (CRUD)
2. Управление заданиями (CRUD)
3. Управление ассистентами (CRUD)

## API контракт

API работает в mock-режиме через MSW. Эндпоинты:

### Auth
- `GET /api/me` — текущий пользователь
- `POST /api/login` — вход
- `GET /api/users` — список пользователей

### Modules
- `GET /api/modules` — список модулей
- `GET /api/modules/:id` — модуль по ID
- `POST /api/modules` — создать модуль
- `PATCH /api/modules/:id` — обновить модуль
- `DELETE /api/modules/:id` — удалить модуль

### Tasks
- `GET /api/tasks` — список заданий
- `GET /api/tasks?module_id=` — задания модуля
- `POST /api/tasks` — создать задание
- `PATCH /api/tasks/:id` — обновить задание
- `DELETE /api/tasks/:id` — удалить задание

### Progress
- `GET /api/user_task_progress?user_id=` — прогресс пользователя
- `POST /api/user_task_progress` — создать прогресс
- `PATCH /api/user_task_progress/:id` — обновить прогресс

### Chat
- `GET /api/chat_sessions?user_id=&module_id=` — сессии чата
- `POST /api/chat_sessions` — создать/получить сессию
- `PATCH /api/chat_sessions/:id` — завершить сессию
- `GET /api/messages?chat_session_id=` — сообщения
- `POST /api/messages` — отправить сообщение

## Тестирование

```bash
# Unit тесты
npm run test

# С UI
npm run test:ui

# Coverage
npm run test:coverage

# E2E тесты
npm run test:e2e

# E2E с UI
npm run test:e2e:ui
```

## Docker

```bash
# Сборка
docker build -t windchaser-frontend .

# Запуск
docker run -p 80:80 windchaser-frontend
```

## Лицензия

MIT

