# Workflow / Graph Diagram — Пошаговое выполнение запроса

Диаграммы покрывают три основных сценария: диалог с тьютором, попытку атаки и финальную сдачу задания — включая все ветки ошибок и fallback-пути.

---

## 1. Диалог студента с тьютором

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart TD
    classDef error  fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    classDef warn   fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef api    fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F
    classDef ok     fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef pub    fill:#F3E8FF,stroke:#9333EA,color:#3B0764
    classDef term   fill:#F1F5F9,stroke:#64748B,color:#0F172A

    A([Студент отправляет сообщение]):::term
    A --> B[Windchaser:\nstudent.message → Redis Streams]
    B --> C{Idempotency check:\nсобытие обработано?}
    C -- Да --> Z1([ACK — пропустить]):::term
    C -- Нет --> D[SessionManager:\nзагрузить TutorSessionState]:::api

    D --> E{Сессия найдена?}
    E -- Нет --> F[Создать сессию:\nstage=ORIENTATION\nhint_depth=shallow]:::ok
    E -- Да  --> G[Восстановить: history,\nstage, hint_depth, attempts]:::ok
    F --> H
    G --> H

    H[StageClassifier:\nclassify 5 реплик, T=0.1]:::api
    H --> H1{Anthropic API\nдоступен?}
    H1 -- Нет --> H2[CircuitBreaker:\ninc error count]:::error
    H2 --> H3{3 ошибки\nза 60 с?}
    H3 -- Да  --> H4[Аварийный режим:\nстатичный ответ]:::error
    H3 -- Нет --> H5[Retry classify\nс backoff]:::warn
    H5 --> H1
    H4 --> PUB

    H1 -- Да --> I[Stage определён:\nORIENTATION / EXPLORATION\nTESTING / REFINEMENT / SOLVED]:::ok

    I --> J[TheoryRetriever.search:\nquery из последнего сообщения]:::api
    J --> K{score > 0?}
    K -- Нет --> L[Fallback:\nкорневой узел темы задания]:::warn
    K -- Да  --> M[theory_context =\nbest matching section]:::ok
    L --> N
    M --> N

    N[SCHPromptBuilder:\nP1: запреты, P2: педагогика\nP3: исключения + контекст]
    N --> O[LLMCaller: messages.create\nT=0.7, max_tokens=512]:::api
    O --> O1{Anthropic API\nдоступен?}
    O1 -- Нет --> H2
    O1 -- Да  --> P[Получен ответ LLM]:::ok

    P --> Q{PostProcessor P1:\nзапрещённые термины?}
    Q -- Найдено --> R{Retry ≤ 3?}
    R -- Да  --> S[Retry LLMCaller\nс усиленным P1-блоком]:::warn
    S --> P
    R -- Нет --> T[Neutral fallback:\n'Давайте подумаем вместе'\nЛог: guardrail_triggered]:::error
    T --> PUB

    Q -- Чисто --> U{Есть '?'\nв ответе?}
    U -- Нет --> V[Добавить уточняющий вопрос\nЛог: missing_question]:::warn
    U -- Да  --> W[Ответ валиден]:::ok
    V --> W

    W --> X{Длина\n≤ 512 токенов?}
    X -- Нет --> Y[Усечение:\nсохранить финальный вопрос]:::warn
    X -- Да  --> PUB
    Y --> PUB

    PUB[StreamPublisher:\nXADD tutor.response]:::pub
    PUB --> PUB2[SessionManager:\nсохранить state в Redis]:::api
    PUB2 --> SCR[SCRTracker:\nзафиксировать '?' → SCR]
    SCR --> SCR2{SCR < 85%\nза последний час?}
    SCR2 -- Да  --> SCR3[Алерт в Grafana]:::error
    SCR2 -- Нет --> END
    SCR3 --> END
    END([tutor.response → WebSocket → студент]):::term
