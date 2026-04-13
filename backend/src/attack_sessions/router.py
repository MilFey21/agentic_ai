import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.agents.instances import evaluator_agent
from src.attack_sessions import service
from src.attack_sessions.models import AttackSessionStatus
from src.attack_sessions.schemas import (
    AttackChatMessage,
    AttackChatMessageCreate,
    AttackChatResponse,
    AttackEvaluationResponse,
    AttackSession,
    AttackSessionCreate,
    EvaluationCriterion,
)
from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.langflow.exceptions import LangflowError
from src.langflow.messages import format_conversation_for_evaluation, get_session_messages
from src.schemas import Error
from src.tasks import service as tasks_service
from src.users import service as users_service


logger = logging.getLogger(__name__)


router = APIRouter(prefix='/attack_sessions', tags=['Attack Sessions'])


@router.get(
    '',
    response_model=list[AttackSession],
    summary='Получить сессии атак пользователя',
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'user_id обязателен'},
    },
)
async def get_attack_sessions(
    user_id: UUID,
    task_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[AttackSession]:
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='user_id is required',
        )
    sessions = await service.get_attack_sessions_by_user(db, user_id, task_id)
    return [AttackSession.model_validate(s) for s in sessions]


@router.post(
    '',
    response_model=AttackSession,
    status_code=status.HTTP_201_CREATED,
    summary='Создать сессию атаки (создаёт flow в LangFlow)',
    responses={
        status.HTTP_200_OK: {'model': AttackSession, 'description': 'Возвращена существующая активная сессия'},
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'Нет LangFlow folder_id у пользователя'},
        status.HTTP_401_UNAUTHORIZED: {'model': Error, 'description': 'Ошибка аутентификации в LangFlow'},
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Пользователь не найден'},
    },
)
async def create_attack_session(
    data: AttackSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> AttackSession:
    # Get user from database
    user = await users_service.get_user_by_id(db, data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    # Check if user has LangFlow folder and API key
    if not user.langflow_folder_id or not user.langflow_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User does not have LangFlow credentials. Please provision LangFlow first.',
        )

    # Check for existing active session
    existing = await service.get_active_attack_session(db, data.user_id, data.task_id)
    if existing:
        return AttackSession.model_validate(existing)

    try:
        session = await service.create_attack_session(
            db,
            data,
            user_folder_id=user.langflow_folder_id,
            user_api_key=user.langflow_api_key,
        )
        return AttackSession.model_validate(session)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except LangflowError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to create LangFlow flow: {e}',
        )


@router.get(
    '/{session_id}',
    response_model=AttackSession,
    summary='Получить сессию атаки по ID',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Сессия не найдена'},
    },
)
async def get_attack_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AttackSession:
    session = await service.get_attack_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Attack session not found',
        )
    return AttackSession.model_validate(session)


@router.post(
    '/{session_id}/chat',
    response_model=AttackChatResponse,
    summary='Отправить сообщение в LangFlow чат',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Сессия не найдена'},
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'Сессия не активна или нет API key'},
    },
)
async def send_chat_message(
    session_id: UUID,
    message: AttackChatMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> AttackChatResponse:
    session = await service.get_attack_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Attack session not found',
        )

    # Check if session is active
    if session.status != AttackSessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Attack session is not active',
        )

    # Get user for LangFlow auth
    user = await users_service.get_user_by_id(db, session.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    # Check if user has API key
    if not user.langflow_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User does not have a LangFlow API key. Please re-provision.',
        )

    try:
        # Send message to LangFlow using API key
        assistant_response, new_session_id = await service.send_message_to_flow(
            session,
            message.content,
            api_key=user.langflow_api_key,
        )

        # Update session ID if it changed
        if new_session_id and new_session_id != session.langflow_session_id:
            await service.update_langflow_session_id(db, session_id, new_session_id)

        now = datetime.now(UTC)
        return AttackChatResponse(
            user_message=AttackChatMessage(
                role='user',
                content=message.content,
                timestamp=now,
            ),
            assistant_message=AttackChatMessage(
                role='assistant',
                content=assistant_response,
                timestamp=now,
            ),
        )
    except LangflowError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to communicate with LangFlow: {e}',
        )


