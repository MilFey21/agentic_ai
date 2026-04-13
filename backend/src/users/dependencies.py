from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.users import service
from src.users.config import auth_settings
from src.users.schemas import UserWithRoles


_unauthorized_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Not authenticated',
    headers={'WWW-Authenticate': 'Bearer'},
)


http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    exp: datetime


def create_access_token(user_id: UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=auth_settings.JWT_EXPIRE_MINUTES)
    payload = {
        'sub': str(user_id),
        'exp': expire,
    }
    return jwt.encode(payload, auth_settings.JWT_SECRET, algorithm=auth_settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(
            token,
            auth_settings.JWT_SECRET,
            algorithms=[auth_settings.JWT_ALGORITHM],
        )
        return TokenPayload(sub=payload['sub'], exp=payload['exp'])
    except (jwt.PyJWTError, KeyError):
        return None


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> UUID:
    if not credentials:
        raise _unauthorized_exception

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise _unauthorized_exception

    return UUID(payload.sub)


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserWithRoles:
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise _unauthorized_exception
    return user


async def valid_user_id(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserWithRoles:
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )
    return user
