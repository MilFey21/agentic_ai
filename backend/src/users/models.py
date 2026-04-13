from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from src.models import Base


if TYPE_CHECKING:
    from src.roles.models import Role


class UserRole(StrEnum):
    ADMIN = 'admin'
    STUDENT = 'student'
    TEACHER = 'teacher'


class User(Base):
    __tablename__ = 'user'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    role_id: Mapped[UUID] = mapped_column(ForeignKey('role.id'))
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    roles: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)  # Legacy field, kept for compatibility
    langflow_user_id: Mapped[str | None] = mapped_column(String(255))
    langflow_folder_id: Mapped[str | None] = mapped_column(String(255))  # Renamed from langflow_project_id per OpenAPI
    langflow_api_key: Mapped[str | None] = mapped_column(String(255))  # API key for running flows

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationship
    role: Mapped['Role'] = Relationship(back_populates='users')
