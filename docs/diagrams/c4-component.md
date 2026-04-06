# C4 Component — Внутреннее устройство ядра системы

Диаграмма раскрывает компоненты внутри **Tutor Agent** и **Evaluator Agent** — ядра мультиагентной системы. Именно здесь сосредоточена вся LLM-логика, SCH-иерархия, retrieval-контур и механизмы защиты.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart LR
    classDef consumer fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F
    classDef state    fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef llm      fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef guard    fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef pub      fill:#F3E8FF,stroke:#9333EA,color:#3B0764
    classDef err      fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    classDef ext      fill:#F1F5F9,stroke:#64748B,color:#0F172A

    REDIS[(Redis\nStreams + KV)]:::ext
    AAPI[Anthropic\nClaude API]:::ext
    TR[TheoryRetriever\nKeyword-search]:::ext
    PG[(PostgreSQL)]:::ext

    subgraph TUTOR["  Tutor Agent  "]
        direction TB
        T_EC[StreamConsumer\nFastStream]:::consumer
        T_SM[SessionManager\nRedis KV, TTL 24ч]:::state
        T_SC[StageClassifier\nT=0.1, 5 реплик]:::llm
        T_CB[CircuitBreaker\n3 ошибки / 60 с]:::err
        T_SPB[SCHPromptBuilder\nP1 · P2 · P3 + контекст]:::llm
        T_LC[LLMCaller\nT=0.7, max_tokens=512]:::llm
        T_PP[PostProcessor\nguardrails · retry ×3]:::guard
        T_SCR[SCRTracker\nSCR < 85% → alert]:::guard
        T_SP[StreamPublisher\ntutor.response]:::pub

        T_EC --> T_SM & T_SC & T_SPB
        T_SC & T_LC --> T_CB
        T_SPB --> T_LC
        T_LC --> T_PP
        T_PP --> T_SCR & T_SP
    end

    subgraph EVAL["  Evaluator Agent  "]
        direction TB
        E_EC[StreamConsumer\nFastStream, 30 с задержка]:::consumer
        E_RL[RubricLoader\n5-компонентная рубрика]:::state
        E_LA[LLMAnalyzer\nT=0.3, JSON]:::llm
        E_PV[PydanticValidator\nretry ×2 · partial result]:::guard
        E_SP[StreamPublisher\nevaluation.result + INSERT]:::pub

        E_EC --> E_RL --> E_LA --> E_PV --> E_SP
    end

    REDIS -->|student.message\nvalidation.result| T_EC
    REDIS -->|task.submitted| E_EC
    T_SM <-->|GET/SET state| REDIS
    E_RL -->|GET rubric| REDIS
    T_SP -->|XADD tutor.response| REDIS
    E_SP -->|XADD evaluation.result| REDIS

    T_SC & T_LC -->|messages.create| AAPI
    E_LA -->|messages.create| AAPI

    T_SPB -->|search(query)| TR

    E_SP -->|INSERT evaluation| PG
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
