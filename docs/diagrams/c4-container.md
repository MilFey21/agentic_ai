# C4 Container — Frontend, Backend, Orchestrator, Retriever, Tool Layer, Storage, Observability

Диаграмма раскрывает внутреннее устройство мультиагентной системы: контейнеры, их технологии и способы взаимодействия.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}}}%%
C4Container
    title C4 Container: Мультиагентная система поддержки обучения Windchaser

    Person(student, "Студент", "Задания, диалог с тьютором")
    Person(instructor, "Преподаватель / Админ", "Мониторинг, управление контентом")

    System_Ext(anthropic, "Anthropic Claude API", "Claude 3.5 Sonnet — LLM-провайдер")
    System_Ext(prometheus, "Prometheus + Grafana", "Внешний мониторинг и алерты")

    System_Boundary(windchaser_sys, "Windchaser Platform") {

        Container(windchaser_fe, "Windchaser Frontend", "React / TypeScript", "Интерфейс курса: задания, чат с тьютором, оценки")
        Container(windchaser_be, "Windchaser Backend / LMS", "Python / FastAPI", "Курсы, прогресс, аутентификация, WebSocket-стриминг")
        Container(agent_bridge, "AgentBridgeService", "Python / FastStream", "Трансляция событий платформы ↔ Redis Streams; жизненный цикл сессий")

        System_Boundary(agent_core, "Мультиагентное ядро") {
            Container(rest_api, "FastAPI REST API", "Python / FastAPI", "CRUD сессий, статус, результаты оценивания, переиндексация")
            Container(tutor_agent, "Tutor Agent", "Python / Anthropic SDK", "Сократический тьютор: SCH-промпт, диагностика этапа, направляющие вопросы")
            Container(evaluator_agent, "Evaluator Agent", "Python / Anthropic SDK", "LLMAnalyzer + Pydantic-валидация; оценка по рубрике")
            Container(prog_validator, "Programmatic Validator", "Python", "Детерминированная проверка атаки: regex / string match / judge model")
            Container(theory_retriever, "TheoryRetriever", "Python", "Keyword-search по MD-индексу → theory_context для тьютора")
        }

        ContainerDb(redis, "Redis", "Redis Streams + Redis KV", "Брокер событий (Streams) + state-хранилище сессий (KV, TTL 24ч)")
        ContainerDb(postgres, "PostgreSQL", "PostgreSQL", "Пользователи, результаты оценивания, аналитика прогресса")
        ContainerDb(markdown_store, "Markdown Knowledge Base", "Файловая система", "~14 MD-файлов теории LLM Security; индексируется TheoryRetriever")

        Container(otel_collector, "OpenTelemetry Collector", "OTEL", "Трейсы LLM-вызовов, метрики SCR, latency, стоимость токенов")
    }

    Rel(student, windchaser_fe, "Чат, задания, оценки", "HTTPS / WebSocket")
    Rel(instructor, windchaser_fe, "Аналитика, управление курсом", "HTTPS")
    Rel(instructor, rest_api, "Переиндексация, статус агентов", "REST")

    Rel(windchaser_fe, windchaser_be, "API-запросы, WebSocket", "HTTPS / WS")
    Rel(windchaser_be, agent_bridge, "События студентов → ответы агентов", "Internal")
    Rel(agent_bridge, redis, "Publish / Consume Redis Streams", "Redis protocol")
    Rel(agent_bridge, rest_api, "Создание / завершение сессий", "REST")

    Rel(tutor_agent, redis, "Consume student.message; Publish tutor.response; R/W state", "Redis protocol")
    Rel(tutor_agent, theory_retriever, "search(query) → theory_context", "In-process")
    Rel(tutor_agent, anthropic, "Генерация / классификация (SCH + history)", "HTTPS")

    Rel(evaluator_agent, redis, "Consume task.submitted; Publish evaluation.result", "Redis protocol")
    Rel(evaluator_agent, anthropic, "LLMAnalyzer: анализ техники атаки", "HTTPS")
    Rel(evaluator_agent, postgres, "Сохранение результатов оценивания", "SQL")

    Rel(prog_validator, redis, "Consume task.attempt; Publish validation.result", "Redis protocol")

    Rel(theory_retriever, markdown_store, "Чтение и индексация MD-файлов", "FS read")

    Rel(rest_api, redis, "R/W session state", "Redis protocol")
    Rel(rest_api, postgres, "Чтение результатов оценивания", "SQL")

    Rel(windchaser_be, postgres, "Пользователи, прогресс, курсы", "SQL")

    Rel(tutor_agent, otel_collector, "Трейсы LLM-вызовов, метрики SCR", "OTEL")
    Rel(evaluator_agent, otel_collector, "Трейсы LLM-вызовов, latency", "OTEL")
    Rel(otel_collector, prometheus, "Экспорт метрик и трейсов", "Prometheus / OTLP")
```

## Пояснения к контейнерам

| Контейнер | Технология | Роль |
|---|---|---|
| **Windchaser Frontend** | React / TypeScript | UI: чат с тьютором, задания, просмотр результатов через WebSocket |
| **Windchaser Backend** | FastAPI | LMS-логика, аутентификация, WebSocket-стриминг ответов агентов студенту |
| **AgentBridgeService** | FastStream | Развязка платформы и агентного ядра через Redis Streams |
| **FastAPI REST API** | FastAPI | Синхронный управляющий слой: CRUD сессий, статус, оценки |
| **Tutor Agent** | Anthropic SDK | Сократический тьютор; SCH-иерархия, анализ этапа, постпроцессинг |
| **Evaluator Agent** | Anthropic SDK | Оценщик; LLMAnalyzer + Pydantic-валидация JSON |
| **Programmatic Validator** | Pure Python | Детерминированный валидатор факта атаки (без LLM) |
| **TheoryRetriever** | Pure Python | Keyword-search по Markdown-индексу; deterministic |
| **Redis** | Redis Streams + KV | Брокер + сессионное state-хранилище |
| **PostgreSQL** | PostgreSQL | Долгосрочное хранилище оценок, прогресса, пользователей |
| **Markdown KB** | FS | Источник теории для индексации TheoryRetriever |
| **OTel Collector** | OpenTelemetry | Агрегация трейсов и метрик перед отправкой в Grafana |
