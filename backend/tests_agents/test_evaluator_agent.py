"""
Тестирование EvaluatorAgent с использованием данных из dataset.
"""

import sys
from pathlib import Path
from typing import Any


# Добавляем корневую директорию проекта в путь
# Файл находится в backend/tests_agents/test_evaluator_agent.py
# project_root будет указывать на корень проекта (WindChaserSecurity/)
backend_dir = Path(__file__).parent.parent  # backend/
project_root = backend_dir.parent  # корень проекта
backend_src = backend_dir / 'src'  # backend/src
sys.path.insert(0, str(backend_src))
sys.path.insert(0, str(backend_dir))  # для импорта tests_agents
sys.path.insert(0, str(project_root))

from agents.evaluator.evaluator_agent import EvaluatorAgent
from tests_agents.data_loader import (
    load_evaluator_test_cases,
    parse_score_range,
)
from tests_agents.evaluator_metrics import (
    EvaluatorAggregatedMetrics,
    EvaluatorMetrics,
    evaluate_evaluator_result,
)


def test_evaluator_agent(
    dataset_path: Path | str,
    api_key: str | None = None,
    max_cases: int | None = None,
) -> tuple[list[EvaluatorMetrics], EvaluatorAggregatedMetrics, list[dict[str, Any]]]:
    """
    Протестировать EvaluatorAgent на данных из dataset.

    Args:
        dataset_path: Путь к папке dataset
        api_key: API ключ для OpenAI (если None, берется из переменной окружения)
        max_cases: Максимальное количество тестовых кейсов (если None, все)

    Returns:
        Кортеж (список метрик для каждого кейса, агрегированные метрики, список ответов агента)
    """
    # Загрузка тестовых данных
    print('Загрузка тестовых данных для EvaluatorAgent...')
    test_cases = load_evaluator_test_cases(dataset_path)

    if max_cases:
        test_cases = test_cases[:max_cases]

    print(f'Загружено {len(test_cases)} тестовых кейсов')

    # Инициализация агента
    print('Инициализация EvaluatorAgent...')
    try:
        agent = EvaluatorAgent(api_key=api_key)
    except ValueError as e:
        print(f'Ошибка инициализации агента: {e}')
        raise

    # Выполнение тестов
    results: list[EvaluatorMetrics] = []
    agent_responses: list[dict[str, Any]] = []

    for i, test_case in enumerate(test_cases, 1):
        print(f'\n[{i}/{len(test_cases)}] Тестирование кейса {test_case.prompt_id}...')
        print(f'  Промпт: {test_case.attack_prompt[:100]}...')
        print(f'  Ожидаемый статус: {test_case.expected_status}')
        print(f'  Ожидаемый диапазон баллов: {test_case.score_range}')

        try:
            # Подготовка assignment_requirements
            assignment_requirements = {
                'description': f'Задание по {test_case.assignment_type}',
                'success_criteria': {'min_completeness': 0.8},
            }

            # Добавление token_limit для token_limit_bypass
            if test_case.assignment_type == 'token_limit_bypass':
                assignment_requirements['token_limit'] = 1000

            # Подготовка test_logs (если есть extracted_content)
            test_logs = None
            if test_case.extracted_content:
                if test_case.assignment_type == 'system_prompt_extraction':
                    test_logs = {
                        'extracted_prompt': test_case.extracted_content,
                        'extraction_successful': test_case.extraction_successful,
                    }
                    # Добавляем extraction_completeness, если оно есть
                    if test_case.extraction_completeness is not None:
                        test_logs['extraction_completeness'] = test_case.extraction_completeness
                        # Также вычисляем original_prompt_length для обратной совместимости
                        if test_case.extraction_completeness > 0:
                            extracted_length = len(test_case.extracted_content)
                            test_logs['original_prompt_length'] = int(
                                extracted_length / test_case.extraction_completeness
                            )
                elif test_case.assignment_type == 'knowledge_base_secret_extraction':
                    test_logs = {
                        'extracted_secret': test_case.extracted_content,
                        'extraction_successful': test_case.extraction_successful,
                    }
                    # Добавляем extraction_completeness, если оно есть
                    if test_case.extraction_completeness is not None:
                        test_logs['extraction_completeness'] = test_case.extraction_completeness
                elif test_case.assignment_type == 'token_limit_bypass':
                    # Парсим количество токенов из extracted_content
                    # Формат: "Generated 5200 tokens"
                    import re

                    token_match = re.search(r'(\d+)', test_case.extracted_content)
                    if token_match:
                        tokens_generated = int(token_match.group(1))
                        test_logs = {
                            'tokens_generated': tokens_generated,
                            'token_limit': 1000,
                        }

            # Вызов агента
            result = agent.evaluate(
                assignment_type=test_case.assignment_type,
                student_solution=test_case.attack_prompt,
                assignment_requirements=assignment_requirements,
                test_logs=test_logs,
            )

            # Сохранение ответа агента с контекстом
            agent_response = {
                'prompt_id': test_case.prompt_id,
                'assignment_type': test_case.assignment_type,
                'attack_prompt': test_case.attack_prompt,
                'expected_status': test_case.expected_status,
                'score_range': test_case.score_range,
                **result,
            }
            agent_responses.append(agent_response)

            # Парсинг ожидаемого диапазона баллов
            score_min, score_max = parse_score_range(test_case.score_range)

            # Оценка результата
            metrics = evaluate_evaluator_result(
                result=result,
                expected_status=test_case.expected_status,
                expected_score_min=score_min,
                expected_score_max=score_max,
                assignment_type=test_case.assignment_type,
            )

            # Установка идентификаторов
            metrics.prompt_id = test_case.prompt_id
            metrics.attack_prompt = test_case.attack_prompt

            results.append(metrics)

            # Вывод результата
            print(f'  Предсказанный этап: {metrics.predicted_stage}')
            print(f'  Использованный валидатор: {metrics.validator_used}')
            print(f'  Предсказанный балл: {metrics.predicted_score:.1f}')
            print(f'  Ожидаемый диапазон: {score_min:.1f}-{score_max:.1f}')
            print(f'  Этап корректен: {metrics.stage_correct}')
            print(f'  Валидатор корректен: {metrics.validator_correct}')
            print(f'  Балл в диапазоне: {metrics.score_in_range}')
            print(f'  Использован LLM анализ: {metrics.llm_analysis_used}')
            print(f'  Использована теория: {metrics.theory_used}')

        except Exception as e:
            print(f'  ОШИБКА при тестировании кейса {test_case.prompt_id}: {e}')
            import traceback

            traceback.print_exc()
            # Сохранение ошибки в ответах
            agent_responses.append(
                {
                    'prompt_id': test_case.prompt_id,
                    'assignment_type': test_case.assignment_type,
                    'attack_prompt': test_case.attack_prompt,
                    'expected_status': test_case.expected_status,
                    'score_range': test_case.score_range,
                    'error': str(e),
                }
            )
            # Создаем метрики с ошибкой
            score_min, score_max = parse_score_range(test_case.score_range)
            metrics = EvaluatorMetrics(
                prompt_id=test_case.prompt_id,
                assignment_type=test_case.assignment_type,
                attack_prompt=test_case.attack_prompt,
                expected_status=test_case.expected_status,
                expected_score_min=score_min,
                expected_score_max=score_max,
            )
            results.append(metrics)

    # Вычисление агрегированных метрик
    print('\nВычисление агрегированных метрик...')
    aggregated = EvaluatorAggregatedMetrics()
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
    print('ТЕСТИРОВАНИЕ EVALUATOR AGENT')
    print('=' * 80)

    try:
        results, aggregated, agent_responses = test_evaluator_agent(
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
        print(f'Validator Selection Accuracy: {aggregated.validator_selection_accuracy:.2%}')
        print(f'Score Accuracy: {aggregated.score_accuracy:.2%}')
        print(f'LLM Analysis Usage Rate: {aggregated.llm_analysis_usage_rate:.2%}')
        print(f'Theory Usage Rate: {aggregated.theory_usage_rate:.2%}')

        print('\nМатрица путаницы для этапов:')
        for expected, predicted_dict in aggregated.stage_confusion_matrix.items():
            print(f'  Ожидаемый: {expected}')
            for predicted, count in predicted_dict.items():
                print(f'    Предсказанный: {predicted} - {count} случаев')

        print('\nСтатистика использования валидаторов:')
        for validator, count in sorted(aggregated.validator_usage_stats.items(), key=lambda x: -x[1]):
            print(f'  {validator}: {count}')

        if aggregated.validator_selection_errors:
            print(f'\nОшибки выбора валидаторов ({len(aggregated.validator_selection_errors)}):')
            for error in aggregated.validator_selection_errors[:5]:  # Показываем первые 5
                print(f'  Кейс {error["prompt_id"]}:')
                print(f'    Ожидался: {error["expected"]}')
                print(f'    Использован: {error["actual"]}')

        if aggregated.score_errors:
            print(f'\nОшибки по баллам ({len(aggregated.score_errors)}):')
            for error in aggregated.score_errors[:5]:  # Показываем первые 5
                print(f'  Кейс {error["prompt_id"]}:')
                print(f'    Предсказанный балл: {error["predicted_score"]:.1f}')
                print(f'    Ожидаемый диапазон: {error["expected_range"]}')
                print(f'    Отклонение: {error["difference"]:.1f}')

    except Exception as e:
        print(f'\nОШИБКА при выполнении тестов: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)
