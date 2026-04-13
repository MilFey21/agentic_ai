"""
Тестирование TutorAgent с использованием данных из dataset.
"""

import sys
from pathlib import Path
from typing import Any


# Добавляем корневую директорию проекта в путь
# Файл находится в backend/tests_agents/test_tutor_agent.py
# project_root будет указывать на корень проекта (WindChaserSecurity/)
backend_dir = Path(__file__).parent.parent  # backend/
project_root = backend_dir.parent  # корень проекта
backend_src = backend_dir / 'src'  # backend/src
sys.path.insert(0, str(backend_src))
sys.path.insert(0, str(backend_dir))  # для импорта tests_agents
sys.path.insert(0, str(project_root))

from agents.tutor.tutor_agent import TutorAgent
from tests_agents.data_loader import load_tutor_test_cases
from tests_agents.tutor_metrics import (
    TutorAggregatedMetrics,
    TutorMetrics,
    evaluate_tutor_result,
)


def test_tutor_agent(
    dataset_path: Path | str,
    api_key: str | None = None,
    max_cases: int | None = None,
) -> tuple[list[TutorMetrics], TutorAggregatedMetrics, list[dict[str, Any]]]:
    """
    Протестировать TutorAgent на данных из dataset.

    Args:
        dataset_path: Путь к папке dataset
        api_key: API ключ для OpenAI (если None, берется из переменной окружения)
        max_cases: Максимальное количество тестовых кейсов (если None, все)

    Returns:
        Кортеж (список метрик для каждого кейса, агрегированные метрики, список ответов агента)
    """
    # Загрузка тестовых данных
    print('Загрузка тестовых данных для TutorAgent...')
    test_cases = load_tutor_test_cases(dataset_path)

    if max_cases:
        test_cases = test_cases[:max_cases]

    print(f'Загружено {len(test_cases)} тестовых кейсов')

    # Инициализация агента
    print('Инициализация TutorAgent...')
    try:
        agent = TutorAgent(api_key=api_key)
    except ValueError as e:
        print(f'Ошибка инициализации агента: {e}')
        raise

    # Выполнение тестов
    results: list[TutorMetrics] = []
    agent_responses: list[dict[str, Any]] = []
    assignment_requirements = {
        'description': 'Задание по безопасности AI-систем',
        'success_criteria': {'min_completeness': 0.8},
    }

    for i, test_case in enumerate(test_cases, 1):
        print(f'\n[{i}/{len(test_cases)}] Тестирование кейса {test_case.question_id}...')
        print(f'  Вопрос: {test_case.student_question[:100]}...')
        print(f'  Ожидаемый этап: {test_case.expected_stage}')
        print(f'  Ожидаемые инструменты: {test_case.expected_tools}')

        try:
            # Вызов агента
            result = agent.help_student(
                assignment_type=test_case.assignment_type,
                student_question=test_case.student_question,
                assignment_requirements=assignment_requirements,
                student_current_solution=None,
            )

            # Сохранение ответа агента с контекстом
            agent_response = {
                'question_id': test_case.question_id,
                'assignment_type': test_case.assignment_type,
                'student_question': test_case.student_question,
                **result,
            }
            agent_responses.append(agent_response)

            # Оценка результата
            metrics = evaluate_tutor_result(
                result=result,
                expected_stage=test_case.expected_stage,
                expected_tools=test_case.expected_tools,
                expected_guiding_question=test_case.expected_guiding_question,
            )

            # Установка идентификаторов
            metrics.question_id = test_case.question_id
            metrics.assignment_type = test_case.assignment_type
            metrics.student_question = test_case.student_question

            results.append(metrics)

            # Вывод результата
            print(f'  Предсказанный этап: {metrics.predicted_stage}')
            print(f'  Использованные инструменты: {metrics.tools_used}')
            print(f'  Этап корректен: {metrics.stage_correct}')
            print(f'  Инструменты корректны: {metrics.tools_correct}')
            print(f'  Использована теория: {metrics.theory_used}')
            print(f'  Использован guiding question: {metrics.used_guiding_question}')

        except Exception as e:
            print(f'  ОШИБКА при тестировании кейса {test_case.question_id}: {e}')
            # Сохранение ошибки в ответах
            agent_responses.append(
                {
                    'question_id': test_case.question_id,
                    'assignment_type': test_case.assignment_type,
                    'student_question': test_case.student_question,
                    'error': str(e),
                }
            )
            # Создаем метрики с ошибкой
            metrics = TutorMetrics(
                question_id=test_case.question_id,
                assignment_type=test_case.assignment_type,
                student_question=test_case.student_question,
                expected_stage=test_case.expected_stage,
                expected_tools=test_case.expected_tools,
                expected_guiding_question=test_case.expected_guiding_question,
            )
            results.append(metrics)

    # Вычисление агрегированных метрик
    print('\nВычисление агрегированных метрик...')
    aggregated = TutorAggregatedMetrics()
    aggregated.calculate_from_results(results)

    return results, aggregated, agent_responses


if __name__ == '__main__':
    import os

    # Путь к dataset (находится в папке tests_agents)
    dataset_path = Path(__file__).parent / 'dataset'

    # API ключ из переменной окружения
    api_key = os.environ.get('OPENAI_API_KEY')

    if not api_key:
        print('ОШИБКА: Не найден API ключ. Установите OPENAI_API_KEY')
        sys.exit(1)

    # Запуск тестов
    print('=' * 80)
    print('ТЕСТИРОВАНИЕ TUTOR AGENT')
    print('=' * 80)

    try:
        results, aggregated, agent_responses = test_tutor_agent(
            dataset_path=dataset_path,
            api_key=api_key,
            max_cases=10,  # Для быстрого теста
        )

        # Вывод результатов
        print('\n' + '=' * 80)
        print('РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ')
        print('=' * 80)
        print(f'\nВсего тестовых кейсов: {aggregated.total_cases}')
        print(f'Accuracy определения этапа: {aggregated.stage_accuracy:.2%}')
        print(f'Tool Selection Accuracy: {aggregated.tool_selection_accuracy:.2%}')
        print(f'Guiding Questions Usage Accuracy: {aggregated.guiding_questions_usage_accuracy:.2%}')
        print(f'Theory Usage Rate: {aggregated.theory_usage_rate:.2%}')

        print('\nМатрица путаницы для этапов:')
        for expected, predicted_dict in aggregated.stage_confusion_matrix.items():
            print(f'  Ожидаемый: {expected}')
            for predicted, count in predicted_dict.items():
                print(f'    Предсказанный: {predicted} - {count} случаев')

        print('\nСтатистика использования инструментов:')
        for tool, count in sorted(aggregated.tool_usage_stats.items(), key=lambda x: -x[1]):
            print(f'  {tool}: {count}')

        if aggregated.tool_selection_errors:
            print(f'\nОшибки выбора инструментов ({len(aggregated.tool_selection_errors)}):')
            for error in aggregated.tool_selection_errors[:5]:  # Показываем первые 5
                print(f'  Кейс {error["question_id"]}:')
                print(f'    Ожидалось: {error["expected"]}')
                print(f'    Получено: {error["actual"]}')
                if error['missing']:
                    print(f'    Отсутствуют: {error["missing"]}')
                if error['extra']:
                    print(f'    Лишние: {error["extra"]}')

    except Exception as e:
        print(f'\nОШИБКА при выполнении тестов: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)
