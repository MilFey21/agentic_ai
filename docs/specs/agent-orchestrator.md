# Spec: Agent / Orchestrator

**Модули**: `backend/src/agents/tutor_agent.py`, `backend/src/agents/evaluator_agent.py`, `backend/src/agents/programmatic_validator.py`  
**Версия**: 1.0  
**Статус**: PoC / Готов к реализации

---

## Назначение

Определяет внутреннюю логику обоих агентов: шаги выполнения, правила переходов между состояниями, условия остановки, механики retry и fallback. Агенты не вызывают друг друга напрямую — взаимодействие только через Redis Streams.

---

## 1. Tutor Agent

### Подписка и запуск

- **Consumer group**: `tutor-agent`
- **Stream**: `student.message`
- **Параллелизм**: до 4 worker-процессов (горизонтальное масштабирование)

### Шаги обработки сообщения

```
[1] Получить событие student.message
    → Десериализация и Pydantic-валидация payload
    → При ошибке: NACK, алерт, сообщение в dead letter queue

[2] Загрузить TutorSessionState из Redis
    → Если сессия не найдена: создать новую с stage=ORIENTATION

[3] TheoryRetriever.search(query=content, task_id=task_id)
    → Получить <theory_context>
    → Timeout 100 мс; при превышении: пустой контекст + лог

[4] analyze_student_stage(history[-5:], failed_attempts)
    → LLM-классификатор (T=0.1, max_tokens=128)
    → Timeout 3 с; при ошибке: сохранить предыдущий stage

[5] Построить LLM-запрос:
    system = SCH_PROMPT + <theory_context>
    messages = history[-10:]

[6] LLM-вызов: ask_guiding_question()
    → claude-3-5-sonnet, T=0.7, max_tokens=512
    → Timeout 20 с

[7] Post-processing ответа (обязателен):
    (a) Проверка SCH-инварианта (prohibited_terms_check)
    (b) Наличие '?' в ответе
    (c) Длина ответа ≤ 512 токенов

[8] Обновить TutorSessionState в Redis
    → Append history, обновить stage/hint_depth

[9] Публикация tutor.response в Redis Streams
    → ACK события student.message
```

### SCH-инвариант (шаг 7a)

Ответ проверяется на наличие терминов из `PROHIBITED_TERMS` — списка конкретных техник атаки, которые тьютор не должен раскрывать.

```
При обнаружении запрещённого термина:
  → Повторный LLM-вызов с усиленным ограничивающим инструктажем
  → До 3 попыток
  → Если все 3 нарушают инвариант: neutral fallback
  → Лог: guardrail_triggered=true, attempt_count=N
```

**Neutral fallback**: «Давайте подумаем вместе — какова цель этого задания?»

### Правила переходов между этапами

| Из | В | Триггер |
|---|---|---|
| ORIENTATION | CONCEPT_EXPLORATION | Stage Classifier решил, что студент понял постановку задачи |
| CONCEPT_EXPLORATION | HYPOTHESIS_TESTING | Студент предложил конкретную гипотезу |
| HYPOTHESIS_TESTING | REFINEMENT | Попытка атаки выполнена (любой результат) |
| HYPOTHESIS_TESTING | REFINEMENT | `failed_attempts >= 1` |
| REFINEMENT | SOLVED | `validation.result.success == true` |
| Любой | REFINEMENT | `failed_attempts >= 3` (принудительный переход) |

### Адаптация `hint_depth`

| `failed_attempts` | `hint_depth` |
|---|---|
| 0–2 | shallow |
| 3–5 | medium |
| 6+ | deep |

Тьютор адаптирует конкретность направляющих вопросов в зависимости от `hint_depth`.

### Stop condition

Тьютор прекращает активную работу при:
- `stage == SOLVED` — публикует поздравительное сообщение и завершает сессию
- `task.submitted` получено — Evaluator Agent берёт управление

### Retry и fallback тьютора

