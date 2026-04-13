"""add_file_upload_fields_to_attack_session

Revision ID: b2c3d4e5f6a7
Revises: c1d2e3f4a5b6
Create Date: 2026-01-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'b1c2d3e4f5g6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add uploaded_file_path column for storing the path to uploaded file in LangFlow
    op.add_column(
        'attack_session',
        sa.Column('uploaded_file_path', sa.String(length=512), nullable=True),
    )
    # Add file_component_id column for storing the ID of the File component in the flow
    op.add_column(
        'attack_session',
        sa.Column('file_component_id', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('attack_session', 'file_component_id')
    op.drop_column('attack_session', 'uploaded_file_path')
