from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttackSessionBase(BaseModel):
    user_id: UUID
    task_id: UUID


class AttackSessionCreate(AttackSessionBase):
    template_name: str = 'agentic_flow'


class AttackSession(AttackSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    progress_id: UUID
    langflow_flow_id: str
    langflow_session_id: str | None
    template_name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class AttackChatMessageCreate(BaseModel):
    content: str


class AttackChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime


class AttackChatResponse(BaseModel):
    user_message: AttackChatMessage
    assistant_message: AttackChatMessage


class EvaluationCriterion(BaseModel):
    """Single evaluation criterion."""

    name: str
    score: float
    max_score: float
    feedback: str


class AttackEvaluationResponse(BaseModel):
    """Response from attack session evaluation."""

    success: bool
    score: float
    max_score: float
    percentage: float
    feedback: str
    criteria: list[EvaluationCriterion] = []
    stage: str | None = None
    recommendations: list[str] = []
    conversation_length: int = 0
