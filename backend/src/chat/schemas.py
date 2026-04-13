from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.chat.models import SenderType


class ChatSessionBase(BaseModel):
    user_id: UUID
    module_id: UUID
    flow_id: UUID | None = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionEnd(BaseModel):
    ended_at: datetime


class ChatSession(ChatSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class MessageBase(BaseModel):
    chat_session_id: UUID
    sender_type: SenderType
    content: str


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
