from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class AttackSessionStatus(StrEnum):
    ACTIVE = 'active'
    COMPLETED = 'completed'
    FAILED = 'failed'


class AttackSession(Base):
    """Stores the connection between a user's task progress and a LangFlow flow instance."""

    __tablename__ = 'attack_session'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('user.id'))
    task_id: Mapped[UUID] = mapped_column(ForeignKey('task.id'))
    progress_id: Mapped[UUID] = mapped_column(ForeignKey('user_task_progress.id'))

    # LangFlow flow info
    langflow_flow_id: Mapped[str] = mapped_column(String(255))
    langflow_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Template used to create the flow
    template_name: Mapped[str] = mapped_column(String(255))

    # Uploaded file path for RAG flows (e.g., "flow_id/kitesurf_customers.csv")
    uploaded_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # File component ID in the flow (e.g., "File-3vcF4")
    file_component_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default=AttackSessionStatus.ACTIVE)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
