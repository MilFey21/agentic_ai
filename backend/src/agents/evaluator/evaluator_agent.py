"""
Агент-проверяющий (Evaluator Agent) для курса LLM Security.

Архитектурные решения (см. system-design.md):
  - Прямое использование Anthropic Python SDK без фреймворков (§1.6).
  - Двухуровневая оценка (§1.5):
      1. ProgrammaticValidator — детерминированная проверка факта успешности
         из heuristics.py (без LLM).
      2. LLMAnalyzer — качественный анализ по 5-компонентной рубрике
         (Claude 3.5 Sonnet, T=0.3).
  - Контекстная изоляция (§1.1, §4): Evaluator НЕ имеет доступа к
    ключам tutor:session:*, работает только с финальной работой студента
    и эталонной рубрикой.
  - Pydantic-валидация ответа LLM + retry до 2 раз (§7.3).
  - Модель: Claude 3.5 Sonnet, температура 0.3 (§8).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Optional

import anthropic
from pydantic import BaseModel, ValidationError, field_validator

from src.agents.evaluator.heuristics import get_goal_achieved
from src.agents.evaluator.rubrics import AssignmentType, rubric_system
from src.agents.evaluator.tools import get_validator
from src.agents.theory_retriever import TheoryRetriever

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

MODEL_ANALYZE = 'claude-sonnet-4-6'   # T=0.3 — LLMAnalyzer (§8)
MAX_TOKENS_ANALYSIS = 1024
LLM_RETRY_LIMIT = 2                             # §7.3

# §3.3 — задержка после task.submitted (ожидание записи всех попыток)
EVALUATION_DELAY_SECONDS = 30
REDIS_EVAL_DEDUP_TTL = 86_400  # 24 ч для idempotency-ключей

# §9.1 — версионирование промпта (откат: смена переменной + перезапуск)
EVALUATOR_PROMPT_VERSION = os.environ.get('EVALUATOR_PROMPT_VERSION', '1.0')

# ---------------------------------------------------------------------------
# Pydantic-схема результата LLMAnalyzer
# ---------------------------------------------------------------------------


class CriterionScore(BaseModel):
    name: str
    score: float
    max_score: float
    feedback: str

    @field_validator('score', 'max_score')
    @classmethod
    def non_negative(cls, v: float) -> float:
        return max(0.0, v)


class LLMAnalysisResult(BaseModel):
    """Результат LLMAnalyzer. Проходит Pydantic-валидацию с retry (§7.3)."""

    pass_fail: bool
    total_score: float
    criterion_scores: list[CriterionScore]
    technique_description: str
    strengths: list[str]
    weaknesses: list[str]
    improvement_suggestions: list[str]
    overall_feedback: str
    evaluation_status: str = 'complete'   # 'complete' | 'partial'

    @field_validator('total_score')
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(100.0, v))


# ---------------------------------------------------------------------------
# Системный промпт Evaluator Agent
# ---------------------------------------------------------------------------

_EVALUATOR_SYSTEM_PROMPT = """\
Ты — Агент-Проверяющий курса LLM Security. Оцениваешь финальное решение студента \
по структурированной рубрике.

ПРАВИЛА ОЦЕНКИ:
• Анализируй только работу студента: его промпт/решение, использованные техники, результат.
• НЕ упоминай инструменты валидации, свои внутренние рассуждения или процесс проверки.
• Оценивай объективно, по критериям рубрики.
• Обращайся к студенту на «ты».
• Давай конструктивную обратную связь: сильные стороны, слабые места, рекомендации.

