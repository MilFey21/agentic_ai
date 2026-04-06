# Spec: Tools / APIs

**Модуль**: интеграции внешних API и внутренние инструменты агентов  
**Версия**: 1.0  
**Статус**: PoC / Готов к реализации

---

## 1. Внешние API

### 1.1 Anthropic Claude 3.5 Sonnet

**Протокол**: HTTPS REST  
**SDK**: `anthropic` Python SDK (прямой вызов, без LangChain)  
**Базовый URL**: `https://api.anthropic.com/v1`

#### Использование в агентах

| Агент | Функция | Модель | Температура | max_tokens |
|---|---|---|---|---|
| Tutor Agent | Генерация направляющего вопроса | claude-3-5-sonnet-20241022 | 0.7 | 512 |
| Stage Classifier | Классификация этапа студента | claude-3-5-sonnet-20241022 | 0.1 | 128 |
| LLMAnalyzer (Evaluator) | Качественный анализ по рубрике | claude-3-5-sonnet-20241022 | 0.3 | 1024 |
| Jailbreak Judge | Детекция jailbreak-попытки | claude-3-5-sonnet-20241022 | 0.0 | 64 |

#### Контракт вызова

```python
response = anthropic_client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=512,
    system=system_prompt,          # SCH-промпт с <theory_context>
    messages=conversation_history, # последние 10 реплик
)
```

#### Ошибки и retry

| Ошибка | HTTP код | Поведение |
|---|---|---|
| `RateLimitError` | 429 | Exponential backoff: 1 с, 2 с, 4 с (3 попытки) |
| `APIConnectionError` | — | Retry 3 раза; если все упали → circuit breaker |
| `APIStatusError` (5xx) | 500–599 | Retry 2 раза; затем fallback |
| `AuthenticationError` | 401 | Немедленная ошибка, алерт в мониторинг, без retry |

#### Circuit breaker

- Порог: 3 ошибки API за 60 секунд → переход в **аварийный режим**
- В аварийном режиме: тьютор возвращает статичный ответ, оценщик откладывает обработку
- Автоматическое восстановление: probe-запрос через 60 секунд

#### Таймауты

```python
anthropic_client = anthropic.Anthropic(
    api_key=settings.ANTHROPIC_API_KEY,
    timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
)
```

#### Защита от cost overrun

- Жёсткий `max_tokens` в каждом вызове (не снимается)
- Логирование `input_tokens` и `output_tokens` в каждом ответе
- Ежечасная агрегация стоимости: `cost_usd = input_tokens/1M * 3 + output_tokens/1M * 15`
- Алерт при превышении $10/час

---

### 1.2 Windchaser Platform (внешняя)

**Протокол**: REST + WebSocket  
**Аутентификация**: Bearer token (сервисный аккаунт)

#### REST эндпоинты (входящие из Windchaser)

| Метод | Путь | Описание | Timeout |
|---|---|---|---|
| `POST` | `/sessions` | Создание сессии при старте задания | 5 с |
| `DELETE` | `/sessions/{id}` | Принудительное завершение сессии | 5 с |
| `GET` | `/sessions/{id}/status` | Текущий этап и статус | 2 с |
| `GET` | `/evaluations/{id}` | Результат оценивания | 10 с |
| `POST` | `/theory/reindex` | Ручной триггер переиндексации | 30 с |

#### WebSocket (исходящий в Windchaser)

Тьютор публикует ответы через Redis Streams → AgentBridgeService → WebSocket → браузер студента.

#### Контракт события `student.message` (входящий)

```json
{
  "event_id": "evt_abc123",
  "session_id": "sess_xyz789",
  "task_id": "task_001",
  "student_id": "student_042",
  "content": "Как работает prompt injection?",
  "timestamp": "2026-04-06T10:30:00Z"
}
```

#### Контракт события `tutor.response` (исходящий)

```json
{
  "event_id": "evt_def456",
  "session_id": "sess_xyz789",
  "content": "Что происходит, когда модель видит пользовательский ввод?",
  "stage": "CONCEPT_EXPLORATION",
  "hint_depth": "shallow",
  "tokens_used": {"input": 4200, "output": 95},
  "timestamp": "2026-04-06T10:30:03Z"
}
```

---

## 2. Внутренние инструменты (tools агентов)

