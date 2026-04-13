from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.progress.models import ProgressStatus


class UserTaskProgressBase(BaseModel):
    user_id: UUID
    task_id: UUID
    status: ProgressStatus
    score: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class UserTaskProgressCreate(UserTaskProgressBase):
    pass


class UserTaskProgressUpdate(BaseModel):
    status: ProgressStatus | None = None
    score: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class UserTaskProgress(UserTaskProgressBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
