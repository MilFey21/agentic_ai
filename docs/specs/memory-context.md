# Spec: Memory / Context

**Модули**: `backend/src/agents/tutor_agent.py`, `backend/src/storage/session_store.py`  
**Версия**: 1.0  
**Статус**: PoC / Готов к реализации

---

## Назначение

Определяет, как система хранит состояние диалога, управляет контекстным окном LLM и изолирует память между агентами.

---

## 1. Сессионное состояние тьютора (TutorSessionState)

### Хранилище

**Ключ Redis**: `tutor:session:{session_id}:state`  
**Формат**: JSON  
**TTL**: 24 часа (сбрасывается при каждом обновлении)

### Схема

```python
class TutorSessionState(BaseModel):
    session_id: str
    task_id: str
    student_id: str
    history: list[Turn]                     # полная история диалога
    current_stage: Stage
    hint_depth: HintDepth
    failed_attempts: int
    stage_transitions: list[StageTransition]
    created_at: datetime
    updated_at: datetime

class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime

class StageTransition(BaseModel):
    from_stage: Stage
    to_stage: Stage
    at: datetime
    trigger: str                            # "failed_attempt" | "llm_classifier" | "manual"

Stage = Literal["ORIENTATION", "CONCEPT_EXPLORATION", "HYPOTHESIS_TESTING", "REFINEMENT", "SOLVED"]
HintDepth = Literal["shallow", "medium", "deep"]
```

### Политика обновления

| Событие | Действие |
|---|---|
| Новое сообщение студента | Append `Turn(role="user", ...)`, обновить `updated_at` |
| Ответ тьютора | Append `Turn(role="assistant", ...)` |
| Изменение этапа | Append `StageTransition`, обновить `current_stage` |
| Неуспешная попытка атаки | Инкремент `failed_attempts` |
| `failed_attempts >= 3` | Перевод `hint_depth` на следующий уровень |

---

## 2. Контекстный бюджет тьютора

Каждый LLM-вызов формируется из следующих компонентов:

| Компонент | Источник | Размер (токены) |
|---|---|---|
| Системный промпт (статика SCH) | Hardcoded | ~500–700 |
| `<theory_context>` | TheoryRetriever | ~300–500 |
| История диалога | `history[-10:]` | ~2000–3000 |
| **Итого входной контекст** | — | **< 5000** |
| Ответ (max_tokens) | Ограничение | **512** |

### Управление историей

- В LLM-запрос включаются **последние 10 реплик** из `history`
- Полная история сохраняется в Redis (без усечения)
- При восстановлении сессии после перезапуска — состояние загружается из Redis целиком

### Принудительное усечение ответа

Если LLM возвращает ответ длиной > 512 токенов (edge case при streaming):

1. Усечение по последнему полному предложению
2. Если усечённый текст не содержит `?` — добавляется generic вопрос: «Что вы думаете об этом?»
3. Предупреждение в лог: `response_truncated=true`

---

## 3. Изоляция контекста оценщика

### Инвариант

**Evaluator Agent не имеет доступа к ключам `tutor:session:*`.**

Входные данные оценщика поступают исключительно из:
- Payload события `task.submitted` (содержит `dialog_log` и `final_solution`)
- `task:{task_id}:rubric` (статичная рубрика задания)

### Проверка инварианта

Инвариант проверяется автоматическими интеграционными тестами при каждой сборке:

```python
def test_evaluator_has_no_tutor_session_access():
    # Evaluator Agent не должен читать ключи tutor:session:*
    with mock_redis() as redis:
        evaluator.process(task_submitted_event)
        accessed_keys = redis.get_accessed_keys()
        assert not any(k.startswith("tutor:session:") for k in accessed_keys)
```

### Мотивация

Разделение контекстов устраняет конфликт ролей «помощника» и «судьи»: оценщик работает только с финальным результатом и не знает, какие подсказки давал тьютор.

---

## 4. Контекст Evaluator Agent

### Входные данные для LLMAnalyzer

```python
class EvaluatorContext(BaseModel):
    task_id: str
    task_type: str
    final_solution: str             # финальный промпт/решение студента
    attempt_log: list[AttemptRecord]# все попытки за сессию
    rubric: EvaluationRubric        # критерии оценивания

class AttemptRecord(BaseModel):
    attempt_number: int
    student_prompt: str
    success: bool
    extracted_content: str | None
    timestamp: datetime
```

### Контекстный бюджет оценщика

| Компонент | Размер (токены) |
|---|---|
| Системный промпт с рубрикой | ~600–800 |
| `final_solution` | ~200–400 |
| `attempt_log` (последние 5 попыток) | ~500–800 |
| **Итого** | **< 3000** |
| Ответ (max_tokens) | **1024** |

---

## 5. Memory policy (сводка)

| Параметр | Тьютор | Оценщик |
|---|---|---|
| Хранилище | Redis (персистентно) | Нет постоянного хранения |
| TTL сессии | 24 ч | N/A |
| История в LLM | последние 10 реплик | N/A (stateless) |
| Доступ к чужим сессиям | Нет | Нет |
| Восстановление при перезапуске | Да (из Redis) | N/A |
| Изоляция между студентами | Да (по `session_id`) | Да (по `task_id`) |

---

## 6. Ошибки и edge cases

| Ситуация | Поведение |
|---|---|
| Redis недоступен при чтении состояния | Создать пустое состояние, предупреждение в лог |
| Redis недоступен при записи состояния | Ответ отправляется, но состояние не сохраняется → потеря диалога |
| Сессия не найдена по `session_id` | `SessionNotFoundError` → Windchaser получает 404 |
| TTL истёк, студент вернулся | Создание новой сессии, история не восстанавливается |
| Повреждённый JSON в Redis | `SessionCorruptedError` → создать новую сессию, алерт |
