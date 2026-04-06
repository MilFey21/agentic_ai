# Spec: Observability / Evals

**Модули**: OpenTelemetry SDK, Prometheus, Grafana, `backend/src/observability/`  
**Версия**: 1.0  
**Статус**: PoC / Готов к реализации

---

## Назначение

Определяет, что и как измеряется в системе: метрики качества агентов, операционные метрики, логи, трейсы и автоматические проверки (evals).

---

## 1. Метрики качества агентов (business / ML)

### 1.1 Tutor Agent

| Метрика | Формула / Определение | Целевое значение | Где собирается |
|---|---|---|---|
| **SCR** (Socratic Compliance Rate) | Доля ответов тьютора, содержащих `?` | ≥ 85% за скользящий час | Автоматически, post-processing |
| **Guardrail trigger rate** | Доля вызовов, где SCH-инвариант нарушен до retry | < 5% | Счётчик `guardrail_triggered_total` |
| **Neutral fallback rate** | Доля ответов, где все 3 retry нарушили SCH | < 1% | Счётчик `neutral_fallback_total` |
| **Stage accuracy** | Совпадение классифицированного stage с экспертной разметкой | ≥ 60% (baseline: 16%) | Offline eval на датасете |
| **Session completion rate** | Доля сессий, завершившихся stage=SOLVED | > 30% пилота | PostgreSQL аналитика |

### 1.2 Evaluator Agent

| Метрика | Формула / Определение | Целевое значение | Где собирается |
|---|---|---|---|
| **Pass/Fail accuracy** | Совпадение pass/fail с экспертом | ≥ 0.8 accuracy | Offline eval |
| **Score accuracy** | MAE оценки vs эксперт | < 0.2 (baseline: 0.48 accuracy) | Offline eval |
| **Cohen's kappa** | Согласованность оценки между запусками | ≥ 0.7 | Offline eval (re-evaluation test) |
| **Partial evaluation rate** | Доля оценок со статусом `partial` | < 3% | Счётчик `partial_evaluation_total` |
| **Pydantic retry rate** | Доля оценок, потребовавших retry | < 10% | Счётчик `evaluator_retry_total` |

### 1.3 TheoryRetriever

| Метрика | Формула / Определение | Целевое значение |
|---|---|---|
| **Retrieval relevance** | Доля запросов, где найденный узел релевантен запросу (экспертная оценка) | ≥ 70% на тестовых запросах |
| **Fallback rate** | Доля запросов, где использован fallback | < 20% |
| **Source citation accuracy** | Доля ответов тьютора с корректными ссылками на теорию | ≥ 80% |

---

## 2. Операционные метрики (Prometheus)

### Латентность

```prometheus
# Histogram метрики
tutor_agent_latency_ms{quantile="0.5"}   < 2000 мс
tutor_agent_latency_ms{quantile="0.95"}  < 7000 мс
evaluator_agent_latency_ms{quantile="0.95"}  < 30000 мс
retriever_latency_ms{quantile="0.95"}    < 50 мс
validator_latency_ms{quantile="0.95"}    < 500 мс
api_request_latency_ms{quantile="0.95"}  < 200 мс
```

### Счётчики

```prometheus
llm_calls_total{agent, status}           # успешные / ошибочные вызовы LLM
llm_tokens_total{agent, type}            # input / output токены
llm_cost_usd_total{agent}               # расчётная стоимость
circuit_breaker_open_total               # сколько раз срабатывал circuit breaker
guardrail_triggered_total                # нарушения SCH до retry
neutral_fallback_total                   # нейтральные fallback-ответы
retriever_fallback_total                 # fallback в retriever
partial_evaluation_total                 # частичные оценки
redis_stream_lag{stream}                 # задержка обработки событий
```

### Алерты (Grafana)

| Алерт | Условие | Severity |
|---|---|---|
| High LLM error rate | `llm_errors_total > 3` за 60 с | Critical (circuit breaker) |
| Low SCR | SCR < 85% за скользящий час | Warning |
| High cost | `llm_cost_usd_total > $10` за час | Warning |
| Queue lag | `redis_stream_lag > 100` событий | Warning |
| High fallback rate | `retriever_fallback_total / requests > 20%` за час | Warning |
| Partial evaluation spike | `partial_evaluation_total > 3%` за день | Warning |

