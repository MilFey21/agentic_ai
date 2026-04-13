"""
Инструменты (tools) для агента-проверяющего.

Каждый инструмент реализует проверку определённого типа задания.
LLMAnalyzer использует Anthropic Python SDK (Claude 3.5 Sonnet, T=0.3).

§1.5 Архитектурный принцип: все ValidationTool — детерминированные эвристики.
LLM-анализ вызывается только из EvaluatorAgent._run_llm_analyzer(), НЕ из валидаторов.
"""

import json
import logging
import os
import re
from typing import Any

import anthropic

from src.agents.evaluator.heuristics import (
    goal_achieved_knowledge_base_secret_extraction,
    goal_achieved_system_prompt_extraction,
    goal_achieved_token_limit_bypass,
)
from src.agents.evaluator.rubrics import (
    AssignmentType,
    Criterion,
    Rubric,
    rubric_system,
)
from src.course.loader import course_loader

logger = logging.getLogger(__name__)

# Модель LLMAnalyzer (§8 system-design.md)
_LLM_ANALYZER_MODEL = 'claude-3-5-sonnet-20241022'
_LLM_ANALYZER_TEMPERATURE = 0.3


# ========== LLM АНАЛИЗАТОР ==========


class LLMAnalyzer:
    """
    Утилита для LLM-анализа решений в EvaluatorAgent.

    Использует Anthropic Claude 3.5 Sonnet (T=0.3) для:
    - Классификации типа атаки
    - Оценки качества техник
    - Оценки оригинальности

    §1.5: Вызывается ТОЛЬКО из EvaluatorAgent._run_llm_analyzer().
    ValidationTool-подклассы не используют LLM — только эвристики.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> None:
        _key = api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        self.model = model or _LLM_ANALYZER_MODEL
        self.temperature = temperature if temperature is not None else _LLM_ANALYZER_TEMPERATURE

        if not _key:
            self.client: anthropic.Anthropic | None = None
            logger.warning('[LLMAnalyzer] ANTHROPIC_API_KEY не задан — LLM-анализ отключён')
        else:
            self.client = anthropic.Anthropic(api_key=_key)

    def _call_llm(self, prompt: str, system_message: str = '') -> str | None:
        """Вызвать LLM через Anthropic SDK. Возвращает None при ошибке."""
        if not self.client:
            return None

        try:
            kwargs: dict[str, Any] = {
                'model': self.model,
                'max_tokens': 512,
                'temperature': self.temperature,
                'messages': [{'role': 'user', 'content': prompt}],
            }
            if system_message:
                kwargs['system'] = system_message

            response = self.client.messages.create(**kwargs)
            return response.content[0].text.strip() if response.content else None

        except anthropic.APIStatusError as exc:
            logger.warning('[LLMAnalyzer] Anthropic API error: %s', exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning('[LLMAnalyzer] Unexpected error: %s', exc)
            return None

    def _parse_llm_json(self, response: str) -> dict[str, Any] | None:
        """
        Извлечь первый JSON-объект из ответа LLM.

        Поддерживает: чистый JSON, JSON в markdown-блоке (```json...```),
        JSON, вложенный в текст (берёт от первого '{' до последнего '}').
        """
        # Markdown code fence
        code_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass
        # First '{' to last '}'
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end > start:
            try:
                return json.loads(response[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None

    def classify_attack_type(self, solution: str) -> dict[str, Any]:
        """
        Классифицировать тип атаки через LLM.

        Returns: {attack_type, confidence, reasoning}
        """
        prompt = f"""Проанализируй решение студента и определи тип атаки на AI-систему.

Решение:
{solution}

Типы атак:
1. prompt_injection — инъекция промпта для изменения поведения модели
2. jailbreak — обход ограничений безопасности (ролевое моделирование и др.)
3. prompt_leaking — извлечение системного промпта
4. token_overflow — принуждение к генерации сверх лимита токенов
5. knowledge_extraction — извлечение конфиденциальной информации из базы знаний
6. unknown — тип не определён