### 2.1 `validate_prompt_attack` (Programmatic Validator)

**Используется**: Evaluator Agent  
**Тип**: детерминированная проверка (без LLM)

```python
def validate_prompt_attack(
    student_prompt: str,
    task_type: Literal["system_prompt_extraction", "knowledge_base_secret_extraction"],
    target_response: str,           # ответ уязвимого чат-бота на атаку
) -> ValidationResult:
    ...

class ValidationResult:
    success: bool                   # факт успешности атаки
    extracted_content: str | None   # извлечённый фрагмент (если успех)
    match_method: str               # "regex" | "string_match" | "judge_model"
    confidence: float               # 0.0–1.0
```

**Логика проверки**:

1. `regex` — совпадение с шаблонами системного промпта/секрета
2. `string_match` — точное вхождение известных секретных строк
3. `judge_model` — вызов изолированной модели (T=0.0) при неопределённости

**Side effects**: нет. Чистая функция, детерминирована для методов 1 и 2.

**Таймаут**: 500 мс (p95). При превышении → `ValidationTimeoutError`, статус `success=False`.

---

### 2.2 `analyze_student_stage` (Stage Classifier)

**Используется**: Tutor Agent перед каждым LLM-вызовом

```python
def analyze_student_stage(
    history: list[Turn],            # последние 5 реплик
    failed_attempts: int,
) -> StageAnalysis:
    ...

class StageAnalysis:
    stage: Literal["ORIENTATION", "CONCEPT_EXPLORATION", "HYPOTHESIS_TESTING", "REFINEMENT", "SOLVED"]
    hint_depth: Literal["shallow", "medium", "deep"]
    reasoning: str                  # кратко для логов
```

**Реализация**: LLM-вызов (claude-3-5-sonnet, T=0.1, max_tokens=128).  
**Таймаут**: 3 с. При ошибке → сохраняем предыдущий `stage` из Redis.

---

### 2.3 `LLMAnalyzer` (Evaluator Agent)

**Используется**: Evaluator Agent после получения `task.submitted`

```python
def analyze_with_llm(
    final_solution: str,
    attempt_log: list[AttemptRecord],
    rubric: EvaluationRubric,
) -> EvaluationReport:
    ...

class EvaluationReport:
    overall_score: float            # 0.0–1.0
    passed: bool
    criteria: list[CriterionScore]  # 5 компонентов рубрики
    feedback: str                   # текстовая обратная связь
    evaluation_status: Literal["complete", "partial"]
```

**5 компонентов рубрики**:
1. Корректность техники атаки (technique_correctness)
2. Эффективность (effectiveness)
3. Оригинальность подхода (originality)
4. Понимание уязвимости (vulnerability_understanding)
5. Качество реализации (implementation_quality)

**Валидация ответа**: Pydantic-схема. При ошибке → retry до 2 раз с напоминанием схемы.  
При 3 неудачах → `evaluation_status: "partial"`, алерт в мониторинг.

---

## 3. Событийная шина Redis Streams

| Stream | Публикует | Потребляет | Retention |
|---|---|---|---|
| `student.message` | Windchaser | Tutor Agent | 24 ч |
| `tutor.response` | Tutor Agent | Windchaser | 24 ч |
| `task.attempt` | Windchaser | Programmatic Validator | 48 ч |
| `validation.result` | Programmatic Validator | Windchaser, Tutor Agent | 48 ч |
| `task.submitted` | Windchaser | Evaluator Agent | 72 ч |
| `evaluation.result` | Evaluator Agent | Windchaser | 72 ч |

**Идемпотентность**: каждое событие имеет уникальный `event_id`. При повторной доставке (сбой до ACK) проверяется наличие результата в Redis → повторная обработка пропускается.

**Consumer groups**: каждый агент имеет отдельную consumer group с `NOACK=False` (требуется явный ACK после успешной обработки).

---

## 4. Безопасность

- `ANTHROPIC_API_KEY` хранится только в переменных окружения, не логируется
- Все сервисные токены Windchaser — в Kubernetes Secrets (или `.env` для PoC)
- Входящие payload от Windchaser валидируются Pydantic-схемой перед обработкой
- PII (student_id, content) не включаются в трейсы OpenTelemetry (атрибут `redact=True`)
