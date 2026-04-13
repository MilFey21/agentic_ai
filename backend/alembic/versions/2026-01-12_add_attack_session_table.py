"""add_attack_session_table

Revision ID: a1b2c3d4e5f6
Revises: ffe2d17eee25
Create Date: 2026-01-12 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'ffe2d17eee25'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'attack_session',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('progress_id', sa.Uuid(), nullable=False),
        sa.Column('langflow_flow_id', sa.String(length=255), nullable=False),
        sa.Column('langflow_session_id', sa.String(length=255), nullable=True),
        sa.Column('template_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('attack_session_user_id_fkey')),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], name=op.f('attack_session_task_id_fkey')),
        sa.ForeignKeyConstraint(
            ['progress_id'], ['user_task_progress.id'], name=op.f('attack_session_progress_id_fkey')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('attack_session_pkey')),
    )
    # Create index for faster lookups by user and task
    op.create_index(
        op.f('attack_session_user_id_task_id_idx'),
        'attack_session',
        ['user_id', 'task_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('attack_session_user_id_task_id_idx'), table_name='attack_session')
    op.drop_table('attack_session')
