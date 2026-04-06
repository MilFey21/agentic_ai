# Data Flow Diagram — Движение данных, хранение и логирование

Диаграммы показывают, как данные проходят через систему на каждом из трёх основных сценариев: что именно хранится, где и как долго; что попадает в логи и мониторинг.

---

## 1. Data flow: диалог с тьютором

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart LR
    classDef kv     fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef stream fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef kb     fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef otel   fill:#FFF7ED,stroke:#EA580C,color:#7C2D12
    classDef term   fill:#F1F5F9,stroke:#64748B,color:#0F172A
    classDef svc    fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F

    STU([Студент]):::term
    STU -->|Текст сообщения| WFE[Windchaser Frontend]:::svc
    WFE -->|POST /chat, HTTPS| WBE[Windchaser Backend]:::svc
    WBE -->|Publish student.message\nsession_id, task_id, message| RS[(Redis Streams\nstudent.message)]:::stream

    RS -->|XREADGROUP| TA[Tutor Agent]:::svc

    TA -->|GET session history| RKV[(Redis KV\nSession State)]:::kv
    RKV -->|history, stage,\nhint_depth, attempts| TA

    TA -->|query string| TR[TheoryRetriever]:::svc
    TR -->|Читает при старте| MKB[(Markdown KB\n~14 файлов)]:::kb
    TR -->|theory_context ≤ 500 символов| TA

    TA -->|SCH-промпт + history\n+ theory_context, ~5000 токенов| AAPI[Anthropic\nClaude API]:::svc
    AAPI -->|Ответ ≤ 512 токенов| TA

    TA -->|SET session history, TTL 24ч| RKV
    TA -->|Publish tutor.response\nsession_id, text, stage, hint_depth| RS2[(Redis Streams\ntutor.response)]:::stream

    TA -->|Трейс: tokens, latency,\nstage, scr_flag| OTL[OTel Collector]:::otel
    OTL -->|Метрики| PROM[Prometheus\n+ Grafana]:::otel

    RS2 -->|XREADGROUP| ABS[AgentBridgeService]:::svc
    ABS -->|WebSocket push| WBE
    WBE -->|WebSocket| WFE
    WFE -->|Рендер ответа| STU
```

### Что хранится при диалоге

| Хранилище | Ключ / таблица | Данные | TTL / Retention |
|---|---|---|---|
| Redis KV | `tutor:session:{id}:history` | history (role, content, ts), stage, hint_depth, failed_attempts, stage_transitions | 24 ч |
| Redis Streams | `student.message` | session_id, task_id, message, timestamp | до ACK + 7 дней |
| Redis Streams | `tutor.response` | session_id, text, stage, hint_depth, scr_flag | до ACK + 7 дней |
| OTel / Prometheus | метрики | input_tokens, output_tokens, latency_ms, stage, scr_value, guardrail_triggered | 30 дней |

---

## 2. Data flow: попытка атаки

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart LR
    classDef kv     fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef stream fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef judge  fill:#FDF4FF,stroke:#A21CAF,color:#4A044E
    classDef term   fill:#F1F5F9,stroke:#64748B,color:#0F172A
    classDef svc    fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F

    STU([Студент]):::term
    STU -->|Промпт атаки| WFE[Windchaser Frontend]:::svc
    WFE -->|POST /attempt| WBE[Windchaser Backend]:::svc
    WBE -->|Publish task.attempt\nsession_id, task_id,\nattack_prompt, attempt_num| RS[(Redis Streams\ntask.attempt)]:::stream

    RS -->|XREADGROUP| PV[Programmatic\nValidator]:::svc

    PV -->|Детерминированная проверка\nregex / string match| PV
    PV -.->|Judge model: attack_prompt| JM[Изолированная\njudge-модель T=0.0]:::judge
    JM -.->|success: bool| PV

    PV -->|Publish validation.result\nsession_id, task_id,\nsuccess, matched_pattern| RS2[(Redis Streams\nvalidation.result)]:::stream

    RS2 -->|XREADGROUP| ABS[AgentBridgeService]:::svc
    ABS -->|Мгновенная обратная связь| WBE
    WBE -->|WebSocket| WFE
    WFE -->|Результат попытки| STU

    RS2 -->|XREADGROUP| TA[Tutor Agent]:::svc
    TA -->|INCR failed_attempts\nSET session history| RKV[(Redis KV)]:::kv

    PV -->|attempt_log:\nattempt_num, success, pattern| RKV2[(Redis KV\nattempt_log)]:::kv
```

### Что хранится при попытке атаки

| Хранилище | Ключ / таблица | Данные | TTL / Retention |
|---|---|---|---|
| Redis Streams | `task.attempt` | session_id, task_id, attack_prompt, attempt_num | до ACK + 7 дней |
| Redis Streams | `validation.result` | session_id, task_id, attempt_num, success, matched_pattern | до ACK + 7 дней |
| Redis KV | `attempt_log:{task_id}:{student_id}` | список попыток: attempt_num, success, pattern, latency_ms | 24 ч |
| Redis KV | `tutor:session:{id}:history` | обновлённый failed_attempts | 24 ч |

---

