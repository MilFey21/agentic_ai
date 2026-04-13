from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.users import service
from src.users.dependencies import create_access_token, get_current_user
from src.users.schemas import LoginCredentials, TokenResponse, UserCreate, UserResponse, UserWithRole, UserWithRoles


router = APIRouter(tags=['Users'])


@router.post(
    '/register',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Регистрация нового пользователя',
    responses={
        status.HTTP_409_CONFLICT: {
            'description': 'Пользователь с таким email или username уже существует',
        },
    },
)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    existing_by_email = await service.get_user_by_email(db, request.email)
    if existing_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='User with this email already exists',
        )

    existing_by_username = await service.get_user_by_username(db, request.username)
    if existing_by_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='User with this username already exists',
        )

    user = await service.create_user(
        db,
        username=request.username,
        email=request.email,
        password=request.password,
    )

    updated_user = await service.provision_langflow_user(db, user, request.password)
    if updated_user:
        user = updated_user

    return UserResponse.from_domain(user)


@router.get(
    '/me',
    response_model=UserResponse,
    summary='Получить текущего пользователя',
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'Не аутентифицирован',
        },
    },
)
async def get_me(
    current_user: UserWithRoles = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.from_domain(current_user)


@router.post(
    '/login',
    response_model=TokenResponse,
    summary='Вход в систему (по username/password)',
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'Неверный логин или пароль',
        },
    },
)
async def login(
    request: LoginCredentials,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await service.authenticate_user(
        db,
        username=request.username,
        password=request.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid username or password',
        )

    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token)


@router.post(
    '/users/{user_id}/provision-langflow',
    response_model=UserResponse,
    summary='Провизионить пользователя в LangFlow',
    responses={
        status.HTTP_404_NOT_FOUND: {'description': 'Пользователь не найден'},
    },
)
async def provision_langflow(
    user_id: str,
    password: str = 'demo123',
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    from uuid import UUID

    user = await service.get_user_by_id(db, UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    updated_user = await service.provision_langflow_user(db, user, password)
    if updated_user:
        return UserResponse.from_domain(updated_user)
    return UserResponse.from_domain(user)


@router.get(
    '/users',
    response_model=list[UserWithRole],
    summary='Получить список пользователей',
)
async def get_users(
    db: AsyncSession = Depends(get_db),
) -> list[UserWithRole]:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.roles import service as role_service
    from src.users.models import User

    query = (
        select(User).where(User.deleted_at.is_(None)).options(selectinload(User.role)).order_by(User.created_at.desc())
    )
    result = await db.execute(query)
    users = result.scalars().all()

    from src.roles.schemas import Role as RoleSchema

    user_list = []
    for user in users:
        role = await role_service.get_role_by_id(db, user.role_id)
        if role:
            user_list.append(
                UserWithRole(
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
            )
    return user_list