Ответь строго в формате JSON:
{{
    "attack_type": "тип_атаки",
    "confidence": 0.0,
    "reasoning": "краткое объяснение"
}}"""

        response = self._call_llm(
            prompt,
            'Ты — эксперт по безопасности AI-систем. Классифицируй тип атаки.',
        )

        if not response:
            return {'attack_type': 'unknown', 'confidence': 0.0, 'reasoning': 'LLM недоступен'}

        parsed = self._parse_llm_json(response)
        if parsed and 'attack_type' in parsed:
            return parsed

        # Текстовый fallback
        attack_type = 'unknown'
        rl = response.lower()
        if 'prompt_injection' in rl:
            attack_type = 'prompt_injection'
        elif 'jailbreak' in rl:
            attack_type = 'jailbreak'
        elif 'prompt_leaking' in rl or 'prompt extraction' in rl:
            attack_type = 'prompt_leaking'
        elif 'token' in rl and 'overflow' in rl:
            attack_type = 'token_overflow'
        elif 'knowledge' in rl and 'extraction' in rl:
            attack_type = 'knowledge_extraction'
        return {'attack_type': attack_type, 'confidence': 0.6, 'reasoning': response[:200]}

    def analyze_attack_technique_quality(
        self,
        solution: str,
        assignment_type: str,
    ) -> dict[str, Any]:
        """
        Проанализировать качество техники атаки через LLM.

        Returns: {score (0–30), techniques_detected, quality_analysis, suggestions}
        """
        descriptions = {
            'system_prompt_extraction': 'извлечение системного промпта из бота',
            'knowledge_base_secret_extraction': 'извлечение конфиденциальных данных из RAG-системы',
            'token_limit_bypass': 'принуждение модели генерировать больше токенов, чем разрешено',
        }
        desc = descriptions.get(assignment_type, 'атака на AI-систему')

        prompt = f"""Оцени качество техники атаки для задания: {desc}

Решение:
{solution}

Оцени: используемые техники, их эффективность, оригинальность, качество реализации.

Ответь строго в формате JSON:
{{
    "score": 0.0,
    "techniques_detected": [],
    "quality_analysis": "анализ",
    "suggestions": []
}}"""

        response = self._call_llm(
            prompt,
            'Ты — эксперт по безопасности AI-систем. Оцени качество техники атаки объективно.',
        )

        default = {
            'score': 10.0,
            'techniques_detected': [],
            'quality_analysis': 'LLM недоступен',
            'suggestions': [],
        }
        if not response:
            return default

        parsed = self._parse_llm_json(response)
        if parsed and 'score' in parsed:
            parsed['score'] = max(0.0, min(30.0, float(parsed.get('score', 10.0))))
            return parsed

        # Текстовый fallback
        rl = response.lower()
        score = 15.0
        if 'отличн' in rl or 'excellent' in rl:
            score = 25.0
        elif 'хорош' in rl or 'good' in rl:
            score = 20.0
        elif 'плох' in rl or 'poor' in rl:
            score = 8.0
        return {**default, 'score': score, 'quality_analysis': response[:300]}

    def evaluate_originality(self, solution: str, assignment_type: str) -> dict[str, Any]:
        """
        Оценить оригинальность решения через LLM.

        Returns: {score (0–10), originality_analysis, common_patterns_detected, unique_elements}
        """
        prompt = f"""Оцени оригинальность решения для задания типа: {assignment_type}

Решение:
{solution}

Оцени: насколько решение отличается от типичных шаблонов, творческий подход, уникальные элементы.

