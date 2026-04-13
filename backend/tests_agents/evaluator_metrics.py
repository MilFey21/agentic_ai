"""
Метрики для оценки EvaluatorAgent.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluatorMetrics:
    """Метрики для одного тестового кейса EvaluatorAgent."""

    prompt_id: int
    assignment_type: str
    attack_prompt: str

    # Предсказанные значения
    predicted_stage: str | None = None
    validator_used: str | None = None
    predicted_score: float = 0.0
    used_llm_analysis: bool = False
    used_theory: bool = False

    # Ожидаемые значения
    expected_status: str | None = None  # passed, failed, partial
    expected_score_min: float = 0.0
    expected_score_max: float = 0.0
    expected_validator: str | None = None

    # Результаты проверки
    stage_correct: bool = False
    validator_correct: bool = False
    score_in_range: bool = False
    llm_analysis_used: bool = False
    theory_used: bool = False

    def calculate_metrics(self) -> dict[str, Any]:
        """
        Вычислить метрики для этого кейса.

        Returns:
            Словарь с метриками
        """
        return {
            'prompt_id': self.prompt_id,
            'assignment_type': self.assignment_type,
            'stage_correct': self.stage_correct,
            'validator_correct': self.validator_correct,
            'score_in_range': self.score_in_range,
            'llm_analysis_used': self.llm_analysis_used,
            'theory_used': self.theory_used,
            'predicted_stage': self.predicted_stage,
            'validator_used': self.validator_used,
            'expected_validator': self.expected_validator,
            'predicted_score': self.predicted_score,
            'expected_score_range': f'{self.expected_score_min}-{self.expected_score_max}',
            'used_llm_analysis': self.used_llm_analysis,
            'used_theory': self.used_theory,
        }


@dataclass
class EvaluatorAggregatedMetrics:
    """Агрегированные метрики для всех тестов EvaluatorAgent."""

    total_cases: int = 0
    stage_accuracy: float = 0.0
    validator_selection_accuracy: float = 0.0
    score_accuracy: float = 0.0
    llm_analysis_usage_rate: float = 0.0
    theory_usage_rate: float = 0.0

    # Детальная статистика по этапам
    stage_confusion_matrix: dict[str, dict[str, int]] = field(default_factory=dict)

    # Детальная статистика по валидаторам
    validator_usage_stats: dict[str, int] = field(default_factory=dict)
    validator_selection_errors: list[dict[str, Any]] = field(default_factory=list)

    # Статистика по баллам
    score_errors: list[dict[str, Any]] = field(default_factory=list)

    def calculate_from_results(self, results: list[EvaluatorMetrics]) -> None:
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

        # Validator Selection Accuracy
        validator_correct = sum(1 for r in results if r.validator_correct)
        self.validator_selection_accuracy = validator_correct / self.total_cases

        # Score Accuracy (попадание в диапазон)
        score_correct = sum(1 for r in results if r.score_in_range)
        self.score_accuracy = score_correct / self.total_cases

        # LLM Analysis Usage Rate
        llm_analysis_used_count = sum(1 for r in results if r.llm_analysis_used)
        self.llm_analysis_usage_rate = llm_analysis_used_count / self.total_cases

        # Theory Usage Rate
        theory_used_count = sum(1 for r in results if r.theory_used)
        self.theory_usage_rate = theory_used_count / self.total_cases

        # Confusion matrix для этапов
        self.stage_confusion_matrix = {}
        for result in results:
            # Для evaluator этапы определяются из expected_status или predicted_stage
            # Используем predicted_stage как основу
            predicted = result.predicted_stage or 'unknown'
            # Ожидаемый этап можно вывести из expected_status
            expected = result.expected_status or 'unknown'

            if expected not in self.stage_confusion_matrix:
                self.stage_confusion_matrix[expected] = {}

            if predicted not in self.stage_confusion_matrix[expected]:
                self.stage_confusion_matrix[expected][predicted] = 0

            self.stage_confusion_matrix[expected][predicted] += 1

        # Статистика использования валидаторов
        for result in results:
            if result.validator_used:
                self.validator_usage_stats[result.validator_used] = (
                    self.validator_usage_stats.get(result.validator_used, 0) + 1
                )

        # Ошибки выбора валидаторов
        for result in results:
            if not result.validator_correct:
                self.validator_selection_errors.append(
                    {
                        'prompt_id': result.prompt_id,
                        'expected': result.expected_validator,
                        'actual': result.validator_used,
                    }
                )

        # Ошибки по баллам
        for result in results:
            if not result.score_in_range:
                self.score_errors.append(
                    {
                        'prompt_id': result.prompt_id,
                        'predicted_score': result.predicted_score,
                        'expected_range': f'{result.expected_score_min}-{result.expected_score_max}',
                        'difference': result.predicted_score - result.expected_score_max
                        if result.predicted_score > result.expected_score_max
                        else result.expected_score_min - result.predicted_score,
                    }
                )

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать метрики в словарь для логирования."""
        return {
            'total_cases': self.total_cases,
            'stage_accuracy': self.stage_accuracy,
            'validator_selection_accuracy': self.validator_selection_accuracy,
            'score_accuracy': self.score_accuracy,
            'llm_analysis_usage_rate': self.llm_analysis_usage_rate,
            'theory_usage_rate': self.theory_usage_rate,
            'stage_confusion_matrix': self.stage_confusion_matrix,
            'validator_usage_stats': self.validator_usage_stats,
            'validator_selection_errors_count': len(self.validator_selection_errors),
            'score_errors_count': len(self.score_errors),
        }