---

## 3. Логи

### Формат

Структурированные JSON-логи. Каждая запись содержит:

```json
{
  "timestamp": "2026-04-06T10:30:03.123Z",
  "level": "INFO",
  "service": "tutor-agent",
  "event": "llm_call_complete",
  "session_id": "sess_xyz789",
  "task_id": "task_001",
  "stage": "CONCEPT_EXPLORATION",
  "hint_depth": "shallow",
  "input_tokens": 4200,
  "output_tokens": 95,
  "latency_ms": 2341,
  "scr": true,
  "guardrail_triggered": false,
  "is_fallback": false
}
```

### Что логируется

| Событие | Поля |
|---|---|
| Каждый LLM-вызов | `agent`, `session_id`, `task_id`, `stage`, `input_tokens`, `output_tokens`, `latency_ms`, `model` |
| SCH-нарушение | `guardrail_triggered=true`, `prohibited_term`, `attempt_count` |
| Neutral fallback | `neutral_fallback=true`, `reason` |
| Retriever-вызов | `query`, `task_id`, `result_score`, `is_fallback`, `latency_ms` |
| Evaluator результат | `task_id`, `passed`, `overall_score`, `evaluation_status`, `retry_count` |
| Circuit breaker | `state_change` (closed→open, open→closed) |

### Что НЕ логируется (privacy)

- Полный текст сообщений студентов (только хэш или длина)
- `student_id` в трейсах OpenTelemetry (атрибут `redact=True`)
- `ANTHROPIC_API_KEY` и другие секреты

---

## 4. Трейсы (OpenTelemetry)

**Экспортёр**: OTLP → Jaeger (PoC) / Tempo (production)

### Span-структура на один вызов тьютора

```
tutor.handle_message [root span]
  ├── redis.load_session
  ├── retriever.search
  ├── llm.classify_stage
  ├── llm.generate_response
  │     └── anthropic.messages.create
  ├── postprocessing.check_sch
  ├── redis.save_session
  └── redis.publish_response
```

### Обязательные атрибуты span

```python
span.set_attribute("session_id", session_id)
span.set_attribute("task_id", task_id)
span.set_attribute("stage", stage)
span.set_attribute("agent", "tutor")
# НЕ добавлять: student_id, content (PII)
```

---

## 5. Offline Evals (автоматические)

### Датасет

- Расположение: `backend/tests_agents/dataset/`
- Формат: CSV с полями `query`, `task_id`, `expected_stage`, `expert_score`, `expert_pass`
- Объём: ≥ 50 диалогов для тьютора, ≥ 30 решений для оценщика

### Запуск

```bash
# После каждого изменения промптов или модели
pytest backend/tests_agents/ -v --eval-mode
```

### Проверяемые инварианты

```python
# Тьютор
assert scr >= 0.85                  # SCR на датасете
assert guardrail_rate < 0.05        # не раскрыл запрещённое
assert "?" in every_tutor_response  # каждый ответ — вопрос

# Оценщик
assert pass_fail_accuracy >= 0.80   # совпадение с экспертом
assert evaluator_has_no_tutor_session_access()  # изоляция контекста

# Retriever
assert retrieval_relevance >= 0.70  # точность поиска
assert fallback_rate < 0.20         # редкий fallback
```

### Регрессионные тесты

При изменении промптов — сравнение со snapshot предыдущего запуска. Если `scr < previous_scr - 5%` → тест падает, требуется явное подтверждение регрессии.

---

## 6. Observability в PoC vs Production

| Компонент | PoC | Production |
|---|---|---|
| Метрики | Prometheus + stdout | Prometheus + Grafana Cloud |
| Логи | Structured JSON в файлы | ELK Stack (Elasticsearch + Kibana) |
| Трейсы | Jaeger (локально) | Tempo + Grafana |
| Алерты | Grafana alerting | PagerDuty / Slack |
| Evals | pytest вручную | CI/CD при каждом PR |
