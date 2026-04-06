# C4 Context — Система, пользователь, внешние сервисы и границы

Диаграмма показывает систему мультиагентного обучения целиком как «чёрный ящик» в окружении людей и внешних систем.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#EFF6FF", "primaryBorderColor": "#3B82F6", "primaryTextColor": "#1E3A5F", "lineColor": "#64748B", "secondaryColor": "#F0FDF4", "tertiaryColor": "#FFFBEB"}}}%%
C4Context
    title C4 Context: Мультиагентная система поддержки обучения Windchaser

    Person(student, "Студент", "Задания LLM Security: диалог с тьютором, промпт-атаки, сдача")
    Person(instructor, "Преподаватель / Админ", "Аналитика, управление базой знаний, мониторинг метрик")

    System_Boundary(windchaser_sys, "Windchaser Platform") {
        System(windchaser, "Windchaser", "Образовательная LMS-платформа: курсы, задания, интерфейс студента")
        System(agent_system, "Мультиагентная система", "Тьютор, оценщик, TheoryRetriever, событийная шина")
    }

    System_Ext(anthropic, "Anthropic Claude API", "Claude 3.5 Sonnet: генерация, классификация, анализ")
    System_Ext(yandex_cloud, "Yandex Cloud / Kubernetes", "Managed Kubernetes, Managed Redis, container registry")
    System_Ext(monitoring, "Prometheus + Grafana", "SCR, latency, cost per token, алерты")

    Rel(student, windchaser, "Взаимодействует через веб-интерфейс", "HTTPS / WebSocket")
    Rel(instructor, windchaser, "Управляет курсом, смотрит аналитику", "HTTPS")
    Rel(instructor, agent_system, "Управляет контентом, ребилдит индекс", "REST API")

    Rel(windchaser, agent_system, "События студентов → ответы агентов", "Redis Streams + REST")
    Rel(agent_system, anthropic, "Генерация, классификация, анализ решений", "HTTPS")
    Rel(agent_system, yandex_cloud, "Развёртывание контейнеров, Managed Redis", "Kubernetes API")
    Rel(agent_system, monitoring, "Экспортирует метрики и трейсы", "OpenTelemetry / Prometheus")
```

## Пояснения

| Актор / система | Роль |
|---|---|
| **Студент** | Основной пользователь: задаёт вопросы тьютору, пробует атаки, сдаёт задания |
| **Преподаватель** | Мониторит прогресс студентов, управляет базой знаний, настраивает задания |
| **Windchaser** | LMS-платформа — источник событий и потребитель ответов агентов |
| **Мультиагентная система** | Ядро: обрабатывает события, генерирует ответы, оценивает задания |
| **Anthropic Claude API** | Внешний LLM-провайдер; единственная внешняя зависимость для интеллектуальных функций |
| **Yandex Cloud** | Инфраструктура развёртывания; Managed Redis — персистентный брокер и state store |
| **Prometheus + Grafana** | Наблюдаемость: SCR, latency, cost per call, circuit breaker state |

## Границы системы

- Всё внутри `Windchaser Platform` — под контролем команды
- Anthropic Claude API — внешняя зависимость; деградация защищена circuit breaker
- Пользовательские данные (PII) не передаются в Anthropic; промпты обезличены
