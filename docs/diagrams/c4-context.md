# C4 Context — Система, пользователь, внешние сервисы и границы

Диаграмма показывает систему мультиагентного обучения целиком как «чёрный ящик» в окружении пользователей и внешних систем.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}, "flowchart": {"curve": "basis", "diagramPadding": 20}}}%%
flowchart TD
    classDef person fill:#DBEAFE,stroke:#2563EB,color:#1E3A5F
    classDef core   fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef ext    fill:#FEF9C3,stroke:#CA8A04,color:#713F12
    classDef mon    fill:#FFF7ED,stroke:#EA580C,color:#7C2D12
    classDef cloud  fill:#F3E8FF,stroke:#9333EA,color:#3B0764

    STU([Студент\nLLM Security: задания · атаки · сдача]):::person

    subgraph PLAT["Windchaser Platform"]
        WC[Windchaser LMS\nкурсы · задания · UI студента]:::core
        MAS[Мультиагентная система\nтьютор · оценщик · Retriever\nRedis Streams шина]:::core
        WC <-->|события ↔ ответы\nRedis Streams + REST| MAS
    end

    AAPI[Anthropic Claude API\nClaude 3.5 Sonnet]:::ext
    YC[Yandex Cloud\nManaged Kubernetes\nManaged Redis]:::cloud
    MON[Prometheus + Grafana\nSCR · latency · cost · alerts]:::mon

    STU -->|HTTPS / WebSocket| WC
    MAS -->|LLM-запросы, HTTPS| AAPI
    MAS -->|деплой + Managed Redis\nKubernetes API| YC
    MAS -->|метрики + трейсы, OTel| MON
```

## Пояснения

| Актор / система | Роль |
|---|---|
| **Студент** | Основной пользователь: задаёт вопросы тьютору, пробует атаки, сдаёт задания |
| **Windchaser** | LMS-платформа — источник событий и потребитель ответов агентов |
| **Мультиагентная система** | Ядро: обрабатывает события, генерирует ответы, оценивает задания |
| **Anthropic Claude API** | Внешний LLM-провайдер; единственная внешняя зависимость для интеллектуальных функций |
| **Yandex Cloud** | Инфраструктура развёртывания; Managed Redis — персистентный брокер и state store |
| **Prometheus + Grafana** | Наблюдаемость: SCR, latency, cost per call, circuit breaker state |

## Границы системы

- Всё внутри `Windchaser Platform` — под контролем команды
- Anthropic Claude API — внешняя зависимость; деградация защищена circuit breaker
- Пользовательские данные (PII) не передаются в Anthropic; промпты обезличены