ФОРМАТ ОТВЕТА — строго валидный JSON (без markdown-обёрток):
{
    "pass_fail": true/false,
    "total_score": 0-100,
    "criterion_scores": [
        {"name": "...", "score": 0-100, "max_score": 100, "feedback": "..."},
        ...
    ],
    "technique_description": "Краткое описание техники студента",
    "strengths": ["...", "..."],
    "weaknesses": ["...", "..."],
    "improvement_suggestions": ["...", "..."],
    "overall_feedback": "Итоговая обратная связь на ты"
}
"""

# ---------------------------------------------------------------------------
# EvaluatorAgent
# ---------------------------------------------------------------------------


class EvaluatorAgent:
    """
    Агент-проверяющий на Anthropic Python SDK.

    ВАЖНО (§1.1, §4 — Контекстная изоляция):
        Этот агент НЕ имеет доступа к ключам tutor:session:*
        и НЕ импортирует SessionStore / TutorSessionState.
        Входные данные: final_solution + attempt_log + rubric.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        _key = api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        if not _key:
            raise ValueError(
                'ANTHROPIC_API_KEY должен быть задан через параметр или переменную окружения'
            )
        self._client = anthropic.Anthropic(api_key=_key)
        self._retriever = TheoryRetriever()
        # §7.5 — in-memory дедупликация: ключ → полный результат (fallback при недоступности Redis)
        self._result_cache: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        assignment_type: str,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: Optional[dict[str, Any]] = None,
        evaluation_id: Optional[str] = None,
        apply_delay: bool = False,
    ) -> dict[str, Any]:
        """
        §3.3 Двухуровневая оценка финального решения студента.

        Шаги:
            0. Идемпотентность: если evaluation_id уже обработан — вернуть
               кешированный результат (§7.5).
            1. [Опционально] 30-секундная задержка — ожидание записи всех
               попыток (§3.3). Включается флагом apply_delay=True.
            2. ProgrammaticValidator — детерминированная проверка по логам (без LLM).
            3. LLMAnalyzer — качественный анализ + рубрика (Claude 3.5 Sonnet).
            4. Pydantic-валидация + retry.

        Args:
            assignment_type:         Тип задания.
            student_solution:        Финальный промпт/решение студента.
            assignment_requirements: Мета-данные задания.
            test_logs:               Логи автоматических тестов (опционально).
            evaluation_id:           Уникальный ID события оценки для идемпотентности (§7.5).
            apply_delay:             Применить 30-секундную задержку перед оценкой (§3.3).

        Returns:
            dict с ключами: score, is_passed, feedback, criterion_details,
                            improvement_suggestions, stage, evaluation_status.
        """
        # ------------------------------------------------------------------
        # Шаг 0. §7.5 Идемпотентность — дедупликация по evaluation_id
        # ------------------------------------------------------------------
        if evaluation_id:
            cached = self._get_cached_result(evaluation_id)
            if cached is not None:
                logger.info(
                    '[EvaluatorAgent] Idempotent hit for evaluation_id=%s', evaluation_id
                )
                return cached

        # ------------------------------------------------------------------
        # §3.3 Задержка перед оценкой (ожидание записи всех попыток)
        # ------------------------------------------------------------------
        if apply_delay:
            logger.info(
                '[EvaluatorAgent] Waiting %ds before evaluation (§3.3)', EVALUATION_DELAY_SECONDS
            )
            time.sleep(EVALUATION_DELAY_SECONDS)
        # ------------------------------------------------------------------
        # Шаг 1. ProgrammaticValidator (детерминированный, §1.5)
        # ------------------------------------------------------------------
        programmatic_result = self._run_programmatic_validator(
            assignment_type, student_solution, assignment_requirements, test_logs
        )
        goal_achieved: Optional[bool] = programmatic_result.get('goal_achieved')

        # ------------------------------------------------------------------
        # Шаг 2. TheoryRetriever — получить контекст для LLMAnalyzer
        # ------------------------------------------------------------------
        theory = self._retriever.get_theory(
            query=assignment_type + ' ' + (student_solution[:200] if student_solution else ''),
            topic=assignment_type,
            depth='intermediate',
        )

        # ------------------------------------------------------------------
        # Шаг 3. LLMAnalyzer (Claude 3.5 Sonnet, T=0.3, §1.5)
        # ------------------------------------------------------------------
        rubric = rubric_system.get_rubric(AssignmentType(assignment_type))
        rubric_description = self._format_rubric(rubric) if rubric else 'Рубрика не определена.'

        llm_result = self._run_llm_analyzer(
            assignment_type=assignment_type,
            student_solution=student_solution,
            assignment_requirements=assignment_requirements,
            test_logs=test_logs,
            programmatic_passed=goal_achieved,
            rubric_description=rubric_description,
            theory_context=theory.content,
        )

        # ------------------------------------------------------------------
        # Шаг 4. Сборка итогового результата
        # ------------------------------------------------------------------
        result = self._build_result(
            llm_result=llm_result,
            programmatic_passed=goal_achieved,
            rubric=rubric,
        )

        # §7.5 — сохранить результат для идемпотентности
        if evaluation_id:
            self._cache_result(evaluation_id, result)

        return result

    # ------------------------------------------------------------------
    # §7.5 Идемпотентность
    # ------------------------------------------------------------------

    def _get_cached_result(self, evaluation_id: str) -> Optional[dict[str, Any]]:
        """§7.5 Вернуть ранее сохранённый результат, если он существует."""
        # Сначала пробуем Redis
        try:
            import redis  # type: ignore[import]
            host = os.environ.get('REDIS_HOST', 'localhost')
            port = int(os.environ.get('REDIS_PORT', 6379))
            r = redis.Redis(host=host, port=port, db=0, socket_connect_timeout=1)
            raw = r.get(f'eval:result:{evaluation_id}')
            if raw:
                return json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
        except Exception:  # noqa: BLE001
            pass

        # Fallback на in-memory — возвращаем полный кешированный результат
        return self._result_cache.get(evaluation_id)

    def _cache_result(self, evaluation_id: str, result: dict[str, Any]) -> None:
        """§7.5 Сохранить результат для идемпотентности (Redis + in-memory fallback)."""
        # In-memory: сохраняем полный результат для работы без Redis
        self._result_cache[evaluation_id] = result
        try:
            import redis  # type: ignore[import]
            host = os.environ.get('REDIS_HOST', 'localhost')
            port = int(os.environ.get('REDIS_PORT', 6379))
            r = redis.Redis(host=host, port=port, db=0, socket_connect_timeout=1)
            r.setex(
                f'eval:result:{evaluation_id}',
                REDIS_EVAL_DEDUP_TTL,
                json.dumps(result, ensure_ascii=False),
            )
        except Exception:  # noqa: BLE001
            pass  # Redis недоступен — idempotency через _result_cache

    # ------------------------------------------------------------------
    # Шаг 1: ProgrammaticValidator
    # ------------------------------------------------------------------

    def _run_programmatic_validator(
        self,
        assignment_type: str,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Детерминированная проверка факта успешности атаки (§1.5).

        Использует heuristics.py для проверки по логам,
        и инструменты-валидаторы для структурированной оценки.
        """
        # Проверка по логам (без LLM)
        goal_achieved = get_goal_achieved(assignment_type, test_logs, assignment_requirements)

        # Структурированная валидация через инструмент
        validator_result: dict[str, Any] = {}
        try:
            validator = get_validator(AssignmentType(assignment_type))
            validator_result = validator.validate(
                student_solution,
                assignment_requirements,
                test_logs,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning('[EvaluatorAgent] Validator error for %s: %s', assignment_type, exc)

        return {
            'goal_achieved': goal_achieved,
            **validator_result,
        }

    # ------------------------------------------------------------------
    # Шаг 3: LLMAnalyzer с Pydantic-валидацией
    # ------------------------------------------------------------------

    def _run_llm_analyzer(
        self,
        assignment_type: str,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: Optional[dict[str, Any]],
        programmatic_passed: Optional[bool],
        rubric_description: str,
        theory_context: str,
    ) -> Optional[LLMAnalysisResult]:
        """
        §7.3 LLMAnalyzer: retry до 2 раз при ошибке Pydantic-валидации.
        """
        user_content = self._build_analysis_prompt(
            assignment_type=assignment_type,
            student_solution=student_solution,
            assignment_requirements=assignment_requirements,
            test_logs=test_logs,
            programmatic_passed=programmatic_passed,
            rubric_description=rubric_description,
            theory_context=theory_context,
        )

        # §9.1 — логируем версию и sha256-хэш промпта для каждого LLM-вызова
        prompt_hash = hashlib.sha256(_EVALUATOR_SYSTEM_PROMPT.encode()).hexdigest()[:16]
        logger.info(
            '[EvaluatorAgent] LLM analyze prompt_version=%s prompt_hash=%s assignment_type=%s',
            EVALUATOR_PROMPT_VERSION, prompt_hash, assignment_type,
        )

        messages: list[dict[str, str]] = [{'role': 'user', 'content': user_content}]

        for attempt in range(LLM_RETRY_LIMIT + 1):
            try:
                resp = self._client.messages.create(
                    model=MODEL_ANALYZE,
                    max_tokens=MAX_TOKENS_ANALYSIS,
                    temperature=0.3,
                    system=_EVALUATOR_SYSTEM_PROMPT,
                    messages=messages,
                )
                raw_text = resp.content[0].text.strip() if resp.content else ''

                # Извлечь JSON из ответа
                parsed = self._extract_json(raw_text)
                if parsed is None:
                    raise ValueError('Не удалось извлечь JSON из ответа LLM')

                # Pydantic-валидация (§7.3)
                result = LLMAnalysisResult.model_validate(parsed)
                return result

            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                logger.warning(
                    '[EvaluatorAgent] LLMAnalyzer validation error attempt %d: %s',
                    attempt + 1, exc
                )
                if attempt < LLM_RETRY_LIMIT:
                    # Добавить напоминание схемы для следующего retry
                    messages.append({
                        'role': 'assistant',
                        'content': raw_text if 'raw_text' in dir() else '',
                    })
                    messages.append({
                        'role': 'user',
                        'content': (
                            'ОШИБКА ВАЛИДАЦИИ: твой ответ не прошёл JSON-схему. '
                            'Верни ТОЛЬКО валидный JSON-объект строго по схеме из системного промпта. '
                            f'Ошибка: {exc}'
                        ),
                    })
                else:
                    logger.error('[EvaluatorAgent] LLMAnalyzer exhausted retries')

            except anthropic.APIStatusError as exc:
                logger.error('[EvaluatorAgent] Anthropic API error: %s', exc)
                break
            except Exception as exc:  # noqa: BLE001
                logger.error('[EvaluatorAgent] Unexpected error in LLMAnalyzer: %s', exc)
                break

        return None

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _build_analysis_prompt(
        assignment_type: str,
        student_solution: str,
        assignment_requirements: dict[str, Any],
        test_logs: Optional[dict[str, Any]],
        programmatic_passed: Optional[bool],
        rubric_description: str,
        theory_context: str,
    ) -> str:
        goal_str = (
            'ДА — атака успешна' if programmatic_passed is True
            else 'НЕТ — атака не удалась' if programmatic_passed is False
            else 'НЕ ОПРЕДЕЛЕНО (нет логов)'
        )
        logs_str = json.dumps(test_logs, ensure_ascii=False, indent=2) if test_logs else 'нет данных'

        return f"""Оцени финальное решение студента по курсу LLM Security.

ТИП ЗАДАНИЯ: {assignment_type}
ОПИСАНИЕ ЗАДАНИЯ: {assignment_requirements.get('description', 'не указано')[:500]}

РЕШЕНИЕ СТУДЕНТА:
{student_solution[:2000] if student_solution else 'не предоставлено'}

РЕЗУЛЬТАТ АВТОТЕСТОВ (детерминированная проверка):
Цель достигнута: {goal_str}
Логи: {logs_str}

РУБРИКА ОЦЕНКИ:
{rubric_description}

ТЕОРЕТИЧЕСКИЙ КОНТЕКСТ:
{theory_context[:800] if theory_context else 'не доступен'}

Проведи качественный анализ решения студента и верни JSON строго по схеме."""

    @staticmethod
    def _format_rubric(rubric: Any) -> str:
        if rubric is None:
            return 'Рубрика не определена.'
        lines = [f'Порог прохождения: {rubric.passing_threshold}/100', '']
        for c in rubric.criteria:
            lines.append(f'• {c.name} (max {c.max_score}): {c.description}')
        return '\n'.join(lines)

    @staticmethod
    def _extract_json(text: str) -> Optional[dict[str, Any]]:
        """Извлечь JSON-объект из текста (может быть обёрнут в markdown)."""
        # Убрать ```json ... ``` обёртку
        clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
        # Найти первый JSON-объект
        m = re.search(r'\{[\s\S]*\}', clean)
        if not m:
            return None
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _build_result(
        llm_result: Optional[LLMAnalysisResult],
        programmatic_passed: Optional[bool],
        rubric: Any,
    ) -> dict[str, Any]:
        """Собрать итоговый результат из двух уровней оценки."""
        passing_threshold = rubric.passing_threshold if rubric else 60.0

        if llm_result is None:
            # §7.3 Частичный результат при исчерпании retry
            score = 50.0 if programmatic_passed else 20.0 if programmatic_passed is False else 0.0
            is_passed = bool(programmatic_passed) and score >= passing_threshold
            return {
                'score': score,
                'is_passed': is_passed,
                'feedback': 'Качественный анализ временно недоступен. Результат основан на автотестах.',
                'criterion_details': [],
                'improvement_suggestions': ['Повторите попытку позже'],
                'stage': 'completed',
                'evaluation_status': 'partial',
            }

        # Финальный pass/fail: детерминированный Validator имеет приоритет (§1.5)
        # LLM не может «убедить» систему в успехе атаки
        final_passed = llm_result.pass_fail
        if programmatic_passed is False:
            # Атака детерминированно не удалась — LLM не может это переопределить
            final_passed = False
        elif programmatic_passed is True and not llm_result.pass_fail:
            # Атака успешна по логам, но LLM считает иначе — доверяем логам
            final_passed = True

        # Пересчитать общий балл с учётом порога
        total = min(100.0, max(0.0, llm_result.total_score))

        criterion_details = [
            {
                'name': c.name,
                'score': c.score,
                'max_score': c.max_score,
                'weighted_score': c.score,
                'max_weighted_score': c.max_score,
                'feedback': c.feedback,
            }
            for c in llm_result.criterion_scores
        ]

        return {
            'score': round(total, 2),
            'is_passed': final_passed,
            'feedback': llm_result.overall_feedback,
            'criterion_details': criterion_details,
            'improvement_suggestions': llm_result.improvement_suggestions,
            'stage': 'completed',
            'evaluation_status': llm_result.evaluation_status,
            'technique_description': llm_result.technique_description,
            'strengths': llm_result.strengths,
            'weaknesses': llm_result.weaknesses,
        }
