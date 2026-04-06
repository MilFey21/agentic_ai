# C4 Container — Frontend, Backend, Orchestrator, Retriever, Tool Layer, Storage, Observability

Диаграмма раскрывает внутреннее устройство мультиагентной системы: контейнеры, их технологии и способы взаимодействия.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart TD
    classDef fe      fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F
    classDef agent   fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef storage fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef db      fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef kb      fill:#F0FDF4,stroke:#22C55E,color:#166534
    classDef ext     fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef mon     fill:#FFF7ED,stroke:#EA580C,color:#7C2D12
    classDef term    fill:#F1F5F9,stroke:#64748B,color:#0F172A

    STU([Студент]):::term

    subgraph PLAT["Windchaser Platform"]
        WFE[Windchaser Frontend\nReact / TypeScript]:::fe
        WBE[Windchaser Backend\nPython / FastAPI]:::fe
        ABS[AgentBridgeService\nPython / FastStream]:::fe

        subgraph CORE["Агентное ядро"]
            TA[Tutor Agent\nPython / Anthropic SDK]:::agent
            EA[Evaluator Agent\nPython / Anthropic SDK]:::agent
            PV[Programmatic Validator\nPython]:::agent
            TR[TheoryRetriever\nPython]:::agent
        end

        subgraph STOR["Хранилище"]
            REDIS[(Redis\nStreams + KV)]:::storage
            PG[(PostgreSQL\nоценки · прогресс)]:::db
            MKB[(Markdown KB\n~14 MD-файлов)]:::kb
        end

        OTEL[OTel Collector\nтрейсы · SCR · latency]:::mon
    end

    AAPI[Anthropic Claude API\nClaude 3.5 Sonnet]:::ext
    PROM[Prometheus + Grafana]:::mon

    STU -->|HTTPS / WebSocket| WFE
    WFE <-->|API + WebSocket| WBE
    WBE <-->|события / ответы| ABS
    ABS <-->|Publish / Consume Streams| REDIS

    TA <-->|Consume / Publish / R/W state| REDIS
    EA <-->|Consume / Publish| REDIS
    PV <-->|Consume / Publish| REDIS

    TA -->|search → theory_context| TR
    TR -->|индексация при старте| MKB

    TA & EA -->|LLM-запросы, HTTPS| AAPI

    EA -->|INSERT evaluation| PG
    WBE -->|SQL| PG

    TA & EA -->|трейсы + метрики| OTEL
    OTEL -->|Prometheus / OTLP| PROM
```

## Пояснения к контейнерам

| Контейнер | Технология | Роль |
|---|---|---|
| **Windchaser Frontend** | React / TypeScript | UI: чат с тьютором, задания, просмотр результатов через WebSocket |
| **Windchaser Backend** | FastAPI | LMS-логика, аутентификация, WebSocket-стриминг ответов агентов студенту |
| **AgentBridgeService** | FastStream | Развязка платформы и агентного ядра через Redis Streams |
| **Tutor Agent** | Anthropic SDK | Сократический тьютор; SCH-иерархия, анализ этапа, постпроцессинг |
| **Evaluator Agent** | Anthropic SDK | Оценщик; LLMAnalyzer + Pydantic-валидация JSON |
| **Programmatic Validator** | Pure Python | Детерминированный валидатор факта атаки (без LLM) |
| **TheoryRetriever** | Pure Python | Keyword-search по Markdown-индексу; deterministic |
| **Redis** | Redis Streams + KV | Брокер + сессионное state-хранилище |
| **PostgreSQL** | PostgreSQL | Долгосрочное хранилище оценок, прогресса, пользователей |
| **Markdown KB** | FS | Источник теории для индексации TheoryRetriever |
| **OTel Collector** | OpenTelemetry | Агрегация трейсов и метрик перед отправкой в Grafana |
