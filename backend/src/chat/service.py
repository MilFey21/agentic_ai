from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.models import ChatSession, Message
from src.chat.schemas import ChatSessionCreate, ChatSessionEnd, MessageCreate
from src.exceptions import NotFoundError


async def get_chat_session_by_id(db: AsyncSession, session_id: UUID) -> ChatSession | None:
    query = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.deleted_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_chat_sessions(
    db: AsyncSession,
    user_id: UUID,
    module_id: UUID | None = None,
    flow_id: UUID | None = None,
) -> list[ChatSession]:
    query = select(ChatSession).where(
        ChatSession.user_id == user_id,
        ChatSession.deleted_at.is_(None),
    )
    if module_id:
        query = query.where(ChatSession.module_id == module_id)
    if flow_id:
        query = query.where(ChatSession.flow_id == flow_id)
    query = query.order_by(ChatSession.started_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_active_chat_session(
    db: AsyncSession,
    user_id: UUID,
    module_id: UUID,
    flow_id: UUID | None = None,
) -> ChatSession | None:
    query = select(ChatSession).where(
        ChatSession.user_id == user_id,
        ChatSession.module_id == module_id,
        ChatSession.ended_at.is_(None),
        ChatSession.deleted_at.is_(None),
    )
    if flow_id:
        query = query.where(ChatSession.flow_id == flow_id)
    else:
        query = query.where(ChatSession.flow_id.is_(None))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_chat_session(
    db: AsyncSession,
    session_data: ChatSessionCreate,
) -> ChatSession:
    # Check if active session exists
    active_session = await get_active_chat_session(
        db,
        session_data.user_id,
        session_data.module_id,
        session_data.flow_id,
    )
    if active_session:
        return active_session

    session = ChatSession(**session_data.model_dump())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def end_chat_session(
    db: AsyncSession,
    session_id: UUID,
    end_data: ChatSessionEnd,
) -> ChatSession:
    query = (
        update(ChatSession)
        .where(
            ChatSession.id == session_id,
            ChatSession.deleted_at.is_(None),
        )
        .values(ended_at=end_data.ended_at)
        .returning(ChatSession)
    )
    result = await db.execute(query)
    await db.commit()
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError('ChatSession')
    return session


async def get_messages_by_session_id(
    db: AsyncSession,
    chat_session_id: UUID,
) -> list[Message]:
    query = select(Message).where(Message.chat_session_id == chat_session_id).order_by(Message.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_message(
    db: AsyncSession,
    message_data: MessageCreate,
) -> Message:
    message = Message(**message_data.model_dump())
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
