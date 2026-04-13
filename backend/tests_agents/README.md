# Пайплайн тестирования агентов

Пайплайн для тестирования TutorAgent и EvaluatorAgent с использованием данных из папки `dataset`.

## Структура

```
tests_agents/
├── __init__.py
├── data_loader.py              # Загрузка данных из CSV
├── tutor_metrics.py            # Метрики для TutorAgent
├── evaluator_metrics.py        # Метрики для EvaluatorAgent
├── test_tutor_agent.py         # Тесты для TutorAgent
├── test_evaluator_agent.py     # Тесты для EvaluatorAgent
├── run_all_tests.py            # Главный скрипт для запуска всех тестов
├── results/                    # Директория для сохранения результатов (создается автоматически)
└── README.md                   # Этот файл
```

## Метрики

### TutorAgent

- **Stage Accuracy** - точность определения этапа работы студента (`initial`, `developing`, `reviewing`)
- **Tool Selection Accuracy** - точность выбора инструментов помощи
- **Guiding Questions Usage Accuracy** - точность использования наводящих вопросов
- **Theory Usage Rate** - частота использования теории (`retrieve_theory`, `provide_theory_context`)

### EvaluatorAgent

- **Stage Accuracy** - точность определения этапа (`initial`, `developing`, `completed`, `partial`)
- **Validator Selection Accuracy** - точность выбора валидатора для типа задания
- **Score Accuracy** - точность оценки (попадание балла в ожидаемый диапазон)
- **LLM Analysis Usage Rate** - частота использования LLM анализа (`analyze_solution_stage`)
- **Theory Usage Rate** - частота использования теории (`retrieve_theory`)

## Использование

### Требования

1. Установлен Python 3.13
2. Установлены зависимости проекта (`uv sync`)
3. Установлена переменная окружения `OPENAI_API_KEY` или `API_KEY`
4. Наличие папки `dataset` с файлами:
   - `student_questions_with_targets.csv` - для TutorAgent
   - `attack_prompts.csv` - для EvaluatorAgent

### Запуск всех тестов

```bash
cd backend
uv run python tests_agents/run_all_tests.py [max_cases]
```

Где `max_cases` - опциональный параметр, ограничивающий количество тестовых кейсов (для быстрого тестирования).

Пример:
```bash
# Запустить все тесты
uv run python tests_agents/run_all_tests.py

# Запустить только первые 10 кейсов каждого агента
uv run python tests_agents/run_all_tests.py 10
```

### Запуск тестов отдельного агента

```bash
# Тестирование только TutorAgent
uv run python tests_agents/test_tutor_agent.py

# Тестирование только EvaluatorAgent
uv run python tests_agents/test_evaluator_agent.py
```

## Результаты

Результаты тестирования сохраняются в директории `backend/tests_agents/results/`:

- `tutor_metrics_YYYYMMDD_HHMMSS.json` - детальные результаты TutorAgent
- `evaluator_metrics_YYYYMMDD_HHMMSS.json` - детальные результаты EvaluatorAgent
- `summary_YYYYMMDD_HHMMSS.json` - сводный отчет с основными метриками
- `tutor_responses_YYYYMMDD_HHMMSS.csv` - полные ответы TutorAgent в формате CSV для ручной оценки
- `evaluator_responses_YYYYMMDD_HHMMSS.csv` - полные ответы EvaluatorAgent в формате CSV для ручной оценки

### Формат результатов

Каждый файл результатов содержит:

```json
{
  "timestamp": "20250101_120000",
  "agent": "TutorAgent",
  "aggregated_metrics": {
    "total_cases": 100,
    "stage_accuracy": 0.85,
    "tool_selection_accuracy": 0.90,
    "guiding_questions_usage_accuracy": 0.75,
    "theory_usage_rate": 0.60,
    "stage_confusion_matrix": {...},
    "tool_usage_stats": {...}
  },
  "individual_results": [
    {
      "question_id": 1,
      "assignment_type": "system_prompt_extraction",
      "stage_correct": true,
      "tools_correct": true,
      ...
    },
    ...
  ]
}
```

### Формат CSV файлов с ответами агентов

CSV файлы содержат полные ответы агентов для ручной оценки. Сложные типы данных (списки, словари) сериализованы в JSON строки.

**tutor_responses_YYYYMMDD_HHMMSS.csv** содержит:
- `question_id` - идентификатор вопроса
- `assignment_type` - тип задания
- `student_question` - вопрос студента
- `help_text` - текст помощи от агента
- `stage` - определенный этап работы студента
- `tools_used` - список использованных инструментов (JSON)
- `guiding_questions` - наводящие вопросы (JSON)
- `examples` - примеры решений (JSON)
- `next_steps` - следующие шаги (JSON)
- `theory_reference` - ссылки на теорию
- `needs_student_response` - требуется ли ответ студента
- `agent_observations` - наблюдения агента для отладки (JSON)

**evaluator_responses_YYYYMMDD_HHMMSS.csv** содержит:
- `prompt_id` - идентификатор промпта
- `assignment_type` - тип задания
- `attack_prompt` - промпт атаки студента
- `expected_status` - ожидаемый статус (passed/failed/partial)
- `score_range` - ожидаемый диапазон баллов
- `is_passed` - прошел ли студент задание
- `score` - итоговый балл
- `stage` - определенный этап работы студента
- `tools_used` - список использованных инструментов (JSON)
- `feedback` - обратная связь студенту
- `detailed_analysis` - детальный анализ работы студента
- `improvement_suggestions` - рекомендации по улучшению (JSON)
- `criterion_scores` - баллы по критериям (JSON)
- `criterion_details` - детали критериев (JSON)
- `validation_iterations` - количество итераций валидации
- `agent_observations` - наблюдения агента для отладки (JSON)

## Интерпретация метрик

### Stage Accuracy

Показывает, насколько точно агент определяет этап работы студента:
- `1.0` (100%) - идеальная точность
- `0.8` (80%) - хорошая точность
- `< 0.7` (< 70%) - требует улучшения

### Tool Selection Accuracy

Показывает, насколько правильно агент выбирает инструменты:
- Проверяется использование ожидаемых инструментов
- Учитывается, что агент может использовать дополнительные инструменты

### Score Accuracy (только EvaluatorAgent)

Показывает, попадает ли оценка в ожидаемый диапазон:
- Учитывается диапазон баллов из `attack_prompts.csv`
- Если балл вне диапазона, это считается ошибкой

## Отладка

При возникновении ошибок проверьте:

1. **API ключ**: Убедитесь, что установлена переменная окружения `OPENAI_API_KEY`
2. **Путь к dataset**: Проверьте, что папка `dataset` находится в директории `tests_agents`
3. **Формат CSV**: Убедитесь, что CSV файлы имеют правильный формат и кодировку UTF-8
4. **Зависимости**: Убедитесь, что все зависимости установлены (`uv sync`)


