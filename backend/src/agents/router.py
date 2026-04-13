"""
API router for agents (tutor and evaluator).
"""

import logging
import traceback
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.agents.instances import evaluator_agent, tutor_agent
from src.dependencies import get_db


# Setup logging
logger = logging.getLogger(__name__)


router = APIRouter(prefix='/agents', tags=['Agents'])


# --- Schemas ---


class TutorChatRequest(BaseModel):
    """Request for tutor chat."""

    task_id: str = Field(..., description='ID задания')
    task_type: str = Field(..., description='Тип задания (system_prompt_extraction, etc)')
    task_title: str = Field(..., description='Название задания')
    task_description: str = Field(..., description='Описание задания')
    message: str = Field(..., description='Сообщение студента')
    current_solution: str | None = Field(
        None, description='Текущее решение студента (deprecated, используй attack_session_id)'
    )
    attack_session_id: str | None = Field(None, description='ID attack session для получения истории диалога с ботом')
    chat_history: list[dict[str, str]] | None = Field(
        default_factory=list, description="История чата [{role: 'user'|'assistant', content: '...'}]"
    )


class TutorChatResponse(BaseModel):
    """Response from tutor chat."""

    response: str = Field(..., description='Ответ тьютора')
    help_type: str | None = Field(None, description='Тип помощи')
    stage: str | None = Field(None, description='Этап работы студента')
    tools_used: list[str] = Field(default_factory=list, description='Использованные инструменты')


class EvaluateTaskRequest(BaseModel):
    """Request for task evaluation."""

    task_id: str = Field(..., description='ID задания')
    task_type: str = Field(..., description='Тип задания')
    task_title: str = Field(..., description='Название задания')
    task_description: str = Field(..., description='Описание задания')
    max_score: float = Field(..., description='Максимальный балл')
    student_solution: str = Field(..., description='Решение студента (промпт атаки)')
    evaluation_id: str | None = Field(None, description='Уникальный ID оценки (для идемпотентности, §7.5)')
    apply_delay: bool = Field(False, description='Применить 30-секундную задержку перед оценкой (§3.3)')


class EvaluationCriterion(BaseModel):
    """Single evaluation criterion."""

    name: str
    score: float
    max_score: float
    feedback: str


class EvaluateTaskResponse(BaseModel):
    """Response from task evaluation."""

    success: bool = Field(..., description='Успешно ли выполнено задание')
    score: float = Field(..., description='Полученный балл')
    max_score: float = Field(..., description='Максимальный балл')
    percentage: float = Field(..., description='Процент выполнения')
    feedback: str = Field(..., description='Общая обратная связь')
    criteria: list[EvaluationCriterion] = Field(default_factory=list, description='Оценка по критериям')
    stage: str | None = Field(None, description='Этап работы студента')
    recommendations: list[str] = Field(default_factory=list, description='Рекомендации по улучшению')


class RecordFailedAttemptRequest(BaseModel):
    """§3.2 — Уведомление о неудачной попытке атаки (Programmatic Validator → Tutor Agent)."""

    session_id: str = Field(..., description='ID tutor-сессии студента')


# --- Endpoints ---


async def _get_attack_dialog_from_langflow(
    db: AsyncSession,
    attack_session_id: str,
    max_length: int = 1000,
) -> str:
    """Get dialog history from LangFlow for an attack session.

    Args:
        db: Database session
        attack_session_id: Attack session UUID
        max_length: Maximum length of dialog string

    Returns:
        Formatted dialog string (truncated to max_length)
    """
    from src.attack_sessions import service as attack_service
    from src.langflow.client import LangflowClient
    from src.users import service as user_service

    try:
        # Get attack session
        session = await attack_service.get_attack_session_by_id(db, UUID(attack_session_id))
        if not session or not session.langflow_session_id:
            logger.warning(f'Attack session {attack_session_id} not found or has no langflow_session_id')
            return ''

        # Get user to get API key
        user = await user_service.get_user_by_id(db, session.user_id)
        if not user or not user.langflow_api_key:
            logger.warning(f'User for attack session {attack_session_id} not found or has no API key')
            return ''

        # Get chat history from LangFlow
        client = LangflowClient()
        messages = await client.get_chat_history(
            session_id=session.langflow_session_id,
            api_key=user.langflow_api_key,
            flow_id=session.langflow_flow_id,
            limit=50,
        )

        # Format as dialog
        dialog = client.format_chat_history_as_dialog(messages, max_length=max_length)
        logger.debug(f'Retrieved dialog for attack session {attack_session_id}: {len(dialog)} chars')
        return dialog

    except Exception as e:
        logger.warning(f'Failed to get attack dialog: {e}')
        return ''