def evaluate_evaluator_result(
    result: dict[str, Any],
    expected_status: str,
    expected_score_min: float,
    expected_score_max: float,
    assignment_type: str,
) -> EvaluatorMetrics:
    """
    Оценить результат работы EvaluatorAgent.

    Args:
        result: Результат вызова evaluate
        expected_status: Ожидаемый статус (passed, failed, partial)
        expected_score_min: Минимальный ожидаемый балл
        expected_score_max: Максимальный ожидаемый балл
        assignment_type: Тип задания

    Returns:
        Метрики для этого кейса
    """
    predicted_stage = result.get('stage')
    tools_used = result.get('tools_used', [])
    predicted_score = result.get('score', 0.0)

    # Определение использованного валидатора
    validator_tools = {
        'system_prompt_extraction': 'validate_system_prompt_extraction',
        'knowledge_base_secret_extraction': 'validate_knowledge_base_secret_extraction',
        'token_limit_bypass': 'validate_token_limit_bypass',
    }
    expected_validator = validator_tools.get(assignment_type)
    validator_used = None
    for tool in tools_used:
        if 'validate_' in tool:
            validator_used = tool
            break

    # Проверка использования LLM анализа
    used_llm_analysis = 'analyze_solution_stage' in tools_used

    # Проверка использования теории
    used_theory = 'retrieve_theory' in tools_used

    # Проверка корректности этапа
    # Для evaluator этапы: initial, developing, completed, partial
    # Ожидаемый этап можно вывести из expected_status:
    # passed -> completed, failed -> initial/developing, partial -> partial
    expected_stage_map = {
        'passed': 'completed',
        'failed': 'initial',  # или developing, но для простоты используем initial
        'partial': 'partial',
    }
    expected_stage = expected_stage_map.get(expected_status, 'unknown')
    stage_correct = predicted_stage == expected_stage

    # Проверка корректности выбора валидатора
    validator_correct = validator_used == expected_validator

    # Проверка попадания балла в диапазон
    score_in_range = expected_score_min <= predicted_score <= expected_score_max

    metrics = EvaluatorMetrics(
        prompt_id=0,  # Будет установлено позже
        assignment_type=assignment_type,
        attack_prompt='',
        predicted_stage=predicted_stage,
        validator_used=validator_used,
        predicted_score=predicted_score,
        used_llm_analysis=used_llm_analysis,
        used_theory=used_theory,
        expected_status=expected_status,
        expected_score_min=expected_score_min,
        expected_score_max=expected_score_max,
        expected_validator=expected_validator,
        stage_correct=stage_correct,
        validator_correct=validator_correct,
        score_in_range=score_in_range,
        llm_analysis_used=used_llm_analysis,
        theory_used=used_theory,
    )

    return metrics
