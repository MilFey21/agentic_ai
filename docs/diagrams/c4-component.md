# C4 Component — Внутреннее устройство ядра системы

Диаграмма раскрывает компоненты внутри **Tutor Agent** и **Evaluator Agent** — ядра мультиагентной системы. Именно здесь сосредоточена вся LLM-логика, SCH-иерархия, retrieval-контур и механизмы защиты.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}}}%%
C4Component
    title C4 Component: Ядро мультиагентной системы (Tutor Agent + Evaluator Agent)

    Container_Ext(redis, "Redis", "Брокер событий + KV state")
    Container_Ext(anthropic, "Anthropic Claude API", "Claude 3.5 Sonnet")
    Container_Ext(theory_retriever, "TheoryRetriever", "Keyword-search по MD-индексу")
    Container_Ext(prog_validator, "Programmatic Validator", "Детерминированная проверка атаки")
    Container_Ext(postgres, "PostgreSQL", "Хранилище оценок")

    Container_Boundary(tutor_boundary, "Tutor Agent") {

        Component(event_consumer, "StreamConsumer", "FastStream consumer", "Consume student.message, validation.result; маршрутизация событий внутрь агента")

        Component(session_manager, "SessionManager", "Python / Redis client", "R/W TutorSessionState в Redis KV (TTL 24ч); идемпотентность при повторной доставке")

        Component(stage_classifier, "StageClassifier", "Claude 3.5 Sonnet T=0.1", "ORIENTATION→SOLVED по последним 5 репликам; T=0.1 для детерминизма")

        Component(sch_prompt_builder, "SCHPromptBuilder", "Python", "SCH-промпт: P1 запреты → P2 педагогика → P3 исключения; вставляет theory_context")

        Component(llm_caller_tutor, "LLMCaller", "Anthropic SDK", "Claude 3.5 Sonnet T=0.7, max_tokens=512; промпт + история диалога")

        Component(post_processor, "PostProcessor", "Python", "Guardrails: '?' в ответе, SCH P1, длина ≤ 512. Retry ×3 → neutral fallback")

        Component(circuit_breaker, "CircuitBreaker", "Python", "3 ошибки / 60 с → аварийный режим; статичный ответ; авто-восстановление")

        Component(scr_tracker, "SCRTracker", "Python / OTel", "SCR = доля ответов с '?' за скользящий час; алерт при SCR < 85%")

        Component(event_publisher_tutor, "StreamPublisher", "FastStream publisher", "Публикует tutor.response в Redis Streams")
    }

    Container_Boundary(evaluator_boundary, "Evaluator Agent") {

        Component(eval_consumer, "StreamConsumer", "FastStream consumer", "Consume task.submitted; задержка 30 с для записи всех попыток")

        Component(rubric_loader, "RubricLoader", "Python", "GET task:{task_id}:rubric из Redis; 5-компонентная схема оценивания")

        Component(llm_analyzer, "LLMAnalyzer", "Claude 3.5 Sonnet T=0.3", "Анализ: solution + attempts + rubric → JSON с оценками per критерий")

        Component(pydantic_validator, "PydanticValidator", "Pydantic v2", "Валидация EvaluationResult; retry ×2; partial result + алерт при исчерпании")

        Component(eval_publisher, "StreamPublisher", "FastStream publisher", "Публикует evaluation.result в Redis Streams; INSERT в PostgreSQL")
    }

    Rel(event_consumer, redis, "XREADGROUP student.message / validation.result", "Redis Streams")
    Rel(event_consumer, session_manager, "Загрузить / обновить состояние сессии")
    Rel(event_consumer, stage_classifier, "Передать последние 5 реплик для классификации")
    Rel(event_consumer, sch_prompt_builder, "Запустить сборку промпта")

    Rel(session_manager, redis, "GET/SET tutor:session:{id}:history", "Redis KV")
    Rel(stage_classifier, anthropic, "classify(history) → stage", "HTTPS")
    Rel(sch_prompt_builder, theory_retriever, "search(query) → theory_context", "In-process")
    Rel(sch_prompt_builder, llm_caller_tutor, "Передать собранный промпт")

    Rel(llm_caller_tutor, anthropic, "messages.create(T=0.7, max_tokens=512)", "HTTPS")
    Rel(llm_caller_tutor, circuit_breaker, "Зарегистрировать успех / ошибку")
    Rel(llm_caller_tutor, post_processor, "Передать ответ на постпроцессинг")

    Rel(post_processor, llm_caller_tutor, "Retry при нарушении SCH (до 3 попыток)")
    Rel(post_processor, scr_tracker, "Зафиксировать наличие '?' в ответе")
    Rel(post_processor, event_publisher_tutor, "Передать финальный ответ")

    Rel(event_publisher_tutor, redis, "XADD tutor.response", "Redis Streams")

    Rel(eval_consumer, redis, "XREADGROUP task.submitted", "Redis Streams")
    Rel(eval_consumer, rubric_loader, "Загрузить рубрику")
    Rel(rubric_loader, redis, "GET task:{task_id}:rubric", "Redis KV")
    Rel(eval_consumer, llm_analyzer, "Передать solution + attempts + rubric")
    Rel(llm_analyzer, anthropic, "messages.create(T=0.3) → JSON", "HTTPS")
    Rel(llm_analyzer, pydantic_validator, "Передать JSON для валидации")
    Rel(pydantic_validator, llm_analyzer, "Retry с напоминанием схемы (до 2)")
    Rel(pydantic_validator, eval_publisher, "Передать валидный EvaluationResult")
    Rel(eval_publisher, redis, "XADD evaluation.result", "Redis Streams")
    Rel(eval_publisher, postgres, "INSERT evaluation", "SQL")

    Rel(prog_validator, redis, "XREADGROUP task.attempt; XADD validation.result", "Redis Streams")
```

## Ключевые компоненты и их роли

### Tutor Agent

| Компонент | Роль |
|---|---|
| **StreamConsumer** | Точка входа; маршрутизирует события; обеспечивает idempotency через проверку уже обработанных event ID |
| **SessionManager** | Единственный компонент, работающий с Redis KV; хранит всё сессионное состояние |
| **StageClassifier** | LLM-вызов с T=0.1; диагностирует педагогический этап студента для адаптации промпта |
| **SCHPromptBuilder** | Сборщик системного промпта; жёсткая иерархия P1 > P2 > P3 не может быть изменена на ходу |
| **LLMCaller** | Изолированный компонент; единственный, кто вызывает Anthropic API в рамках тьютора |
| **PostProcessor** | Детерминированные guardrails: проверка SCH, вопросительный знак, длина; retry / fallback |
| **CircuitBreaker** | Защита от каскадного сбоя при недоступности Anthropic API |
| **SCRTracker** | Метрика качества тьютора: SCR < 85% → алерт в Grafana |

### Evaluator Agent

| Компонент | Роль |
|---|---|
| **StreamConsumer** | Задержка 30 с после получения task.submitted для завершения записи всех попыток |
| **RubricLoader** | Загружает 5-компонентную рубрику из Redis; изолирован от истории тьютора |
| **LLMAnalyzer** | Анализирует технику атаки; структурированный JSON-вывод |
| **PydanticValidator** | Детерминированный контракт вывода; retry при невалидном JSON; partial result при исчерпании |
| **StreamPublisher** | Гарантирует запись в PostgreSQL перед ACK события в Redis Streams |
