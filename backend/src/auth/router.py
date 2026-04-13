from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.roles import service as role_service
from src.schemas import Error
from src.users import service as user_service
from src.users.dependencies import get_current_user
from src.users.schemas import LoginRequest, UserWithRole


router = APIRouter(tags=['Auth'])


@router.get(
    '/me',
    response_model=UserWithRole,
    summary='Получить текущего пользователя',
    responses={
        status.HTTP_401_UNAUTHORIZED: {'model': Error, 'description': 'Не аутентифицирован'},
    },
)
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWithRole:
    # Get user with role
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.users.models import User

    query = select(User).where(User.id == current_user.id, User.deleted_at.is_(None)).options(selectinload(User.role))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found',
        )

    role = await role_service.get_role_by_id(db, user.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Role not found',
        )

    from src.roles.schemas import Role as RoleSchema

    return UserWithRole(
        id=user.id,
        role_id=user.role_id,
        username=user.username,
        email=user.email,
        langflow_user_id=user.langflow_user_id,
        langflow_folder_id=user.langflow_folder_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        deleted_at=user.deleted_at,
        role=RoleSchema.model_validate(role),
    )


@router.post(
    '/demo-login',
    response_model=UserWithRole,
    summary='Вход в систему (демо-режим по user_id)',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Пользователь не найден'},
    },
)
async def demo_login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> UserWithRole:
    user = await user_service.get_user_by_id(db, request.user_id)
    if not user:
        raise NotFoundError('User')

    # Get role
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.users.models import User

    query = select(User).where(User.id == request.user_id, User.deleted_at.is_(None)).options(selectinload(User.role))
    result = await db.execute(query)
    user_model = result.scalar_one_or_none()
    if not user_model:
        raise NotFoundError('User')

    role = await role_service.get_role_by_id(db, user_model.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Role not found',
        )

    from src.roles.schemas import Role as RoleSchema

    return UserWithRole(
        id=user_model.id,
        role_id=user_model.role_id,
        username=user_model.username,
        email=user_model.email,
        langflow_user_id=user_model.langflow_user_id,
        langflow_folder_id=user_model.langflow_folder_id,
        created_at=user_model.created_at,
        updated_at=user_model.updated_at,
        deleted_at=user_model.deleted_at,
        role=RoleSchema.model_validate(role),
    )
