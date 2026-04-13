from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat import service
from src.chat.schemas import ChatSession, ChatSessionCreate, ChatSessionEnd, Message, MessageCreate
from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.schemas import Error


router = APIRouter(prefix='/chat_sessions', tags=['Chat'])


@router.get(
    '',
    response_model=list[ChatSession],
    summary='Получить чат-сессии пользователя',
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'user_id обязателен'},
    },
)
async def get_chat_sessions(
    user_id: UUID,
    module_id: UUID | None = None,
    flow_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ChatSession]:
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='user_id is required',
        )
    sessions = await service.get_chat_sessions(db, user_id, module_id, flow_id)
    return [ChatSession.model_validate(s) for s in sessions]


@router.post(
    '',
    response_model=ChatSession,
    status_code=status.HTTP_201_CREATED,
    summary='Создать чат-сессию',
    responses={
        status.HTTP_200_OK: {'model': ChatSession, 'description': 'Возвращена существующая активная сессия'},
    },
)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    # Check if active session exists first
    active_session = await service.get_active_chat_session(
        db,
        session_data.user_id,
        session_data.module_id,
        session_data.flow_id,
    )
    if active_session:
        return ChatSession.model_validate(active_session)

    session = await service.create_chat_session(db, session_data)
    return ChatSession.model_validate(session)


@router.patch(
    '/{id}',
    response_model=ChatSession,
    summary='Завершить чат-сессию',
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'Некорректный запрос'},
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Сессия не найдена'},
    },
)
async def end_chat_session(
    id: UUID,
    end_data: ChatSessionEnd,
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    try:
        session = await service.end_chat_session(db, id, end_data)
        return ChatSession.model_validate(session)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='ChatSession not found',
        )


# Messages router
messages_router = APIRouter(prefix='/messages', tags=['Chat'])


@messages_router.get(
    '',
    response_model=list[Message],
    summary='Получить сообщения чат-сессии',
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'chat_session_id обязателен'},
    },
)
async def get_messages(
    chat_session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[Message]:
    if not chat_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='chat_session_id is required',
        )
    messages = await service.get_messages_by_session_id(db, chat_session_id)
    return [Message.model_validate(m) for m in messages]


@messages_router.post(
    '',
    response_model=Message | list[Message],
    status_code=status.HTTP_201_CREATED,
    summary='Отправить сообщение',
)
async def send_message(
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
) -> Message | list[Message]:
    message = await service.create_message(db, message_data)
    result = Message.model_validate(message)

    # If sender_type is 'user', generate assistant response
    if message_data.sender_type == 'user':
        # TODO: Implement assistant response generation
        # For now, just return the user message
        return result

    return result
