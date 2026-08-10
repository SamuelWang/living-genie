"""add pending_action to conversations

Revision ID: eecfb6d8a415
Revises: 315d72b8728f
Create Date: 2026-08-10 15:39:16.194078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'eecfb6d8a415'
down_revision: Union[str, Sequence[str], None] = '315d72b8728f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'conversations', sa.Column('pending_action', postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('conversations', 'pending_action')