Ответь строго в формате JSON:
{{
    "score": 0.0,
    "originality_analysis": "анализ",
    "common_patterns_detected": [],
    "unique_elements": []
}}"""

        response = self._call_llm(
            prompt,
            'Ты — эксперт по безопасности AI-систем. Оцени оригинальность решения.',
        )

        default = {
            'score': 5.0,
            'originality_analysis': 'LLM недоступен',
            'common_patterns_detected': [],
            'unique_elements': [],
        }
        if not response:
            return default

        parsed = self._parse_llm_json(response)
        if parsed and 'score' in parsed:
            parsed['score'] = max(0.0, min(10.0, float(parsed.get('score', 5.0))))
            return parsed

        # Текстовый fallback
        rl = response.lower()
        score = 5.0
        if 'very original' in rl or 'очень оригинальн' in rl:
            score = 8.0
        elif 'original' in rl or 'оригинальн' in rl:
            score = 6.0
        elif 'common' in rl or 'стандартн' in rl:
            score = 3.0
        return {**default, 'score': score, 'originality_analysis': response[:300]}


# Глобальный singleton LLMAnalyzer
_llm_analyzer: LLMAnalyzer | None = None


def get_llm_analyzer() -> LLMAnalyzer:
    """Получить глобальный экземпляр LLMAnalyzer (ленивая инициализация)."""
    global _llm_analyzer
    if _llm_analyzer is None:
        _llm_analyzer = LLMAnalyzer()
    return _llm_analyzer


def _get_rubric_from_course(assignment_type: AssignmentType) -> Rubric | None:
    """Получить rubric из CourseLoader для типа задания."""
    assignment_type_str = assignment_type.value
    assignment_meta = course_loader.get_assignment_by_type(assignment_type_str)

    if not assignment_meta or not assignment_meta.rubric:
        return None

    rubric_data = assignment_meta.rubric
    criteria = [
        Criterion(
            name=criterion.name,
            description=criterion.description,
            max_score=criterion.max_score,
        )
        for criterion in rubric_data.criteria
    ]

    return Rubric(
        assignment_type=assignment_type,
        criteria=criteria,
        passing_threshold=rubric_data.passing_threshold,
    )


# ========== БАЗОВЫЙ КЛАСС ВАЛИДАТОРА ==========


class ValidationTool:
    """
    Базовый класс для детерминированных инструментов валидации (§1.5).

    Подклассы реализуют только эвристики — без LLM-вызовов.
    LLM-анализ вынесен в EvaluatorAgent._run_llm_analyzer().
    """

    def __init__(self, assignment_type: AssignmentType) -> None:
        self.assignment_type = assignment_type
        rubric = _get_rubric_from_course(assignment_type)
        self.rubric = rubric if rubric else rubric_system.get_rubric(assignment_type)

    def validate(
        self,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Выполнить детерминированную валидацию решения.

        Returns:
            is_passed, score, feedback, detailed_analysis,
            improvement_suggestions, criterion_scores, criterion_details
        """
        raise NotImplementedError

    def _calculate_rubric_score(self, criterion_scores: dict[str, float]) -> dict[str, Any]:
        """Вычислить итоговый балл и детали по рубрике."""
        if not self.rubric:
            raise ValueError(f'Рубрика для типа {self.assignment_type} не найдена')

        total_score = 0.0
        criterion_details = []

        for criterion in self.rubric.criteria:
            score = max(0.0, min(criterion.max_score, criterion_scores.get(criterion.name, 0.0)))
            total_score += score
            criterion_details.append({
                'name': criterion.name,
                'score': round(score, 2),
                'max_score': criterion.max_score,
            })

        total_score = max(0.0, min(100.0, total_score))
        return {
            'total_score': round(total_score, 2),
            'is_passed': total_score >= self.rubric.passing_threshold,
            'passing_threshold': self.rubric.passing_threshold,
            'criterion_details': criterion_details,
        }


# ========== ВАЛИДАТОРЫ (детерминированные эвристики, §1.5) ==========