@router.post(
    '/{session_id}/end',
    response_model=AttackSession,
    summary='Завершить сессию атаки',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Сессия не найдена'},
    },
)
async def end_attack_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AttackSession:
    session = await service.get_attack_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Attack session not found',
        )

    try:
        session = await service.end_attack_session(db, session_id)
        return AttackSession.model_validate(session)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Attack session not found',
        )


@router.post(
    '/{session_id}/evaluate',
    response_model=AttackEvaluationResponse,
    summary='Оценить диалог атаки',
    description='Получить диалог из LangFlow и отправить на оценку агенту',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Сессия не найдена'},
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'Нет сообщений для оценки'},
    },
)
async def evaluate_attack_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AttackEvaluationResponse:
    """
    Evaluate the attack session by fetching conversation from LangFlow DB
    and sending it to the EvaluatorAgent.
    """
    # Get the session
    session = await service.get_attack_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Attack session not found',
        )

    # Get the task info
    task = await tasks_service.get_task_by_id(db, session.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Task not found',
        )

    # Get langflow_session_id - use flow_id if session_id not set
    langflow_session_id = session.langflow_session_id or session.langflow_flow_id
    if not langflow_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No LangFlow session ID available',
        )

    try:
        # Fetch last N messages from LangFlow database (most recent are most relevant)
        messages = await get_session_messages(langflow_session_id, limit=50)

        if not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Нет сообщений для оценки. Сначала пообщайтесь с ботом.',
            )

        # Format conversation for evaluation
        conversation = format_conversation_for_evaluation(messages)

        logger.info(
            'Evaluating session %s with %d messages. Conversation:\n%s',
            session_id,
            len(messages),
            conversation[:500],
        )

        # Build assignment requirements
        assignment_requirements = {
            'task_id': str(task.id),
            'title': task.title,
            'description': task.description[:500] if task.description else '',
            'max_score': float(task.max_score) if task.max_score else 100.0,
        }

        # Map task type to assignment type
        assignment_type_map = {
            'attack': 'system_prompt_extraction',
            'system_prompt_extraction': 'system_prompt_extraction',
            'knowledge_base_secret_extraction': 'knowledge_base_secret_extraction',
            'token_limit_bypass': 'token_limit_bypass',
        }
        assignment_type = assignment_type_map.get(task.type, 'system_prompt_extraction')

        # Evaluate the conversation (sync SDK call — offloaded to thread pool)
        # §7.5 — передаём evaluation_id для идемпотентности: повторный клик «Оценить»
        # не вызовет второй LLM-вызов, вернётся кешированный результат
        result = await run_in_threadpool(
            evaluator_agent.evaluate,
            assignment_type=assignment_type,
            student_solution=conversation,
            assignment_requirements=assignment_requirements,
            evaluation_id=str(session_id),
        )

        # Log the result for debugging
        logger.info(
            'Evaluator result: score=%s, is_passed=%s, criterion_details=%s',
            result.get('score'),
            result.get('is_passed'),
            result.get('criterion_details'),
        )

        # Parse result
        score = result.get('score', 0.0)
        is_passed = result.get('is_passed', False)

        # Build criteria from criterion_details
        criteria = []
        for detail in result.get('criterion_details', []):
            criterion_score = detail.get('score', 0.0)
            criterion_max = detail.get('max_score', 0.0)
            criteria.append(
                EvaluationCriterion(
                    name=detail.get('name', ''),
                    score=criterion_score,
                    max_score=criterion_max,
                    feedback=(f'Получено {criterion_score:.1f} из {criterion_max:.1f} баллов'),
                )
            )

        percentage = (score / 100.0) * 100.0 if score > 0 else 0.0

        return AttackEvaluationResponse(
            success=is_passed,
            score=score,
            max_score=100.0,
            percentage=round(percentage, 1),
            feedback=result.get('feedback', 'Оценка завершена.'),
            criteria=criteria,
            stage=result.get('stage'),
            recommendations=result.get('improvement_suggestions', [])[:5],
            conversation_length=len(messages),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception('Failed to evaluate attack session: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Ошибка при оценке: {e!s}',
        )
