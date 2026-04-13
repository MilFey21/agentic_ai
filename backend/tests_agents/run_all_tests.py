"""
Главный скрипт для запуска всех тестов агентов с логированием метрик.
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Добавляем корневую директорию проекта в путь
# Файл находится в backend/tests_agents/run_all_tests.py
# project_root будет указывать на корень проекта (WindChaserSecurity/)
backend_dir = Path(__file__).parent.parent  # backend/
project_root = backend_dir.parent  # корень проекта
backend_src = backend_dir / 'src'  # backend/src
sys.path.insert(0, str(backend_src))
sys.path.insert(0, str(backend_dir))  # для импорта tests_agents
sys.path.insert(0, str(project_root))

from tests_agents.test_evaluator_agent import test_evaluator_agent
from tests_agents.test_tutor_agent import test_tutor_agent


def save_agent_responses_to_csv(
    agent_responses: list[dict[str, Any]],
    agent_name: str,
    output_dir: Path,
    timestamp: str,
) -> None:
    """
    Сохранить ответы агента в CSV файл.

    Args:
        agent_responses: Список ответов агента
        agent_name: Имя агента ('tutor' или 'evaluator')
        output_dir: Директория для сохранения
        timestamp: Временная метка для имени файла
    """
    if not agent_responses:
        print(f'Предупреждение: Нет ответов для сохранения {agent_name} агента')
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_file = output_dir / f'{agent_name}_responses_{timestamp}.csv'

    # Определяем все возможные поля из всех ответов
    all_fields = set()
    for response in agent_responses:
        all_fields.update(response.keys())

    # Сортируем поля для консистентности
    field_order = []
    if agent_name == 'tutor':
        field_order = [
            'question_id',
            'assignment_type',
            'student_question',
            'help_text',
            'stage',
            'tools_used',
            'guiding_questions',
            'examples',
            'next_steps',
            'theory_reference',
            'needs_student_response',
            'agent_observations',
            'error',
        ]
    else:  # evaluator
        field_order = [
            'prompt_id',
            'assignment_type',
            'attack_prompt',
            'expected_status',
            'score_range',
            'is_passed',
            'score',
            'stage',
            'tools_used',
            'feedback',
            'detailed_analysis',
            'improvement_suggestions',
            'criterion_scores',
            'criterion_details',
            'validation_iterations',
            'agent_observations',
            'error',
        ]

    # Добавляем остальные поля в конец
    remaining_fields = sorted(all_fields - set(field_order))
    fieldnames = field_order + remaining_fields

    try:
        # Записываем CSV с правильной обработкой специальных символов
        # Используем utf-8-sig для добавления BOM (для лучшей совместимости с Excel)
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                extrasaction='ignore',
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()

            for response in agent_responses:
                # Преобразуем сложные типы в строки для CSV
                row = {}
                for key, value in response.items():
                    if isinstance(value, (list, dict)):
                        # Сериализуем списки и словари в JSON строки
                        row[key] = json.dumps(value, ensure_ascii=False)
                    elif value is None:
                        row[key] = ''
                    else:
                        # Преобразуем значение в строку
                        # CSV модуль автоматически правильно экранирует переносы строк
                        row[key] = str(value)
                writer.writerow(row)

        # Проверяем, что файл был создан и не пустой
        if csv_file.exists():
            file_size = csv_file.stat().st_size
            if file_size > 0:
                print(
                    f'✅ Ответы {agent_name} агента сохранены в {csv_file} ({len(agent_responses)} записей, {file_size} байт)'
                )
            else:
                print(f'⚠️  Файл {csv_file} создан, но пуст')
        else:
            print(f'❌ Ошибка: файл {csv_file} не был создан')
    except Exception as e:
        print(f'❌ Ошибка при сохранении CSV для {agent_name} агента: {e}')
        import traceback

        traceback.print_exc()


def save_results(
    tutor_results: tuple,
    evaluator_results: tuple,
    output_dir: Path,
) -> None:
    """
    Сохранить результаты тестирования в файлы.

    Args:
        tutor_results: Результаты тестирования TutorAgent
        evaluator_results: Результаты тестирования EvaluatorAgent
        output_dir: Директория для сохранения результатов
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Сохранение результатов TutorAgent
    tutor_metrics_list, tutor_aggregated, tutor_responses = tutor_results

    tutor_output = {
        'timestamp': timestamp,
        'agent': 'TutorAgent',
        'aggregated_metrics': tutor_aggregated.to_dict(),
        'individual_results': [m.calculate_metrics() for m in tutor_metrics_list],
    }

    tutor_file = output_dir / f'tutor_metrics_{timestamp}.json'
    with open(tutor_file, 'w', encoding='utf-8') as f:
        json.dump(tutor_output, f, ensure_ascii=False, indent=2)

    print(f'\nРезультаты TutorAgent сохранены в {tutor_file}')

    # Сохранение ответов TutorAgent в CSV
    save_agent_responses_to_csv(tutor_responses, 'tutor', output_dir, timestamp)

    # Сохранение результатов EvaluatorAgent
    evaluator_metrics_list, evaluator_aggregated, evaluator_responses = evaluator_results

    evaluator_output = {
        'timestamp': timestamp,
        'agent': 'EvaluatorAgent',
        'aggregated_metrics': evaluator_aggregated.to_dict(),
        'individual_results': [m.calculate_metrics() for m in evaluator_metrics_list],
    }

    evaluator_file = output_dir / f'evaluator_metrics_{timestamp}.json'
    with open(evaluator_file, 'w', encoding='utf-8') as f:
        json.dump(evaluator_output, f, ensure_ascii=False, indent=2)

    print(f'Результаты EvaluatorAgent сохранены в {evaluator_file}')

    # Сохранение ответов EvaluatorAgent в CSV
    save_agent_responses_to_csv(evaluator_responses, 'evaluator', output_dir, timestamp)

    # Сохранение сводного отчета
    summary = {
        'timestamp': timestamp,
        'tutor_agent': {
            'total_cases': tutor_aggregated.total_cases,
            'stage_accuracy': tutor_aggregated.stage_accuracy,
            'tool_selection_accuracy': tutor_aggregated.tool_selection_accuracy,
            'guiding_questions_usage_accuracy': tutor_aggregated.guiding_questions_usage_accuracy,
            'theory_usage_rate': tutor_aggregated.theory_usage_rate,
        },
        'evaluator_agent': {
            'total_cases': evaluator_aggregated.total_cases,
            'stage_accuracy': evaluator_aggregated.stage_accuracy,
            'validator_selection_accuracy': evaluator_aggregated.validator_selection_accuracy,
            'score_accuracy': evaluator_aggregated.score_accuracy,
            'llm_analysis_usage_rate': evaluator_aggregated.llm_analysis_usage_rate,
            'theory_usage_rate': evaluator_aggregated.theory_usage_rate,
        },
    }

    summary_file = output_dir / f'summary_{timestamp}.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'Сводный отчет сохранен в {summary_file}')


