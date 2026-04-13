from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModuleBase(BaseModel):
    title: str = Field(min_length=1)
    description: str
    flow_id: UUID | None = None
    is_active: bool = True


class ModuleCreate(ModuleBase):
    pass


class ModuleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    flow_id: UUID | None = None
    is_active: bool | None = None


class Module(ModuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
