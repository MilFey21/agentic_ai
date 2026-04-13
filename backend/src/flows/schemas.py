from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FlowBase(BaseModel):
    title: str
    description: str
    module_branch_id: UUID | None = None
    langflow_flow_id: str | None = None


class Flow(FlowBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
