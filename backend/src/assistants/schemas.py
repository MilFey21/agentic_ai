from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssistantProfileBase(BaseModel):
    module_id: UUID
    name: str
    system_prompt: str
    capabilities_json: dict | None = None


class AssistantProfileCreate(AssistantProfileBase):
    pass


class AssistantProfileUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    capabilities_json: dict | None = None


class AssistantProfile(AssistantProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