| Ситуация | Retry | Fallback |
|---|---|---|
| LLM timeout / ошибка сети | 3 раза (exponential backoff) | Статичный ответ «Система временно недоступна» |
| SCH-нарушение | До 3 повторных вызовов с усиленным промптом | Neutral fallback |
| Ответ без `?` | Автодобавление generic-вопроса | — |
| Stage Classifier упал | 0 retry | Сохранить предыдущий stage |

---

## 2. Programmatic Validator

### Подписка и запуск

- **Consumer group**: `validator`
- **Stream**: `task.attempt`
- **Параллелизм**: 2 worker-процесса

### Шаги обработки

```
[1] Получить событие task.attempt
    → Валидация payload

[2] validate_prompt_attack(student_prompt, task_type, target_response)
    → Детерминированная проверка: regex → string_match → judge_model
    → Timeout 500 мс

[3] Публикация validation.result:
    → В stream validation.result (Windchaser получает мгновенную обратную связь)
    → В stream validation.result (Tutor Agent обновляет failed_attempts)

[4] ACK события task.attempt
```

### Детерминированность

Методы `regex` и `string_match` полностью детерминированы. Метод `judge_model` (T=0.0) используется только при неоднозначных случаях и также стремится к детерминированности.

**Инвариант**: LLM не может изменить факт `success`. Только Programmatic Validator определяет, успешна ли атака.

---

## 3. Evaluator Agent

### Подписка и запуск

- **Consumer group**: `evaluator-agent`
- **Stream**: `task.submitted`
- **Параллелизм**: 1 worker-процесс (оценки не параллелятся)

### Шаги обработки

```
[1] Получить событие task.submitted
    → Валидация payload

[2] Задержка 30 секунд
    → Ожидание завершения записи всех попыток в Redis

[3] Собрать EvaluatorContext:
    → final_solution из payload
    → attempt_log из Redis: attempt:{task_id}:*
    → rubric из Redis: task:{task_id}:rubric

[4] LLMAnalyzer(context) → EvaluationReport
    → claude-3-5-sonnet, T=0.3, max_tokens=1024
    → Timeout 25 с

[5] Pydantic-валидация EvaluationReport
    → При ошибке: retry до 2 раз с напоминанием схемы
    → При исчерпании: evaluation_status="partial", алерт

[6] Сохранить результат в Redis: evaluation:{task_id}
    → TTL 7 дней

[7] Публикация evaluation.result
    → ACK события task.submitted
```

### Retry и fallback оценщика

| Ситуация | Retry | Fallback |
|---|---|---|
| LLM timeout / ошибка | 2 раза | `evaluation_status="partial"`, алерт |
| Pydantic-валидация не прошла | 2 раза с уточнённым промптом | `evaluation_status="partial"` |
| Redis недоступен при сборке контекста | 0 | Отложить обработку на 60 с (переполнение очереди) |

### Stop condition

Evaluator Agent завершает обработку события после публикации `evaluation.result`. Повторные `task.submitted` для той же `task_id` + `session_id` → идемпотентность (результат уже есть в Redis → пропустить).

---

## 4. Идемпотентность

Все агенты проверяют уникальный `event_id` перед обработкой:

```python
if await redis.exists(f"processed:{event_id}"):
    await stream.ack(event_id)
    return  # уже обработано

# ... обработка ...

await redis.set(f"processed:{event_id}", "1", ex=86400)  # TTL 24 ч
await stream.ack(event_id)
```

---

## 5. SCH (Socratic Constraint Hierarchy)

Системный промпт тьютора имеет явную иерархию приоритетов:

| Приоритет | Тип ограничения | Пример | Может быть снят? |
|---|---|---|---|
| 1 (абсолютный) | Запреты | Раскрытие конкретных техник атаки | Никогда |
| 2 (педагогический) | Предписания | Только вопросы, не ответы | Только адаптивными исключениями |
| 3 (адаптивный) | Исключения | Более прямая подсказка при hint_depth=deep | Да, при соблюдении уровня 1 |

Попытки студента снять ограничения уровня 1 (через аргументы «нехватки времени», «педагогической нецелесообразности», прямые просьбы) логируются с меткой `guardrail_triggered`.
