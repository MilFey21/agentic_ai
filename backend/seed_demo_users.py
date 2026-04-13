"""Create demo users for testing"""

import asyncio
import logging
from uuid import uuid4

from sqlalchemy import text

from src.database import get_session_maker, init_db
from src.langflow.client import LangflowClient
from src.langflow.exceptions import LangflowError, LangflowUserCreationError
from src.users.utils import hash_password


logger = logging.getLogger(__name__)

DEMO_PASSWORD = 'demo123'


async def provision_langflow_for_user(
    session,
    user_id: str,
    username: str,
    password: str,
) -> bool:
    """Provision LangFlow user, project and API key."""
    client = LangflowClient()
    langflow_user_id = None

    try:
        # Try to create user, but handle "already exists" gracefully
        try:
            langflow_user = await client.create_user(
                username=username,
                password=password,
            )
            langflow_user_id = langflow_user.id
        except LangflowUserCreationError as e:
            logger.warning('Could not create Langflow user (may already exist): %s', e)

        # Login to get access token
        user_access_token = await client.login_user(username, password)

        # Get user info if we don't have the ID
        if not langflow_user_id:
            langflow_user_id = await client.get_current_user_id(user_access_token)

        # Create project
        project_name = f"{username}'s Project"
        langflow_project = await client.create_project(
            name=project_name,
            description=f'Personal project for {username}',
            user_access_token=user_access_token,
        )

        # Create API key for running flows
        api_key_response = await client.create_api_key(
            name=f'{username}-flow-runner',
            user_access_token=user_access_token,
        )

        # Update user in database
        await session.execute(
            text("""
                UPDATE public.user 
                SET langflow_user_id = :langflow_user_id,
                    langflow_folder_id = :langflow_folder_id,
                    langflow_api_key = :langflow_api_key,
                    updated_at = now()
                WHERE id = :user_id
            """),
            {
                'user_id': user_id,
                'langflow_user_id': langflow_user_id,
                'langflow_folder_id': langflow_project.id,
                'langflow_api_key': api_key_response.api_key,
            },
        )

        print(f'  ✓ Provisioned LangFlow: user_id={langflow_user_id}, folder_id={langflow_project.id}')
        return True

    except LangflowError as e:
        print(f'  ✗ Failed to provision LangFlow: {e}')
        return False


async def seed_demo_users() -> None:
    """Create demo users if they don't exist"""

    # Initialize database connection
    await init_db()

    # Get session maker
    session_maker = get_session_maker()

    # Demo password for all users
    demo_password_hash = hash_password(DEMO_PASSWORD)

    async with session_maker() as session:
        # Check if users already exist
        result = await session.execute(text('SELECT COUNT(*) FROM public.user'))
        user_count = result.scalar()

        if user_count > 0:
            print(f'Users already exist ({user_count} users found). Skipping seed.')
            return

        # Get role IDs
        result = await session.execute(text('SELECT id, name FROM role'))
        roles = {row[1]: row[0] for row in result.fetchall()}

        if not roles:
            print('No roles found! Please run migrations first.')
            return

        # Create demo users
        demo_users = [
            {
                'id': str(uuid4()),
                'username': 'student_demo',
                'email': 'student@demo.com',
                'role_id': roles.get('student'),
                'hashed_password': demo_password_hash,
            },
            {
                'id': str(uuid4()),
                'username': 'admin_demo',
                'email': 'admin@demo.com',
                'role_id': roles.get('admin'),
                'hashed_password': demo_password_hash,
            },
        ]

        # Insert users and provision LangFlow
        for user in demo_users:
            if user['role_id']:
                await session.execute(
                    text("""
                        INSERT INTO public.user 
                        (id, username, email, role_id, hashed_password, roles, created_at)
                        VALUES 
                        (:id, :username, :email, :role_id, :hashed_password, ARRAY[]::varchar[], now())
                    """),
                    user,
                )
                print(f'Created user: {user["username"]} ({user["email"]})')

                # Provision LangFlow for this user
                await provision_langflow_for_user(
                    session,
                    user_id=user['id'],
                    username=user['username'],
                    password=DEMO_PASSWORD,
                )
            else:
                print(f'Skipping user {user["username"]} - role not found')

        await session.commit()
        print('\n✅ Demo users created successfully!')


if __name__ == '__main__':
    asyncio.run(seed_demo_users())
