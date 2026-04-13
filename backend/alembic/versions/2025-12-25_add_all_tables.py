"""add_all_tables

Revision ID: ffe2d17eee25
Revises: 3bc156a26cb9
Create Date: 2025-12-25 10:31:52.636946

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ffe2d17eee25'
down_revision: str | None = '3bc156a26cb9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create role table first (needed for user.role_id FK)
    op.create_table(
        'role',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('role_pkey')),
    )
    op.create_index(op.f('role_name_idx'), 'role', ['name'], unique=True)

    # Insert default role
    op.execute("INSERT INTO role (id, name, created_at) VALUES (gen_random_uuid(), 'student', now())")

    # Create flow table WITHOUT the FK to module (will add later)
    op.create_table(
        'flow',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('module_branch_id', sa.Uuid(), nullable=True),
        sa.Column('langflow_flow_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('flow_pkey')),
    )

    # Create module table with FK to flow (flow already exists)
    op.create_table(
        'module',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('flow_id', sa.Uuid(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['flow_id'], ['flow.id'], name=op.f('module_flow_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('module_pkey')),
    )

    # Now add FK from flow to module (module exists now)
    op.create_foreign_key(op.f('flow_module_branch_id_fkey'), 'flow', 'module', ['module_branch_id'], ['id'])

    # Create other tables
    op.create_table(
        'assistant_profile',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('module_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('capabilities_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['module.id'], name=op.f('assistant_profile_module_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('assistant_profile_pkey')),
    )
    op.create_table(
        'lesson',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['flow_id'], ['flow.id'], name=op.f('lesson_flow_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('lesson_pkey')),
    )
    op.create_table(
        'mission',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('module_id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['module.id'], name=op.f('mission_module_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('mission_pkey')),
    )
    op.create_table(
        'task',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('module_id', sa.Uuid(), nullable=False),
        sa.Column('flow_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('max_score', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('achievement_badge', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['flow_id'], ['flow.id'], name=op.f('task_flow_id_fkey')),
        sa.ForeignKeyConstraint(['module_id'], ['module.id'], name=op.f('task_module_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('task_pkey')),
    )
    op.create_table(
        'chat_session',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('module_id', sa.Uuid(), nullable=False),
        sa.Column('flow_id', sa.Uuid(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['flow_id'], ['flow.id'], name=op.f('chat_session_flow_id_fkey')),
        sa.ForeignKeyConstraint(['module_id'], ['module.id'], name=op.f('chat_session_module_id_fkey')),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('chat_session_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('chat_session_pkey')),
    )
    op.create_table(
        'user_task_progress',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('score', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], name=op.f('user_task_progress_task_id_fkey')),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('user_task_progress_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('user_task_progress_pkey')),
    )
    op.create_table(
        'message',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('chat_session_id', sa.Uuid(), nullable=False),
        sa.Column('sender_type', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['chat_session_id'], ['chat_session.id'], name=op.f('message_chat_session_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('message_pkey')),
    )

    # Add columns to user table - role_id initially nullable
    op.add_column('user', sa.Column('role_id', sa.Uuid(), nullable=True))
    op.add_column('user', sa.Column('langflow_folder_id', sa.String(length=255), nullable=True))

    # Set default role for existing users
    op.execute(
        'UPDATE "user" SET role_id = (SELECT id FROM role WHERE name = \'student\' LIMIT 1) WHERE role_id IS NULL'
    )

    # Now make role_id NOT NULL
    op.alter_column('user', 'role_id', nullable=False)

    op.create_foreign_key(op.f('user_role_id_fkey'), 'user', 'role', ['role_id'], ['id'])
    op.drop_column('user', 'langflow_project_id')


def downgrade() -> None:
    op.add_column('user', sa.Column('langflow_project_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.drop_constraint(op.f('user_role_id_fkey'), 'user', type_='foreignkey')
    op.drop_column('user', 'langflow_folder_id')
    op.drop_column('user', 'role_id')
    op.drop_table('message')
    op.drop_table('user_task_progress')
    op.drop_table('chat_session')
    op.drop_table('task')
    op.drop_table('mission')
    op.drop_table('lesson')
    op.drop_table('assistant_profile')
    op.drop_constraint(op.f('flow_module_branch_id_fkey'), 'flow', type_='foreignkey')
    op.drop_table('module')
    op.drop_table('flow')
    op.drop_index(op.f('role_name_idx'), table_name='role')
    op.drop_table('role')
