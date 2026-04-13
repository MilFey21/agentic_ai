"""Seed database with demo users, modules, and tasks from course assignments"""

import asyncio
import json
import logging
from pathlib import Path
from uuid import UUID, uuid4, uuid5

from sqlalchemy import text

from src.database import get_session_maker, init_db
from src.langflow.client import LangflowClient
from src.langflow.exceptions import LangflowError, LangflowUserCreationError
from src.users.utils import hash_password


logger = logging.getLogger(__name__)

DEMO_PASSWORD = 'demo123'

# UUID namespaces (must match src/modules/service.py and src/tasks/service.py)
NAMESPACE_MODULE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_TASK = UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')

# Paths
COURSE_DIR = Path(__file__).parent / 'course'
MODULES_DIR = COURSE_DIR / 'modules'
ASSIGNMENTS_DIR = COURSE_DIR / 'assignments'


def string_to_uuid(string_id: str, namespace: UUID) -> UUID:
    """Generate deterministic UUID from string ID (same as in service)."""
    return uuid5(namespace, string_id)


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


async def seed_roles(session) -> dict[str, str]:
    """Create roles if they don't exist and return role mapping."""
    roles = {}

    # Check if roles exist
    result = await session.execute(text('SELECT id, name FROM role'))
    existing_roles = {row[1]: str(row[0]) for row in result.fetchall()}

    # Create missing roles
    required_roles = ['student', 'admin', 'teacher']
    for role_name in required_roles:
        if role_name in existing_roles:
            roles[role_name] = existing_roles[role_name]
        else:
            role_id = str(uuid4())
            await session.execute(
                text("""
                    INSERT INTO role (id, name, created_at)
                    VALUES (:id, :name, now())
                """),
                {'id': role_id, 'name': role_name},
            )
            roles[role_name] = role_id
            print(f'Created role: {role_name}')

    if not any(role not in existing_roles for role in required_roles):
        print(f'Roles already exist: {list(existing_roles.keys())}')

    return roles


async def seed_users(session, roles: dict[str, str]) -> None:
    """Create demo users if they don't exist."""
    # Check if users already exist
    result = await session.execute(text('SELECT COUNT(*) FROM public.user'))
    user_count = result.scalar()

    if user_count > 0:
        print(f'Users already exist ({user_count} users found). Skipping user seed.')
        return

    demo_password_hash = hash_password(DEMO_PASSWORD)

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


async def seed_modules(session) -> dict[str, str]:
    """Create modules from course files if they don't exist."""
    module_ids = {}

    # Find all module JSON files
    module_files = list(MODULES_DIR.glob('*.json'))

    if not module_files:
        print(f'No module files found in {MODULES_DIR}')
        return module_ids

    for json_file in module_files:
        with open(json_file, encoding='utf-8') as f:
            config = json.load(f)

        # Generate deterministic UUID (same as in service)
        string_id = config['id']
        module_id = str(string_to_uuid(string_id, NAMESPACE_MODULE))

        # Check if module exists
        result = await session.execute(
            text('SELECT id FROM module WHERE id = :id'),
            {'id': module_id},
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f'Module already exists: {config["title"]} ({module_id})')
            module_ids[string_id] = module_id
            continue

        await session.execute(
            text("""
                INSERT INTO module (id, title, description, is_active, created_at)
                VALUES (:id, :title, :description, :is_active, now())
            """),
            {
                'id': module_id,
                'title': config['title'],
                'description': config['description'],
                'is_active': config.get('is_active', True),
            },
        )
        module_ids[string_id] = module_id
        print(f'Created module: {config["title"]} ({module_id})')

    return module_ids


async def seed_tasks(session, module_ids: dict[str, str]) -> None:
    """Create tasks from assignment files with deterministic UUIDs."""
    # Find all assignment JSON files
    assignment_files = list(ASSIGNMENTS_DIR.glob('*.json'))

    if not assignment_files:
        print(f'No assignment files found in {ASSIGNMENTS_DIR}')
        return

    for json_file in assignment_files:
        # Load JSON config
        with open(json_file, encoding='utf-8') as f:
            config = json.load(f)

        # Generate deterministic UUID (same as in service)
        string_id = config['id']
        task_id = str(string_to_uuid(string_id, NAMESPACE_TASK))

        # Get module UUID
        module_string_id = config['module_id']
        module_id = module_ids.get(module_string_id)
        if not module_id:
            module_id = str(string_to_uuid(module_string_id, NAMESPACE_MODULE))

        # Check if task exists
        result = await session.execute(
            text('SELECT id FROM task WHERE id = :id'),
            {'id': task_id},
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f'Task already exists: {config["title"]} ({task_id})')
            continue

        # Load MD description if exists
        md_file = json_file.with_suffix('.md')
        description = ''
        if md_file.exists():
            with open(md_file, encoding='utf-8') as f:
                description = f.read()
        else:
            # Use success criteria and learning objectives as description
            description = '## Цели обучения\n\n'
            for obj in config.get('learning_objectives', []):
                description += f'- {obj}\n'
            description += '\n## Критерии успеха\n\n'
            for criteria in config.get('success_criteria', []):
                description += f'- {criteria}\n'

        await session.execute(
            text("""
                INSERT INTO task (id, module_id, title, type, description, max_score, created_at)
                VALUES (:id, :module_id, :title, :type, :description, :max_score, now())
            """),
            {
                'id': task_id,
                'module_id': module_id,
                'title': config['title'],
                'type': config['type'],
                'description': description,
                'max_score': config.get('max_score', 100),
            },
        )
        print(f'Created task: {config["title"]} ({task_id})')


async def seed_database() -> None:
    """Main function to seed the database."""
    print('\n🌱 Seeding database...\n')

    # Initialize database connection
    await init_db()

    # Get session maker
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            # 1. Seed roles
            print('📋 Creating roles...')
            roles = await seed_roles(session)
            await session.commit()

            # 2. Seed users
            print('\n👤 Creating users...')
            await seed_users(session, roles)
            await session.commit()

            # 3. Seed modules from course files
            print('\n📦 Creating modules...')
            module_ids = await seed_modules(session)
            await session.commit()

            # 4. Seed tasks from assignments with deterministic UUIDs
            print('\n📝 Creating tasks from assignments...')
            await seed_tasks(session, module_ids)
            await session.commit()

            print('\n✅ Database seeding completed successfully!')

        except Exception as e:
            await session.rollback()
            print(f'\n❌ Error seeding database: {e}')
            raise


if __name__ == '__main__':
    asyncio.run(seed_database())
