import logging
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.langflow.client import LangflowClient
from src.langflow.exceptions import LangflowError
from src.users.models import User, UserRole
from src.users.schemas import UserWithRoles
from src.users.utils import hash_password, verify_password


logger = logging.getLogger(__name__)


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> UserWithRoles | None:
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return UserWithRoles.model_validate(user)


async def get_user_by_email(db: AsyncSession, email: str) -> UserWithRoles | None:
    query = select(User).where(User.email == email, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return UserWithRoles.model_validate(user)


async def get_user_by_username(db: AsyncSession, username: str) -> UserWithRoles | None:
    query = select(User).where(User.username == username, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return UserWithRoles.model_validate(user)


async def get_all_users(db: AsyncSession) -> list[UserWithRoles]:
    query = select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return [UserWithRoles.model_validate(user) for user in users]


async def create_user(
    db: AsyncSession,
    *,
    username: str,
    email: str,
    password: str,
    roles: list[UserRole] | None = None,
    role_id: UUID | None = None,
) -> UserWithRoles:
    from src.roles import service as role_service

    roles_values = [r.value for r in (roles or [UserRole.STUDENT])]

    # Get role_id: use provided, or get 'student' role by default
    if role_id is None:
        student_role = await role_service.get_role_by_name(db, 'student')
        if student_role:
            role_id = student_role.id
        else:
            # Fallback: get the first role available
            all_roles = await role_service.get_all_roles(db)
            if all_roles:
                role_id = all_roles[0].id
            else:
                raise ValueError('No roles found in database. Please create at least one role.')

    query = (
        insert(User)
        .values(
            id=uuid4(),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            roles=roles_values,
            role_id=role_id,
        )
        .returning(User)
    )

    result = await db.scalars(query)
    await db.commit()

    user = result.one()
    return UserWithRoles.model_validate(user)


async def authenticate_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
) -> UserWithRoles | None:
    query = select(User).where(User.username == username, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return UserWithRoles.model_validate(user)


async def update_langflow_ids(
    db: AsyncSession,
    user_id: UUID,
    *,
    langflow_user_id: str,
    langflow_folder_id: str,
    langflow_api_key: str | None = None,
) -> UserWithRoles:
    values = {
        'langflow_user_id': langflow_user_id,
        'langflow_folder_id': langflow_folder_id,
    }
    if langflow_api_key:
        values['langflow_api_key'] = langflow_api_key

    query = update(User).where(User.id == user_id).values(**values).returning(User)

    result = await db.execute(query)
    await db.commit()

    user = result.scalar_one()
    return UserWithRoles.model_validate(user)


async def provision_langflow_user(
    db: AsyncSession,
    user: UserWithRoles,
    password: str,
) -> UserWithRoles | None:
    from src.langflow.exceptions import LangflowUserCreationError

    client = LangflowClient()
    langflow_user_id = None

    try:
        # Try to create user, but handle "already exists" gracefully
        try:
            langflow_user = await client.create_user(
                username=user.username,
                password=password,
            )
            langflow_user_id = langflow_user.id
        except LangflowUserCreationError as e:
            # User might already exist, try to login
            logger.warning('Could not create Langflow user (may already exist): %s', e)

        # Login to get access token (works whether user was just created or already existed)
        user_access_token = await client.login_user(user.username, password)

        # Get user info if we don't have the ID
        if not langflow_user_id:
            # Use the token to get current user info
            langflow_user_id = await client.get_current_user_id(user_access_token)

        project_name = f"{user.username}'s Project"
        langflow_project = await client.create_project(
            name=project_name,
            description=f'Personal project for {user.username}',
            user_access_token=user_access_token,
        )

        # Create API key for running flows
        api_key_response = await client.create_api_key(
            name=f'{user.username}-flow-runner',
            user_access_token=user_access_token,
        )

        updated_user = await update_langflow_ids(
            db,
            user.id,
            langflow_user_id=langflow_user_id,
            langflow_folder_id=langflow_project.id,
            langflow_api_key=api_key_response.api_key,
        )

        logger.info(
            'Provisioned Langflow user and project for user %s: langflow_user_id=%s, langflow_folder_id=%s',
            user.id,
            langflow_user_id,
            langflow_project.id,
        )
    except LangflowError:
        logger.exception('Failed to provision Langflow user for %s', user.id)
        return None
    else:
        return updated_user
