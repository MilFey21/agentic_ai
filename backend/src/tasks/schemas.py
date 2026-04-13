from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    module_id: UUID
    flow_id: UUID | None = None
    title: str
    type: str
    description: str
    max_score: float
    achievement_badge: str | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    description: str | None = None
    max_score: float | None = None
    achievement_badge: str | None = None


class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
