"""
Модуль для загрузки тестовых данных из dataset.
"""

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TutorTestCase:
    """Тестовый кейс для TutorAgent."""

    question_id: int
    assignment_type: str
    student_question: str
    expected_stage: str
    expected_tools: list[str]
    expected_help_type: str
    expected_guiding_question: bool


@dataclass
class EvaluatorTestCase:
    """Тестовый кейс для EvaluatorAgent."""

    prompt_id: int
    assignment_type: str
    attack_prompt: str
    extraction_successful: bool
    extracted_content: str
    extraction_completeness: float | None  # Доля извлечения (0.0-1.0), None для token_limit_bypass
    score_range: str  # Формат: "min-max"
    expected_status: str  # passed, failed, partial


def load_tutor_test_cases(dataset_path: Path | str) -> list[TutorTestCase]:
    """
    Загрузить тестовые кейсы для TutorAgent из CSV.

    Args:
        dataset_path: Путь к папке dataset

    Returns:
        Список тестовых кейсов
    """
    dataset_path = Path(dataset_path)
    csv_path = dataset_path / 'student_questions_with_targets.csv'

    if not csv_path.exists():
        raise FileNotFoundError(f'Файл {csv_path} не найден')

    test_cases = []

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Парсинг expected_tools из строки вида "tool1,tool2,tool3"
            expected_tools_str = row.get('expected_tools', '')
            expected_tools = [tool.strip() for tool in expected_tools_str.split(',') if tool.strip()]

            test_case = TutorTestCase(
                question_id=int(row['question_id']),
                assignment_type=row['assignment_type'],
                student_question=row['student_question'],
                expected_stage=row['student_stage'],
                expected_tools=expected_tools,
                expected_help_type=row.get('expected_help_type', ''),
                expected_guiding_question=row.get('expected_guiding_question', 'false').lower() == 'true',
            )
            test_cases.append(test_case)

    return test_cases


def load_evaluator_test_cases(dataset_path: Path | str) -> list[EvaluatorTestCase]:
    """
    Загрузить тестовые кейсы для EvaluatorAgent из CSV.

    Args:
        dataset_path: Путь к папке dataset

    Returns:
        Список тестовых кейсов
    """
    dataset_path = Path(dataset_path)
    csv_path = dataset_path / 'attack_prompts.csv'

    if not csv_path.exists():
        raise FileNotFoundError(f'Файл {csv_path} не найден')

    test_cases = []

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Парсинг extraction_successful из строки "true"/"false"
            extraction_successful = row.get('extraction_successful', 'false').lower() == 'true'

            # Парсинг extraction_completeness (может быть пустым для token_limit_bypass)
            extraction_completeness_str = row.get('extraction_completeness', '').strip()
            extraction_completeness = None
            if extraction_completeness_str:
                try:
                    extraction_completeness = float(extraction_completeness_str)
                except ValueError:
                    extraction_completeness = None

            test_case = EvaluatorTestCase(
                prompt_id=int(row['prompt_id']),
                assignment_type=row['assignment_type'],
                attack_prompt=row['attack_prompt'],
                extraction_successful=extraction_successful,
                extracted_content=row.get('extracted_content', ''),
                extraction_completeness=extraction_completeness,
                score_range=row.get('score_range', '0-0'),
                expected_status=row.get('status', 'failed'),
            )
            test_cases.append(test_case)

    return test_cases


def parse_score_range(score_range: str) -> tuple[float, float]:
    """
    Парсить диапазон баллов из строки вида "min-max".

    Args:
        score_range: Строка вида "85-95" или "0-20"

    Returns:
        Кортеж (min_score, max_score)
    """
    try:
        parts = score_range.split('-')
        if len(parts) == 2:
            return (float(parts[0]), float(parts[1]))
        return (0.0, 0.0)
    except (ValueError, IndexError):
        return (0.0, 0.0)