def print_summary(tutor_results: tuple, evaluator_results: tuple) -> None:
    """
    Вывести сводку результатов тестирования.

    Args:
        tutor_results: Результаты тестирования TutorAgent
        evaluator_results: Результаты тестирования EvaluatorAgent
    """
    tutor_metrics_list, tutor_aggregated, _ = tutor_results
    evaluator_metrics_list, evaluator_aggregated, _ = evaluator_results

    print('\n' + '=' * 80)
    print('СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ')
    print('=' * 80)

    print('\n📚 TUTOR AGENT:')
    print(f'  Всего тестовых кейсов: {tutor_aggregated.total_cases}')
    print(f'  ✅ Accuracy определения этапа: {tutor_aggregated.stage_accuracy:.2%}')
    print(f'  ✅ Tool Selection Accuracy: {tutor_aggregated.tool_selection_accuracy:.2%}')
    print(f'  ✅ Guiding Questions Usage Accuracy: {tutor_aggregated.guiding_questions_usage_accuracy:.2%}')
    print(f'  ✅ Theory Usage Rate: {tutor_aggregated.theory_usage_rate:.2%}')

    print('\n📊 EVALUATOR AGENT:')
    print(f'  Всего тестовых кейсов: {evaluator_aggregated.total_cases}')
    print(f'  ✅ Accuracy определения этапа: {evaluator_aggregated.stage_accuracy:.2%}')
    print(f'  ✅ Validator Selection Accuracy: {evaluator_aggregated.validator_selection_accuracy:.2%}')
    print(f'  ✅ Score Accuracy: {evaluator_aggregated.score_accuracy:.2%}')
    print(f'  ✅ LLM Analysis Usage Rate: {evaluator_aggregated.llm_analysis_usage_rate:.2%}')
    print(f'  ✅ Theory Usage Rate: {evaluator_aggregated.theory_usage_rate:.2%}')

    print('\n' + '=' * 80)


def main():
    """Главная функция для запуска всех тестов."""
    # Путь к dataset (находится в папке tests_agents)
    dataset_path = Path(__file__).parent / 'dataset'

    # API ключ из переменной окружения
    api_key = os.environ.get('OPENAI_API_KEY')

    if not api_key:
        print('ОШИБКА: Не найден API ключ. Установите OPENAI_API_KEY')
        sys.exit(1)

    # Параметры тестирования
    max_cases = None
    if len(sys.argv) > 1:
        try:
            max_cases = int(sys.argv[1])
        except ValueError:
            print(f'Предупреждение: неверный аргумент {sys.argv[1]}, используем все кейсы')

    # Директория для сохранения результатов
    output_dir = backend_dir / 'tests_agents' / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)

    print('=' * 80)
    print('ПАЙПЛАЙН ТЕСТИРОВАНИЯ АГЕНТОВ')
    print('=' * 80)
    print(f'\nДата и время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Dataset: {dataset_path}')
    print(f'Максимум кейсов: {max_cases or "все"}')
    print(f'Результаты будут сохранены в: {output_dir}')

    # Тестирование TutorAgent
    print('\n' + '=' * 80)
    print('ТЕСТИРОВАНИЕ TUTOR AGENT')
    print('=' * 80)

    try:
        tutor_results = test_tutor_agent(
            dataset_path=dataset_path,
            api_key=api_key,
            max_cases=max_cases,
        )
    except Exception as e:
        print(f'\nОШИБКА при тестировании TutorAgent: {e}')
        import traceback

        traceback.print_exc()
        tutor_results = None

    # Тестирование EvaluatorAgent
    print('\n' + '=' * 80)
    print('ТЕСТИРОВАНИЕ EVALUATOR AGENT')
    print('=' * 80)

    try:
        evaluator_results = test_evaluator_agent(
            dataset_path=dataset_path,
            api_key=api_key,
            max_cases=max_cases,
        )
    except Exception as e:
        print(f'\nОШИБКА при тестировании EvaluatorAgent: {e}')
        import traceback

        traceback.print_exc()
        evaluator_results = None

    # Сохранение результатов
    if tutor_results and evaluator_results:
        try:
            save_results(tutor_results, evaluator_results, output_dir)
            print_summary(tutor_results, evaluator_results)
        except Exception as e:
            print(f'\nОШИБКА при сохранении результатов: {e}')
            import traceback

            traceback.print_exc()

    print('\n' + '=' * 80)
    print('ТЕСТИРОВАНИЕ ЗАВЕРШЕНО')
    print('=' * 80)


if __name__ == '__main__':
    main()
