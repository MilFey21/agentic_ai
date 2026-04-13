from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MissionBase(BaseModel):
    module_id: UUID
    code: str
    title: str
    description: str


class Mission(MissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