```

---

## 2. Попытка атаки (промпт студента)

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart TD
    classDef error fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    classDef warn  fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef api   fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F
    classDef ok    fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef pub   fill:#F3E8FF,stroke:#9333EA,color:#3B0764
    classDef term  fill:#F1F5F9,stroke:#64748B,color:#0F172A

    A([Студент отправляет промпт-атаку]):::term
    A --> B[Windchaser:\ntask.attempt → Redis Streams]
    B --> C{Idempotency check}
    C -- Уже обработано --> Z1([ACK — пропустить]):::term
    C -- Новое --> D[Programmatic Validator\nполучает событие]:::api

    D --> E{Тип проверки}
    E -- regex / string match --> F[Детерминированная проверка\nбез LLM-вызова]:::ok
    E -- judge model          --> G[Изолированная judge-модель\nT=0.0, без истории сессии]:::api

    F --> H{Атака успешна?}
    G --> H
    H -- Да  --> I[validation.result: success=true]:::ok
    H -- Нет --> J[validation.result: success=false]:::error

    I --> K[XADD validation.result\n→ Redis Streams]:::pub
    J --> K

    K --> K1[Windchaser:\nмгновенная обратная связь]:::ok
    K --> K2[Tutor Agent:\nобновить failed_attempts]:::api

    K2 --> K3{failed_attempts ≥\nпорог адаптации?}
    K3 -- Да  --> K4[hint_depth = deep\nstage → REFINEMENT]:::warn
    K3 -- Нет --> END
    K4 --> END([Обновлённый state сохранён]):::term
```

---

## 3. Финальная сдача задания

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart TD
    classDef error fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    classDef warn  fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef api   fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F
    classDef ok    fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef pub   fill:#F3E8FF,stroke:#9333EA,color:#3B0764
    classDef term  fill:#F1F5F9,stroke:#64748B,color:#0F172A

    A([Студент нажимает 'Сдать задание']):::term
    A --> B[Windchaser:\ntask.submitted → Redis Streams]
    B --> C{Idempotency check}
    C -- Уже обработано --> Z1([Вернуть сохранённый результат]):::term
    C -- Новое --> D[Evaluator Agent\nполучает событие]:::api

    D --> E[Задержка 30 с:\nожидание записи всех попыток]:::warn

    E --> F[RubricLoader:\nзагрузить rubric из Redis]:::api
    F --> F1{Рубрика найдена?}
    F1 -- Нет --> F2[Алерт: missing rubric\nevaluation_status = error]:::error
    F2 --> PUB
    F1 -- Да  --> G[Собрать payload:\nfinal_solution + attempt_log + rubric]:::ok

    G --> H[LLMAnalyzer: messages.create\nT=0.3, структурированный JSON]:::api
    H --> H1{Anthropic API\nдоступен?}
    H1 -- Нет --> H2[Retry с backoff\nдо 3 попыток]:::warn
    H2 --> H3{Попытки\nисчерпаны?}
    H3 -- Нет --> H
    H3 -- Да  --> H4[evaluation_status = error\nОтложенная оценка + алерт]:::error
    H4 --> PUB
    H1 -- Да  --> I[Получен JSON-ответ от LLM]:::ok

    I --> J[PydanticValidator:\nпроверить по схеме EvaluationResult]:::api
    J --> J1{JSON валиден?}
    J1 -- Да  --> K[EvaluationResult:\nоценки по 5 критериям рубрики]:::ok
    J1 -- Нет --> J2{Retry ≤ 2?}
    J2 -- Да  --> J3[Retry LLMAnalyzer\nс напоминанием схемы]:::warn
    J3 --> I
    J2 -- Нет --> J4[Partial result:\nevaluation_status = partial]:::error
    J4 --> J5[Алерт: pydantic_validation_failed]:::error
    J5 --> PUB

    K --> L{Programmatic Validator\nподтвердил success?}
    L -- Нет --> M[overall_status = failed]:::error
    L -- Да  --> N[overall_status = passed]:::ok
    M --> PUB
    N --> PUB

    PUB[StreamPublisher:\nXADD evaluation.result\n+ INSERT в PostgreSQL]:::pub
    PUB --> END([evaluation.result → интерфейс курса → студент]):::term
