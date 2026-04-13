from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.roles.schemas import Role
from src.users.models import UserRole


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role_id: UUID
    username: str
    email: str
    langflow_user_id: str | None = None
    langflow_folder_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class UserWithRole(User):
    role: Role


class UserWithRoles(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    roles: list[UserRole]
    langflow_user_id: str | None = None
    langflow_folder_id: str | None = None
    langflow_api_key: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    roles: list[UserRole]
    langflow_user_id: str | None = None
    langflow_folder_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_domain(cls, user: UserWithRoles) -> 'UserResponse':
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=user.roles,
            langflow_user_id=user.langflow_user_id,
            langflow_folder_id=user.langflow_folder_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )


class LoginRequest(BaseModel):
    user_id: UUID


class LoginCredentials(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