@router.post(
    '/tutor/chat',
    response_model=TutorChatResponse,
    summary='Чат с тьютором',
    description='Отправить сообщение тьютору для получения помощи по заданию',
)
async def tutor_chat(
    request: TutorChatRequest,
    db: AsyncSession = Depends(get_db),
) -> TutorChatResponse:
    """Chat with tutor agent for help."""
    try:
        # Build assignment requirements from task info
        assignment_requirements = {
            'task_id': request.task_id,
            'title': request.task_title,
            'description': request.task_description,
            'type': request.task_type,
        }

        # Map task type to assignment type
        assignment_type_map = {
            'attack': 'system_prompt_extraction',  # Default attack type
            'system_prompt_extraction': 'system_prompt_extraction',
            'knowledge_base_secret_extraction': 'knowledge_base_secret_extraction',
            'token_limit_bypass': 'token_limit_bypass',
        }
        assignment_type = assignment_type_map.get(request.task_type, 'system_prompt_extraction')

        # Get current solution: prefer dialog from LangFlow attack session
        current_solution = request.current_solution
        if request.attack_session_id:
            # Fetch dialog from LangFlow and use it as current_solution
            dialog = await _get_attack_dialog_from_langflow(
                db,
                request.attack_session_id,
                max_length=1000,
            )
            if dialog:
                current_solution = f'История диалога студента с тестовым ботом:\n{dialog}'
                logger.info(f'Using LangFlow dialog as current_solution ({len(dialog)} chars)')

        # Get help from tutor (sync SDK call — offloaded to thread pool to avoid blocking event loop)
        result = await run_in_threadpool(
            tutor_agent.help_student,
            assignment_type=assignment_type,
            student_question=request.message,
            assignment_requirements=assignment_requirements,
            student_current_solution=current_solution,
            session_id=request.attack_session_id or request.task_id,
            chat_history=request.chat_history,
        )

        return TutorChatResponse(
            response=result.get('help_text', 'Извините, не удалось получить ответ.'),
            help_type=result.get('help_type'),
            stage=result.get('current_stage') or result.get('stage'),
            tools_used=result.get('tools_used', []),
        )

    except Exception as e:
        # Log the full error for debugging
        logger.error(f'Tutor chat error: {e!s}')
        logger.error(f'Full traceback: {traceback.format_exc()}')
        print(f'[TUTOR ERROR] {e!s}')
        print(f'[TUTOR TRACEBACK] {traceback.format_exc()}')

        return TutorChatResponse(
            response='Система временно недоступна, попробуйте позже.',
            help_type='error',
            stage=None,
            tools_used=[],
        )


@router.post(
    '/evaluator/evaluate',
    response_model=EvaluateTaskResponse,
    summary='Оценить задание',
    description='Отправить решение на оценку',
)
async def evaluate_task(request: EvaluateTaskRequest) -> EvaluateTaskResponse:
    """Evaluate student's task submission."""
    try:
        # Build assignment requirements from task info
        assignment_requirements = {
            'task_id': request.task_id,
            'title': request.task_title,
            'description': request.task_description[:500],
            'max_score': request.max_score,
        }

        # Map task type to assignment type
        assignment_type_map = {
            'attack': 'system_prompt_extraction',
            'system_prompt_extraction': 'system_prompt_extraction',
            'knowledge_base_secret_extraction': 'knowledge_base_secret_extraction',
            'token_limit_bypass': 'token_limit_bypass',
        }
        assignment_type = assignment_type_map.get(request.task_type, 'system_prompt_extraction')

        # Evaluate the solution (sync SDK + time.sleep — offloaded to thread pool)
        result = await run_in_threadpool(
            evaluator_agent.evaluate,
            assignment_type=assignment_type,
            student_solution=request.student_solution,
            assignment_requirements=assignment_requirements,
            evaluation_id=request.evaluation_id,   # §7.5 идемпотентность
            apply_delay=request.apply_delay,        # §3.3 30-секундная задержка
        )

        # Агент возвращает результат напрямую, не через validation_result
        score = result.get('score', 0.0)
        is_passed = result.get('is_passed', False)

        # Build criteria from criterion_details (weighted scores)
        criteria = []
        criterion_details = result.get('criterion_details', [])

        for detail in criterion_details:
            criteria.append(
                EvaluationCriterion(
                    name=detail.get('name', ''),
                    score=detail.get('weighted_score', 0.0),
                    max_score=detail.get('max_weighted_score', 0.0),
                    feedback=(
                        f'Получено {detail.get("weighted_score", 0):.1f} '
                        f'из {detail.get("max_weighted_score", 0):.1f} баллов'
                    ),
                )
            )

        # Build recommendations
        recommendations = result.get('improvement_suggestions', [])

        # Get feedback
        feedback = result.get('feedback', 'Оценка завершена.')

        # Calculate percentage
        percentage = (score / 100.0) * 100.0 if score > 0 else 0.0

        return EvaluateTaskResponse(
            success=is_passed,
            score=score,
            max_score=100.0,  # Агент всегда возвращает score из 100
            percentage=round(percentage, 1),
            feedback=feedback,
            criteria=criteria,
            stage=result.get('stage'),
            recommendations=recommendations[:5],  # Limit recommendations
        )

    except Exception as e:
        # Return error response
        return EvaluateTaskResponse(
            success=False,
            score=0,
            max_score=request.max_score,
            percentage=0,
            feedback=f'Произошла ошибка при оценке: {e!s}. Попробуйте еще раз.',
            criteria=[],
            stage=None,
            recommendations=['Проверьте формат ввода', 'Убедитесь, что решение не пустое'],
        )


@router.post(
    '/tutor/failed-attempt',
    summary='Уведомить тьютора о неудачной попытке',
    description='§3.2 — Programmatic Validator вызывает этот endpoint при неудачной атаке. '
                'Обновляет failed_attempts и адаптирует hint_depth в сессии студента.',
)
async def record_failed_attempt(request: RecordFailedAttemptRequest) -> dict:
    """§3.2 — Обновить счётчик неудачных попыток в tutor-сессии."""
    await run_in_threadpool(tutor_agent.record_failed_attempt, request.session_id)
    return {'status': 'ok', 'session_id': request.session_id}