## 3. Data flow: финальная сдача задания

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart LR
    classDef kv     fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef stream fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef pg     fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef otel   fill:#FFF7ED,stroke:#EA580C,color:#7C2D12
    classDef term   fill:#F1F5F9,stroke:#64748B,color:#0F172A
    classDef svc    fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F

    STU([Студент]):::term
    STU -->|Нажать 'Сдать'| WFE[Windchaser Frontend]:::svc
    WFE -->|POST /submit| WBE[Windchaser Backend]:::svc
    WBE -->|Publish task.submitted\nsession_id, task_id,\nfinal_solution| RS[(Redis Streams\ntask.submitted)]:::stream

    RS -->|XREADGROUP + 30 с| EA[Evaluator Agent]:::svc

    EA -->|GET rubric| RKV[(Redis KV\nRubric Store)]:::kv
    RKV -->|5-компонентная рубрика| EA

    EA -->|GET attempt_log| RKV2[(Redis KV\nAttempt Log)]:::kv
    RKV2 -->|Лог всех попыток| EA

    EA -->|solution + attempt_log\n+ rubric, ~3000 токенов, T=0.3| AAPI[Anthropic\nClaude API]:::svc
    AAPI -->|JSON: scores, feedback,\noverall_status| EA

    EA -->|PydanticValidator\nEvaluationResult schema| EA
    EA -->|INSERT evaluation| PG[(PostgreSQL\nevaluations)]:::pg
    EA -->|Publish evaluation.result\nscores, feedback, overall_status| RS2[(Redis Streams\nevaluation.result)]:::stream

    EA -->|Трейс: tokens, latency,\npydantic_retries, eval_status| OTL[OTel Collector]:::otel
    OTL -->|Метрики| PROM[Prometheus + Grafana]:::otel

    RS2 -->|XREADGROUP| ABS[AgentBridgeService]:::svc
    ABS -->|Результат оценки| WBE
    WBE -->|Render evaluation UI| WFE
    WFE -->|Оценка + обратная связь| STU
```

### Что хранится при сдаче задания

| Хранилище | Ключ / таблица | Данные | TTL / Retention |
|---|---|---|---|
| Redis KV | `task:{task_id}:rubric` | 5-компонентная рубрика | постоянно |
| Redis KV | `attempt_log:{task_id}:{student_id}` | лог попыток (источник для LLMAnalyzer) | 24 ч |
| Redis Streams | `task.submitted` | session_id, task_id, final_solution, dialog_log | до ACK + 7 дней |
| Redis Streams | `evaluation.result` | scores, feedback, overall_status | до ACK + 7 дней |
| **PostgreSQL** | `evaluations` | task_id, student_id, scores по критериям, feedback, overall_status, evaluation_status, created_at | постоянно |
| OTel / Prometheus | метрики | input_tokens, output_tokens, latency_ms, pydantic_retries, evaluation_status | 30 дней |

---

## 4. Сводная схема: что где хранится и логируется

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart TD
    classDef kv     fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef stream fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef pg     fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef otel   fill:#FFF7ED,stroke:#EA580C,color:#7C2D12
    classDef nolog  fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D

    subgraph INPUT ["Входные данные (не персонализированные)"]
        MD[Markdown KB\nТеория LLM Security\n~14 файлов, ~120k символов]
        RUB[Рубрики заданий\nRedis KV: task:*:rubric]:::kv
    end

    subgraph SESSION ["Сессионные данные (TTL 24ч)"]
        SESS[Redis KV\ntutor:session:*:history\nstage, hint_depth, failed_attempts]:::kv
        ATT[Redis KV\nattempt_log:*\nПопытки атак per студент]:::kv
    end

    subgraph BUS ["Шина событий (Redis Streams, 7 дней)"]
        E1[student.message]:::stream
        E2[tutor.response]:::stream
        E3[task.attempt]:::stream
        E4[validation.result]:::stream
        E5[task.submitted]:::stream
        E6[evaluation.result]:::stream
    end

    subgraph PERSIST ["Долгосрочное хранилище"]
        PG[(PostgreSQL\nРезультаты оценивания\nПрогресс студентов\nАналитика)]:::pg
    end

    subgraph OBS ["Наблюдаемость (30 дней)"]
        OTL[OTel Collector\nТрейсы LLM-вызовов]:::otel
        PROM[Prometheus + Grafana\nSCR, latency_p95, cost_per_call\ncircuit_breaker, guardrail, pydantic_retries]:::otel
    end

    subgraph NOLOG ["НЕ логируется (privacy)"]
        PII[PII студентов\nНЕ попадает в Anthropic\nНЕ попадает в логи]:::nolog
    end

    SESS -->|Источник для промпта тьютора| E1
    E1 -->|Обработан| SESS
    E3 -->|Обработан| ATT
    ATT -->|Источник для LLMAnalyzer| E5
    E5 -->|Результат| PG
    E6 -->|Сохранён| PG

    OTL --> PROM
```

## Что НЕ передаётся во внешние системы

- **PII студентов** (имена, email, ID) — не включаются в промпты для Anthropic API; промпты обезличены
- **Диалог тьютора** — не передаётся в Evaluator Agent; изоляция контекстов контролируется интеграционными тестами
- **Системные промпты (SCH)** — не раскрываются студентам и не логируются в открытом виде
- **Секреты заданий** (целевой системный промпт уязвимого LLM) — хранятся отдельно, не попадают в контекст тьютора
