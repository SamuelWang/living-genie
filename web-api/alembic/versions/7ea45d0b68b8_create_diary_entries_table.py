"""create users, diary_entries, and sessions tables

Revision ID: 7ea45d0b68b8
Revises:
Create Date: 2026-07-22 01:20:21.637974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ea45d0b68b8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('hashed_password', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table('diary_entries',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('entry_date', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diary_entries_user_id'), 'diary_entries', ['user_id'])

    op.create_table('sessions',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_diary_entries_user_id'), table_name='diary_entries')
    op.drop_table('diary_entries')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
