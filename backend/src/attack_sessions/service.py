import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.attack_sessions.config import TEMPLATE_FILE_CONFIG, attack_sessions_settings
from src.attack_sessions.models import AttackSession, AttackSessionStatus
from src.attack_sessions.schemas import AttackSessionCreate
from src.exceptions import NotFoundError
from src.langflow.client import LangflowClient
from src.langflow.exceptions import LangflowError
from src.progress.models import ProgressStatus, UserTaskProgress
from src.tasks.models import Task
from src.users.models import User


logger = logging.getLogger(__name__)


async def get_attack_session_by_id(db: AsyncSession, session_id: UUID) -> AttackSession | None:
    query = select(AttackSession).where(
        AttackSession.id == session_id,
        AttackSession.deleted_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_active_attack_session(
    db: AsyncSession,
    user_id: UUID,
    task_id: UUID,
) -> AttackSession | None:
    query = select(AttackSession).where(
        AttackSession.user_id == user_id,
        AttackSession.task_id == task_id,
        AttackSession.status == AttackSessionStatus.ACTIVE,
        AttackSession.deleted_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_attack_sessions_by_user(
    db: AsyncSession,
    user_id: UUID,
    task_id: UUID | None = None,
) -> list[AttackSession]:
    query = select(AttackSession).where(
        AttackSession.user_id == user_id,
        AttackSession.deleted_at.is_(None),
    )
    if task_id:
        query = query.where(AttackSession.task_id == task_id)
    query = query.order_by(AttackSession.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


def get_template_path(template_name: str) -> Path:
    """Get the path to the template JSON file."""
    return attack_sessions_settings.ATTACK_TEMPLATES_DIR / f'{template_name}.json'


async def create_attack_session(
    db: AsyncSession,
    data: AttackSessionCreate,
    user_folder_id: str,
    user_api_key: str,
) -> AttackSession:
    """Create a new attack session with a LangFlow flow.

    Args:
        db: Database session
        data: Attack session creation data
        user_folder_id: User's LangFlow folder ID
        user_api_key: User's LangFlow API key (flow will be owned by user)
    """

    # Check if there's already an active session for this task
    existing = await get_active_attack_session(db, data.user_id, data.task_id)
    if existing:
        return existing

    # Get the user to access langflow credentials
    user_query = select(User).where(User.id == data.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError('User')

    # Get the task
    task_query = select(Task).where(Task.id == data.task_id)
    task_result = await db.execute(task_query)
    task = task_result.scalar_one_or_none()
    if not task:
        raise NotFoundError('Task')

    # Check/create progress record
    # Use user.id instead of data.user_id to ensure we use the correct ID from DB
    progress_query = select(UserTaskProgress).where(
        UserTaskProgress.user_id == user.id,
        UserTaskProgress.task_id == data.task_id,
        UserTaskProgress.deleted_at.is_(None),
    )
    progress_result = await db.execute(progress_query)
    progress = progress_result.scalar_one_or_none()

    if not progress:
        # Create progress record
        progress = UserTaskProgress(
            user_id=user.id,  # Use user.id from DB, not data.user_id
            task_id=data.task_id,
            status=ProgressStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
        )
        db.add(progress)
        await db.flush()
    elif progress.status == ProgressStatus.NOT_STARTED:
        # Update to in_progress
        progress.status = ProgressStatus.IN_PROGRESS
        progress.started_at = datetime.now(UTC)
        await db.flush()

    # Create flow in LangFlow using user's API key (flow will be owned by user)
    template_path = get_template_path(data.template_name)
    flow_name = f'{task.title} - {user.username} - {datetime.now(UTC).strftime("%Y%m%d_%H%M%S")}'

    # Check if this template requires file upload
    file_component_id = None
    file_to_upload = None
    if data.template_name in TEMPLATE_FILE_CONFIG:
        file_component_id, file_config_key = TEMPLATE_FILE_CONFIG[data.template_name]
        file_to_upload = getattr(attack_sessions_settings, file_config_key, None)
        logger.info(
            'Template %s requires file upload: component=%s, file=%s',
            data.template_name,
            file_component_id,
            file_to_upload,
        )

    client = LangflowClient()
    try:
        flow_response = await client.create_flow_from_template(
            template_path=template_path,
            flow_name=flow_name,
            folder_id=user_folder_id,
            user_api_key=user_api_key,
            file_component_id=file_component_id,
            file_to_upload=file_to_upload,
        )
    except LangflowError:
        logger.exception('Failed to create LangFlow flow for attack session')
        raise

    # Create attack session record
    session = AttackSession(
        user_id=data.user_id,
        task_id=data.task_id,
        progress_id=progress.id,
        langflow_flow_id=flow_response.id,
        template_name=data.template_name,
        status=AttackSessionStatus.ACTIVE,
        uploaded_file_path=flow_response.uploaded_file_path,
        file_component_id=flow_response.file_component_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(
        'Created attack session %s for user %s, task %s, langflow_flow_id=%s',
        session.id,
        data.user_id,
        data.task_id,
        flow_response.id,
    )

    return session


def build_file_tweaks(session: AttackSession) -> dict:
    """Build tweaks dict for file component if session has uploaded file."""
    tweaks: dict = {}
    if session.uploaded_file_path and session.file_component_id:
        tweaks[session.file_component_id] = {
            'path': session.uploaded_file_path,
        }
        logger.debug(
            'Adding file tweaks for session %s: component=%s, path=%s',
            session.id,
            session.file_component_id,
            session.uploaded_file_path,
        )
    return tweaks


async def send_message_to_flow(
    session: AttackSession,
    message: str,
    api_key: str,
) -> tuple[str, str | None]:
    """Send a message to the LangFlow flow and get the response.

    Returns:
        Tuple of (assistant_response, updated_session_id)
    """
    client = LangflowClient()

    # Build tweaks for file component if this flow uses file uploads
    tweaks = build_file_tweaks(session)

    response = await client.run_flow(
        flow_id=session.langflow_flow_id,
        input_value=message,
        session_id=session.langflow_session_id,
        api_key=api_key,
        tweaks=tweaks if tweaks else None,
    )

    assistant_message = response.get_message()
    new_session_id = response.session_id

    return assistant_message, new_session_id


async def update_langflow_session_id(
    db: AsyncSession,
    session_id: UUID,
    langflow_session_id: str,
) -> None:
    """Update the LangFlow session ID for an attack session."""
    query = update(AttackSession).where(AttackSession.id == session_id).values(langflow_session_id=langflow_session_id)
    await db.execute(query)
    await db.commit()


async def end_attack_session(
    db: AsyncSession,
    session_id: UUID,
    status: AttackSessionStatus = AttackSessionStatus.COMPLETED,
) -> AttackSession:
    """End an attack session."""
    query = (
        update(AttackSession)
        .where(
            AttackSession.id == session_id,
            AttackSession.deleted_at.is_(None),
        )
        .values(
            status=status,
            ended_at=datetime.now(UTC),
        )
        .returning(AttackSession)
    )
    result = await db.execute(query)
    await db.commit()
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError('AttackSession')
    return session
