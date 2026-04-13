from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class Task(Base):
    __tablename__ = 'task'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    module_id: Mapped[UUID] = mapped_column(ForeignKey('module.id'))
    flow_id: Mapped[UUID | None] = mapped_column(ForeignKey('flow.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    max_score: Mapped[float] = mapped_column(Numeric(10, 2))
    achievement_badge: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
