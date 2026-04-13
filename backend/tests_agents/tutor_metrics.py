"""
Метрики для оценки TutorAgent.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TutorMetrics:
    """Метрики для одного тестового кейса TutorAgent."""

    question_id: int
    assignment_type: str
    student_question: str

    # Предсказанные значения
    predicted_stage: str | None = None
    tools_used: list[str] = field(default_factory=list)
    used_guiding_question: bool = False
    used_theory: bool = False

    # Ожидаемые значения
    expected_stage: str | None = None
    expected_tools: list[str] = field(default_factory=list)
    expected_guiding_question: bool = False

    # Результаты проверки
    stage_correct: bool = False
    tools_correct: bool = False
    guiding_question_correct: bool = False
    theory_used: bool = False

    def calculate_metrics(self) -> dict[str, Any]:
        """
        Вычислить метрики для этого кейса.

        Returns:
            Словарь с метриками
        """
        return {
            'question_id': self.question_id,
            'assignment_type': self.assignment_type,
            'stage_correct': self.stage_correct,
            'tools_correct': self.tools_correct,
            'guiding_question_correct': self.guiding_question_correct,
            'theory_used': self.theory_used,
            'predicted_stage': self.predicted_stage,
            'expected_stage': self.expected_stage,
            'tools_used': self.tools_used,
            'expected_tools': self.expected_tools,
            'used_guiding_question': self.used_guiding_question,
            'expected_guiding_question': self.expected_guiding_question,
        }


@dataclass
class TutorAggregatedMetrics:
    """Агрегированные метрики для всех тестов TutorAgent."""

    total_cases: int = 0
    stage_accuracy: float = 0.0
    tool_selection_accuracy: float = 0.0
    guiding_questions_usage_accuracy: float = 0.0
    theory_usage_rate: float = 0.0

    # Детальная статистика по этапам
    stage_confusion_matrix: dict[str, dict[str, int]] = field(default_factory=dict)

    # Детальная статистика по инструментам
    tool_usage_stats: dict[str, int] = field(default_factory=dict)
    tool_selection_errors: list[dict[str, Any]] = field(default_factory=list)

    def calculate_from_results(self, results: list[TutorMetrics]) -> None:
        """
        Вычислить агрегированные метрики из списка результатов.

        Args:
            results: Список результатов тестирования
        """
        self.total_cases = len(results)

        if self.total_cases == 0:
            return

        # Accuracy определения этапа
        stage_correct = sum(1 for r in results if r.stage_correct)
        self.stage_accuracy = stage_correct / self.total_cases

        # Tool Selection Accuracy
        tools_correct = sum(1 for r in results if r.tools_correct)
        self.tool_selection_accuracy = tools_correct / self.total_cases

        # Guiding Questions Usage Accuracy
        guiding_correct = sum(1 for r in results if r.guiding_question_correct)
        self.guiding_questions_usage_accuracy = guiding_correct / self.total_cases

        # Theory Usage Rate
        theory_used_count = sum(1 for r in results if r.theory_used)
        self.theory_usage_rate = theory_used_count / self.total_cases

        # Confusion matrix для этапов
        self.stage_confusion_matrix = {}
        for result in results:
            expected = result.expected_stage or 'unknown'
            predicted = result.predicted_stage or 'unknown'

            if expected not in self.stage_confusion_matrix:
                self.stage_confusion_matrix[expected] = {}

            if predicted not in self.stage_confusion_matrix[expected]:
                self.stage_confusion_matrix[expected][predicted] = 0

            self.stage_confusion_matrix[expected][predicted] += 1

        # Статистика использования инструментов
        for result in results:
            for tool in result.tools_used:
                self.tool_usage_stats[tool] = self.tool_usage_stats.get(tool, 0) + 1

        # Ошибки выбора инструментов
        for result in results:
            if not result.tools_correct:
                missing_tools = set(result.expected_tools) - set(result.tools_used)
                extra_tools = set(result.tools_used) - set(result.expected_tools)

                if missing_tools or extra_tools:
                    self.tool_selection_errors.append(
                        {
                            'question_id': result.question_id,
                            'expected': result.expected_tools,
                            'actual': result.tools_used,
                            'missing': list(missing_tools),
                            'extra': list(extra_tools),
                        }
                    )

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать метрики в словарь для логирования."""
        return {
            'total_cases': self.total_cases,
            'stage_accuracy': self.stage_accuracy,
            'tool_selection_accuracy': self.tool_selection_accuracy,
            'guiding_questions_usage_accuracy': self.guiding_questions_usage_accuracy,
            'theory_usage_rate': self.theory_usage_rate,
            'stage_confusion_matrix': self.stage_confusion_matrix,
            'tool_usage_stats': self.tool_usage_stats,
            'tool_selection_errors_count': len(self.tool_selection_errors),
        }


def evaluate_tutor_result(
    result: dict[str, Any],
    expected_stage: str,
    expected_tools: list[str],
    expected_guiding_question: bool,
) -> TutorMetrics:
    """
    Оценить результат работы TutorAgent.

    Args:
        result: Результат вызова help_student
        expected_stage: Ожидаемый этап
        expected_tools: Ожидаемые инструменты
        expected_guiding_question: Ожидается ли использование guiding question

    Returns:
        Метрики для этого кейса
    """
    predicted_stage = result.get('stage')
    tools_used = result.get('tools_used', [])
    guiding_questions = result.get('guiding_questions', [])

    # Проверка использования теории
    theory_tools = ['retrieve_theory', 'provide_theory_context']
    used_theory = any(tool in tools_used for tool in theory_tools)

    # Проверка использования guiding questions
    used_guiding_question = len(guiding_questions) > 0

    # Проверка корректности этапа
    stage_correct = predicted_stage == expected_stage

    # Проверка корректности выбора инструментов
    # Проверяем, что все ожидаемые инструменты использованы
    expected_set = set(expected_tools)
    used_set = set(tools_used)
    tools_correct = expected_set.issubset(used_set) or (
        len(expected_set) > 0 and len(used_set.intersection(expected_set)) > 0
    )

    # Проверка корректности использования guiding questions
    guiding_question_correct = used_guiding_question == expected_guiding_question

    metrics = TutorMetrics(
        question_id=0,  # Будет установлено позже
        assignment_type='',
        student_question='',
        predicted_stage=predicted_stage,
        tools_used=tools_used,
        used_guiding_question=used_guiding_question,
        used_theory=used_theory,
        expected_stage=expected_stage,
        expected_tools=expected_tools,
        expected_guiding_question=expected_guiding_question,
        stage_correct=stage_correct,
        tools_correct=tools_correct,
        guiding_question_correct=guiding_question_correct,
        theory_used=used_theory,
    )

    return metrics