```

---

## 4. UML Sequence — Диалог студента с тьютором

Диаграмма показывает точную последовательность и направление вызовов между компонентами: кто кого ждёт, где есть ветки retry, и как ответ доходит до студента через WebSocket.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"actorBkg": "#EFF6FF", "actorBorder": "#3B82F6", "actorTextColor": "#1E3A5F", "signalColor": "#64748B", "signalTextColor": "#1E3A5F", "noteBkgColor": "#FFFBEB", "noteTextColor": "#713F12", "labelBoxBkgColor": "#F3E8FF", "labelTextColor": "#3B0764", "loopTextColor": "#3B0764", "activationBorderColor": "#3B82F6", "activationBkgColor": "#DBEAFE"}}}%%
sequenceDiagram
    autonumber
    participant S as Студент
    participant W as Windchaser
    participant R as Redis Streams
    participant TA as Tutor Agent
    participant AN as Anthropic API
    participant TR as TheoryRetriever
    participant PP as PostProcessor

    S->>W: отправить сообщение
    W->>R: XADD student.message {event_id, session_id, text}
    R-->>TA: deliver event (consumer group)

    TA->>TA: idempotency check (event_id)

    TA->>R: GET tutor:session:{id}:history
    R-->>TA: TutorSessionState (history, stage, hint_depth, failed_attempts)

    Note over TA,AN: StageClassifier, классификация этапа, T=0.1
    TA->>AN: messages.create classify(last 5 turns)
    AN-->>TA: stage, hint_depth

    TA->>TR: search(last_message_text)
    alt score > 0
        TR-->>TA: best matching section (theory_context)
    else score = 0
        TR-->>TA: root node темы задания (retrieval fallback)
    end

    Note over TA: SCHPromptBuilder with theory_context
    loop retry <= 3
        TA->>AN: messages.create (T=0.7, max_tokens=512)
        AN-->>TA: raw response
        TA->>PP: check(response)
        alt запрещённый термин найден
            PP-->>TA: VIOLATION
        else ответ чистый
            PP-->>TA: OK
        end
    end

    alt все 3 попытки нарушают P1
        TA->>R: XADD tutor.response {neutral fallback}
        Note over TA: guardrail_triggered
    else ответ прошёл P1
        opt нет вопроса в ответе
            Note over PP: add follow-up question
        end
        opt длина > 512 токенов
            Note over PP: trim response and keep final question
        end
        TA->>R: SET tutor:session:{id}:history TTL 24h
        TA->>R: XADD tutor.response {session_id, text}
        TA->>TA: SCR tracking and Grafana alert
    end

    TA->>R: XACK student.message
    R-->>W: deliver tutor.response
    W-->>S: WebSocket push
```

---

## 5. UML Sequence — Попытка атаки (промпт студента)

Ключевые особенности: Programmatic Validator работает без LLM (или с изолированной judge-моделью); доставка результата — параллельная: студент и Tutor Agent получают событие одновременно.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"actorBkg": "#EFF6FF", "actorBorder": "#3B82F6", "actorTextColor": "#1E3A5F", "signalColor": "#64748B", "signalTextColor": "#1E3A5F", "noteBkgColor": "#FFFBEB", "noteTextColor": "#713F12", "labelBoxBkgColor": "#F3E8FF", "labelTextColor": "#3B0764", "loopTextColor": "#3B0764", "activationBorderColor": "#3B82F6", "activationBkgColor": "#DBEAFE"}}}%%
sequenceDiagram
    autonumber
    participant S  as Студент
    participant W  as Windchaser
    participant R  as Redis Streams
    participant PV as Programmatic Validator
    participant JM as Judge Model
    participant TA as Tutor Agent

    S->>W: отправить промпт-атаку
    W->>R: XADD task.attempt {event_id, session_id, task_id, payload}
    R-->>PV: deliver event (consumer group)

    PV->>PV: idempotency check (event_id)

    alt тип проверки: regex / string match
        Note over PV: детерминированная проверка без LLM-вызова
        PV->>PV: regex / exact match → {success: bool}
    else тип проверки: judge model
        PV->>JM: classify(payload, T=0.0)
        Note over JM: изолированная модель, без истории сессии
        JM-->>PV: {success: bool}
    end

    PV->>R: XADD validation.result {event_id, session_id, success}
    PV->>R: XACK task.attempt

    par мгновенная обратная связь студенту
        R-->>W: deliver validation.result
        W-->>S: результат попытки (успех / неудача)
    and обновление состояния Tutor Agent
        R-->>TA: deliver validation.result
        TA->>R: GET tutor:session:{id}:history
        R-->>TA: current state (failed_attempts)
        alt failed_attempts ≥ порог адаптации
            TA->>R: SET hint_depth=deep, stage=REFINEMENT
        end
        TA->>R: XACK validation.result
    end