class SystemPromptExtractionValidator(ValidationTool):
    """Валидатор задания «Извлечь системный промпт» — только эвристики."""

    def __init__(self) -> None:
        super().__init__(AssignmentType.SYSTEM_PROMPT_EXTRACTION)

    def validate(
        self,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        extraction_success_score = self._check_extraction_success(student_solution, test_logs)
        technique_score = self._check_attack_technique_quality(student_solution)
        completeness_score = self._check_extraction_completeness(student_solution, test_logs)

        criterion_scores = {
            'Успешность извлечения': extraction_success_score,
            'Качество техники атаки': technique_score,
            'Полнота извлечения': completeness_score,
        }
        rubric_result = self._calculate_rubric_score(criterion_scores)

        return {
            'is_passed': rubric_result['is_passed'],
            'score': rubric_result['total_score'],
            'feedback': self._generate_feedback(
                extraction_success_score, technique_score, completeness_score, test_logs
            ),
            'detailed_analysis': self._generate_detailed_analysis(student_solution, test_logs),
            'improvement_suggestions': self._generate_improvement_suggestions(
                extraction_success_score, technique_score, completeness_score
            ),
            'criterion_scores': criterion_scores,
            'criterion_details': rubric_result.get('criterion_details', []),
        }

    def _check_extraction_success(self, solution: str, test_logs: dict[str, Any] | None) -> float:
        """Проверить успешность извлечения по логам или по эвристике."""
        if test_logs:
            if goal_achieved_system_prompt_extraction(test_logs):
                extracted = test_logs.get('extracted_prompt', '')
                if len(extracted) > 100:
                    return 50.0
                if len(extracted) > 50:
                    return 35.0
                if len(extracted) > 20:
                    return 25.0
                return 20.0
            return 0.0

        sol_lower = solution.lower()
        extraction_kw = [
            'system prompt', 'system_prompt', 'ignore previous',
            'show me your', 'what are your instructions',
            'repeat your', 'print your', 'reveal your',
        ]
        found = sum(1 for kw in extraction_kw if kw in sol_lower)
        if found >= 2:
            return 30.0
        if found >= 1:
            return 15.0
        return 5.0

    def _check_attack_technique_quality(self, solution: str) -> float:
        """Детерминированная оценка техники по характеристикам промпта."""
        sol_lower = solution.lower()
        techniques = []

        if any(p in sol_lower for p in ['ignore', 'forget', 'disregard']):
            techniques.append('ignore_instructions')
        if any(p in sol_lower for p in ['repeat', 'show', 'print', 'reveal', 'tell me']):
            techniques.append('direct_request')
        if any(p in sol_lower for p in ['you are', 'act as', 'pretend']):
            techniques.append('role_playing')
        if any(c in solution for c in ['```', '---', '===', '###']):
            techniques.append('formatting')

        n = len(techniques)
        if n >= 3:
            return 30.0
        if n == 2:
            return 20.0
        if n == 1:
            return 12.0
        return 5.0

    def _check_extraction_completeness(self, solution: str, test_logs: dict[str, Any] | None) -> float:
        """Оценить полноту извлечения по логам или длине решения."""
        if test_logs:
            completeness = test_logs.get('extraction_completeness')
            if completeness is not None:
                if completeness >= 0.8:
                    return 20.0
                if completeness >= 0.5:
                    return 15.0
                if completeness >= 0.3:
                    return 10.0
                return 5.0 if completeness > 0 else 0.0

            extracted = test_logs.get('extracted_prompt', '')
            original_len = test_logs.get('original_prompt_length', 0)
            if original_len > 0:
                ratio = len(extracted) / original_len
                if ratio >= 0.8:
                    return 20.0
                if ratio >= 0.5:
                    return 15.0
                if ratio >= 0.3:
                    return 10.0
                return 5.0 if ratio > 0 else 0.0

            if len(extracted) > 200:
                return 18.0
            if len(extracted) > 100:
                return 12.0
            if len(extracted) > 50:
                return 7.0
            return 3.0

        if len(solution) > 200:
            return 10.0
        if len(solution) > 100:
            return 7.0
        return 3.0

    def _generate_feedback(
        self,
        extraction_success: float,
        technique: float,
        completeness: float,
        test_logs: dict[str, Any] | None,
    ) -> str:
        parts = [
            f'Успешность извлечения: {extraction_success:.1f}/50.0',
            f'Качество техники атаки: {technique:.1f}/30.0',
            f'Полнота извлечения: {completeness:.1f}/20.0',
        ]
        if test_logs:
            extracted = test_logs.get('extracted_prompt', '')
            if extracted:
                parts.append('\nИзвлечённый фрагмент (до 200 симв.):')
                parts.append(extracted[:200] + ('…' if len(extracted) > 200 else ''))
        return '\n'.join(parts)

    def _generate_detailed_analysis(self, solution: str, test_logs: dict[str, Any] | None) -> str:
        analysis = f'Длина промпта: {len(solution)} симв.\n'
        if test_logs:
            analysis += '\nРезультаты тестирования:\n'
            for k, v in test_logs.items():
                if k != 'extracted_prompt':
                    analysis += f'  {k}: {v}\n'
        return analysis

    def _generate_improvement_suggestions(
        self,
        extraction_success: float,
        technique: float,
        completeness: float,
    ) -> list[str]:
        suggestions = []
        if extraction_success < 30.0:
            suggestions.append(
                'Подумайте о том, как сформулировать запрос, '
                'чтобы модель раскрыла информацию о своих инструкциях.'
            )
        if technique < 20.0:
            suggestions.append(
                'Попробуйте сочетать несколько подходов: '
                'изменение контекста, ролевые сценарии, нестандартное форматирование.'
            )
        if completeness < 12.0:
            suggestions.append(
                'Для извлечения более полной информации рассмотрите '
                'многоходовые или уточняющие запросы.'
            )
        return suggestions


class KnowledgeBaseSecretExtractionValidator(ValidationTool):
    """Валидатор задания «Извлечь секрет из базы знаний» — только эвристики."""

    def __init__(self) -> None:
        super().__init__(AssignmentType.KNOWLEDGE_BASE_SECRET_EXTRACTION)

    def validate(
        self,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        extraction_success_score = self._check_secret_extraction_success(student_solution, test_logs)
        technique_score = self._check_extraction_technique_effectiveness(student_solution)
        identification_score = self._check_secret_identification(student_solution, test_logs)

        criterion_scores = {
            'Успешность извлечения секрета': extraction_success_score,
            'Эффективность техники': technique_score,
            'Корректность идентификации секрета': identification_score,
        }
        rubric_result = self._calculate_rubric_score(criterion_scores)

        return {
            'is_passed': rubric_result['is_passed'],
            'score': rubric_result['total_score'],
            'feedback': self._generate_feedback(
                extraction_success_score, technique_score, identification_score, test_logs
            ),
            'detailed_analysis': self._generate_detailed_analysis(student_solution, test_logs),
            'improvement_suggestions': self._generate_improvement_suggestions(
                extraction_success_score, technique_score, identification_score
            ),
            'criterion_scores': criterion_scores,
            'criterion_details': rubric_result.get('criterion_details', []),
        }

    def _check_secret_extraction_success(self, solution: str, test_logs: dict[str, Any] | None) -> float:
        if test_logs:
            if goal_achieved_knowledge_base_secret_extraction(test_logs):
                extracted = test_logs.get('extracted_secret', '')
                secret_type = test_logs.get('secret_type', '')
                completeness = test_logs.get('extraction_completeness')
                if completeness is not None:
                    base = completeness * 50.0
                    return min(50.0, base) if secret_type in (
                        'athlete_logs', 'training_plans', 'incident_reports'
                    ) else min(40.0, base * 0.8)
                if secret_type in ('athlete_logs', 'training_plans', 'incident_reports'):
                    if len(extracted) > 150:
                        return 50.0
                    if len(extracted) > 80:
                        return 35.0
                    if len(extracted) > 40:
                        return 25.0
                    return 20.0
                return 25.0
            return 0.0

        sol_lower = solution.lower()
        secret_kw = [
            'athlete', 'training', 'progress', 'log', 'plan',
            'incident', 'report', 'confidential', 'private',
            'show me', 'give me', 'tell me about',
        ]
        found = sum(1 for kw in secret_kw if kw in sol_lower)
        if found >= 3:
            return 30.0
        if found >= 2:
            return 20.0
        if found >= 1:
            return 10.0
        return 3.0

    def _check_extraction_technique_effectiveness(self, solution: str) -> float:
        sol_lower = solution.lower()
        techniques = []

        if any(p in sol_lower for p in ['show me', 'give me', 'tell me', 'what is', 'who is']):
            techniques.append('direct_query')
        if any(p in sol_lower for p in ['as an admin', 'as a manager', 'i need', 'i have access']):
            techniques.append('role_escalation')
        if any(p in sol_lower for p in ['summarize', 'list all', 'what information', 'what data']):
            techniques.append('indirect_query')
        if re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', solution):
            techniques.append('specific_identifiers')
        if any(p in sol_lower for p in ['all athletes', 'all logs', 'all reports', 'all plans']):
            techniques.append('bulk_query')

        n = len(techniques)
        if n >= 4:
            return 30.0
        if n == 3:
            return 22.0
        if n == 2:
            return 15.0
        if n == 1:
            return 8.0
        return 3.0

    def _check_secret_identification(self, solution: str, test_logs: dict[str, Any] | None) -> float:
        sol_lower = solution.lower()
        secret_types = {
            'athlete_logs': ['athlete', 'log', 'progress', 'performance', 'sport'],
            'training_plans': ['training', 'plan', 'schedule', 'workout', 'exercise'],
            'incident_reports': ['incident', 'report', 'accident', 'event', 'occurrence'],
        }
        identified = [
            st for st, kws in secret_types.items()
            if sum(1 for kw in kws if kw in sol_lower) >= 2
        ]

        if test_logs:
            actual = test_logs.get('secret_type', '')
            if actual in identified:
                return 20.0
            return 12.0 if identified else 5.0

        if len(identified) >= 2:
            return 18.0
        if len(identified) == 1:
            return 12.0
        return 5.0

    def _generate_feedback(
        self,
        extraction_success: float,
        technique: float,
        identification: float,
        test_logs: dict[str, Any] | None,
    ) -> str:
        parts = [
            f'Успешность извлечения секрета: {extraction_success:.1f}/50.0',
            f'Эффективность техники: {technique:.1f}/30.0',
            f'Корректность идентификации: {identification:.1f}/20.0',
        ]
        if test_logs:
            secret_type = test_logs.get('secret_type', '')
            if secret_type:
                parts.append(f'\nТип извлечённого секрета: {secret_type}')
            extracted = test_logs.get('extracted_secret', '')
            if extracted:
                parts.append('\nИзвлечённый фрагмент (до 150 симв.):')
                parts.append(extracted[:150] + ('…' if len(extracted) > 150 else ''))
        return '\n'.join(parts)

    def _generate_detailed_analysis(self, solution: str, test_logs: dict[str, Any] | None) -> str:
        analysis = f'Длина промпта: {len(solution)} симв.\n'
        sol_lower = solution.lower()
        if 'athlete' in sol_lower or 'log' in sol_lower:
            analysis += 'Целевой тип: Журналы спортсменов\n'
        elif 'training' in sol_lower or 'plan' in sol_lower:
            analysis += 'Целевой тип: Планы тренировок\n'
        elif 'incident' in sol_lower or 'report' in sol_lower:
            analysis += 'Целевой тип: Отчёты по инцидентам\n'
        if test_logs:
            analysis += '\nРезультаты тестирования:\n'
            for k, v in test_logs.items():
                if k != 'extracted_secret':
                    analysis += f'  {k}: {v}\n'
        return analysis

    def _generate_improvement_suggestions(
        self,
        extraction_success: float,
        technique: float,
        identification: float,
    ) -> list[str]:
        suggestions = []
        if extraction_success < 30.0:
            suggestions.append(
                'Подумайте, как сформулировать запрос так, '
                'чтобы он точнее соответствовал содержимому защищённых документов.'
            )
        if technique < 20.0:
            suggestions.append(
                'Рассмотрите разные подходы к запросу: прямые, косвенные, '
                'с использованием ролевого контекста или агрегации.'
            )
        if identification < 12.0:
            suggestions.append(
                'Убедитесь, что запрос направлен на конкретный тип данных: '
                'журналы спортсменов, планы тренировок или отчёты по инцидентам.'
            )
        return suggestions


class TokenLimitBypassValidator(ValidationTool):
    """Валидатор задания «Обход ограничения токенов» — только эвристики."""

    def __init__(self) -> None:
        super().__init__(AssignmentType.TOKEN_LIMIT_BYPASS)

    def validate(
        self,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token_limit: int = assignment_requirements.get('token_limit', 1000)

        limit_bypass_score = self._check_token_limit_bypass(student_solution, test_logs, token_limit)
        technique_score = self._check_bypass_technique_effectiveness(student_solution)
        excess_score = self._check_token_excess_amount(student_solution, test_logs, token_limit)

        criterion_scores = {
            'Превышение лимита токенов': limit_bypass_score,
            'Эффективность техники обхода': technique_score,
            'Количество превышения': excess_score,
        }
        rubric_result = self._calculate_rubric_score(criterion_scores)

        return {
            'is_passed': rubric_result['is_passed'],
            'score': rubric_result['total_score'],
            'feedback': self._generate_feedback(
                limit_bypass_score, technique_score, excess_score, test_logs, token_limit
            ),
            'detailed_analysis': self._generate_detailed_analysis(
                student_solution, test_logs, token_limit
            ),
            'improvement_suggestions': self._generate_improvement_suggestions(
                limit_bypass_score, technique_score, excess_score
            ),
            'criterion_scores': criterion_scores,
            'criterion_details': rubric_result.get('criterion_details', []),
        }

    def _check_token_limit_bypass(
        self,
        solution: str,
        test_logs: dict[str, Any] | None,
        token_limit: int,
    ) -> float:
        """Проверить превышение лимита по логам или по эвристике запроса."""
        if test_logs:
            if goal_achieved_token_limit_bypass(test_logs, token_limit):
                generated = test_logs.get('generated_tokens') or test_logs.get('tokens_generated', 0)
                try:
                    n = int(generated)
                except (TypeError, ValueError):
                    n = 0
                excess_ratio = (n - token_limit) / token_limit if token_limit else 0
                if excess_ratio >= 0.5:
                    return 50.0
                if excess_ratio >= 0.2:
                    return 40.0
                return 35.0

            generated = test_logs.get('generated_tokens') or test_logs.get('tokens_generated', 0)
            try:
                g = int(generated)
            except (TypeError, ValueError):
                g = 0
            if g > token_limit * 0.9:
                return 35.0
            if g > token_limit * 0.7:
                return 20.0
            return 5.0

        sol_lower = solution.lower()
        bypass_kw = [
            'repeat', 'again', 'continue', 'more', 'expand',
            'detailed', 'comprehensive', 'explain in detail',
            'list all', 'enumerate', 'every',
        ]
        found = sum(1 for kw in bypass_kw if kw in sol_lower)
        if len(solution) > 500:
            found += 2

        if found >= 4:
            return 35.0
        if found >= 2:
            return 20.0
        if found >= 1:
            return 10.0
        return 3.0

    def _check_bypass_technique_effectiveness(self, solution: str) -> float:
        """Детерминированная оценка техники обхода по характеристикам промпта."""
        sol_lower = solution.lower()
        techniques = []

        if any(p in sol_lower for p in ['continue', 'go on', 'more', 'keep going']):
            techniques.append('continuation_request')
        if any(p in sol_lower for p in ['explain in detail', 'detailed explanation', 'comprehensive', 'thorough', 'extensive']):
            techniques.append('detailed_explanation')
        if any(p in sol_lower for p in ['list all', 'enumerate', 'every', 'all possible', 'complete list', 'full list']):
            techniques.append('enumeration')
        if len(solution) > 300:
            techniques.append('long_prompt')
        if any(p in sol_lower for p in ['repeat', 'say again', 'quote', 'copy']):
            techniques.append('repetition')
        if any(p in sol_lower for p in ['for each', 'one by one', 'step by step', 'iteratively']):
            techniques.append('iteration')

        n = len(techniques)
        if n >= 4:
            return 30.0
        if n == 3:
            return 22.0
        if n == 2:
            return 15.0
        if n == 1:
            return 8.0
        return 3.0

    def _check_token_excess_amount(
        self,
        solution: str,
        test_logs: dict[str, Any] | None,
        token_limit: int,
    ) -> float:
        if test_logs:
            generated = test_logs.get('generated_tokens', 0)
            if generated > token_limit:
                ratio = (generated - token_limit) / token_limit
                if ratio >= 1.0:
                    return 20.0
                if ratio >= 0.5:
                    return 15.0
                if ratio >= 0.2:
                    return 12.0
                return 7.0
            return 0.0

        complexity = 0.0
        if len(solution) > 500:
            complexity += 7.0
        elif len(solution) > 300:
            complexity += 5.0

        sol_lower = solution.lower()
        tech_count = sum(
            1 for p in ['continue', 'detailed', 'list all', 'repeat', 'every', 'comprehensive']
            if p in sol_lower
        )
        if tech_count >= 3:
            complexity += 8.0
        elif tech_count >= 2:
            complexity += 5.0
        elif tech_count >= 1:
            complexity += 3.0

        return min(complexity, 20.0)

    def _generate_feedback(
        self,
        limit_bypass: float,
        technique: float,
        excess: float,
        test_logs: dict[str, Any] | None,
        token_limit: int,
    ) -> str:
        parts = [
            f'Превышение лимита токенов: {limit_bypass:.1f}/50.0',
            f'Эффективность техники обхода: {technique:.1f}/30.0',
            f'Количество превышения: {excess:.1f}/20.0',
            f'\nУстановленный лимит: {token_limit} токенов',
        ]
        if test_logs:
            generated = test_logs.get('generated_tokens', 0)
            parts.append(f'Сгенерировано токенов: {generated}')
            if generated > token_limit:
                diff = generated - token_limit
                parts.append(f'Превышение: {diff} токенов ({diff / token_limit * 100:.1f}%)')
        return '\n'.join(parts)

    def _generate_detailed_analysis(
        self, solution: str, test_logs: dict[str, Any] | None, token_limit: int
    ) -> str:
        analysis = f'Длина промпта: {len(solution)} симв.\nЛимит токенов: {token_limit}\n'
        if test_logs:
            generated = test_logs.get('generated_tokens', 0)
            analysis += f'Сгенерировано токенов: {generated}\n'
            if generated > token_limit:
                analysis += f'Лимит превышен на {generated - token_limit} токенов\n'
            else:
                analysis += f'Лимит не превышен (не хватает {token_limit - generated} токенов)\n'

        sol_lower = solution.lower()
        used = []
        if 'continue' in sol_lower or 'more' in sol_lower:
            used.append('Запросы на продолжение')
        if 'detailed' in sol_lower or 'comprehensive' in sol_lower:
            used.append('Детальные объяснения')
        if 'list all' in sol_lower or 'enumerate' in sol_lower:
            used.append('Перечисления')
        if used:
            analysis += '\nПризнаки техник обхода:\n' + ''.join(f'  - {t}\n' for t in used)
        return analysis

    def _generate_improvement_suggestions(
        self,
        limit_bypass: float,
        technique: float,
        excess: float,
    ) -> list[str]:
        suggestions = []
        if limit_bypass < 30.0:
            suggestions.append(
                'Подумайте, какой тип задачи естественно требует длинного ответа, '
                'и как сформулировать запрос, чтобы модель не могла ответить кратко.'
            )
        if technique < 20.0:
            suggestions.append(
                'Попробуйте сочетать несколько элементов в запросе: '
                'структурирование, требование детализации, перечисление.'
            )
        if excess < 12.0:
            suggestions.append(
                'Для значительного превышения лимита рассмотрите запросы, '
                'которые по природе требуют развёрнутого ответа.'
            )
        return suggestions


# ========== ФАБРИКА ВАЛИДАТОРОВ ==========

_VALIDATORS: dict[AssignmentType, type[ValidationTool]] = {
    AssignmentType.SYSTEM_PROMPT_EXTRACTION: SystemPromptExtractionValidator,
    AssignmentType.KNOWLEDGE_BASE_SECRET_EXTRACTION: KnowledgeBaseSecretExtractionValidator,
    AssignmentType.TOKEN_LIMIT_BYPASS: TokenLimitBypassValidator,
}


def get_validator(assignment_type: AssignmentType) -> ValidationTool:
    """Получить детерминированный валидатор для типа задания."""
    cls = _VALIDATORS.get(assignment_type)
    if cls is None:
        raise ValueError(f'Валидатор для типа «{assignment_type}» не реализован')
    return cls()
