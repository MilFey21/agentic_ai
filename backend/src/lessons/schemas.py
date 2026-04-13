from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LessonBase(BaseModel):
    flow_id: UUID
    type: str
    title: str


class Lesson(LessonBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