```

---

## 6. UML Sequence — Финальная сдача задания

Evaluator Agent полностью изолирован от истории тьютора. Входные данные — только `dialog_log` из payload события и рубрика из Redis.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"actorBkg": "#EFF6FF", "actorBorder": "#3B82F6", "actorTextColor": "#1E3A5F", "signalColor": "#64748B", "signalTextColor": "#1E3A5F", "noteBkgColor": "#FFFBEB", "noteTextColor": "#713F12", "labelBoxBkgColor": "#F3E8FF", "labelTextColor": "#3B0764", "loopTextColor": "#3B0764", "activationBorderColor": "#3B82F6", "activationBkgColor": "#DBEAFE"}}}%%
sequenceDiagram
    autonumber
    participant S  as Студент
    participant W  as Windchaser
    participant R  as Redis Streams
    participant EA as Evaluator Agent
    participant AN as Anthropic API
    participant PD as Pydantic Validator
    participant PG as PostgreSQL

    S->>W: нажать "Сдать задание"
    W->>R: XADD task.submitted {event_id, session_id, task_id, dialog_log, final_solution}
    R-->>EA: deliver event (consumer group)

    EA->>EA: idempotency check (event_id)

    Note over EA: задержка 30 с — ожидание записи всех попыток в Redis

    EA->>R: GET task:{task_id}:rubric
    alt рубрика не найдена
        R-->>EA: nil
        EA->>R: XADD evaluation.result {status: error}
        Note over EA: алерт: missing_rubric
    else рубрика загружена
        R-->>EA: rubric JSON

        loop retry ≤ 2 (Pydantic enforcement)
            EA->>AN: messages.create (final_solution + attempt_log + rubric, T=0.3)
            AN-->>EA: JSON response
            EA->>PD: validate(response, EvaluationResult schema)
            alt JSON валиден
                PD-->>EA: EvaluationResult (оценки по 5 критериям)
            else JSON невалиден
                PD-->>EA: ValidationError → retry с напоминанием схемы
            end
        end

        alt все retry исчерпаны
            EA->>R: XADD evaluation.result {status: partial}
            Note over EA: алерт: pydantic_validation_failed
        else оценка получена
            Note over EA: проверка флага от Programmatic Validator (из Redis)
            alt Programmatic Validator: success = true
                Note over EA: overall_status = passed
            else Programmatic Validator: success = false
                Note over EA: overall_status = failed
            end

            EA->>PG: INSERT evaluation_records (session_id, status, scores, feedback)
            PG-->>EA: OK
            EA->>R: XADD evaluation.result {status, scores, feedback}
        end
    end

    EA->>R: XACK task.submitted
    R-->>W: deliver evaluation.result
    W-->>S: отобразить результат оценивания
```

---

## Сводная таблица failure modes и fallback-путей

| Scenario | Trigger | Fallback | Логирование |
|---|---|---|---|
| Anthropic API недоступен (тьютор) | 3 ошибки за 60 с | Статичный ответ студенту; очередь не теряется | circuit_breaker_open |
| SCH P1 нарушен в ответе тьютора | Запрещённый термин в PostProcessor | Retry ×3 → neutral fallback | guardrail_triggered |
| Нет '?' в ответе тьютора | PostProcessor | Добавить обобщённый вопрос | missing_question |
| theory_context не найден | score = 0 в TheoryRetriever | Корневой узел темы задания | retrieval_fallback |
| Pydantic-валидация провалилась (оценщик) | Невалидный JSON от LLM | Retry ×2 → partial result + алерт | pydantic_validation_failed |
| Рубрика не найдена | missing key в Redis | evaluation_status = error + алерт | missing_rubric |
| SCR < 85% за час | SCRTracker | Алерт в Grafana | scr_degradation |
| Повторная доставка события | Redis Streams re-delivery | Idempotency check → пропуск | duplicate_event_skipped |
