"""add email verification and password reset support

Revision ID: b5c6ad17165d
Revises: eecfb6d8a415
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c6ad17165d'
down_revision: Union[str, Sequence[str], None] = 'eecfb6d8a415'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- users: email verification / locale / resend-cooldown timestamps ---
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'users', sa.Column('locale', sa.Text(), server_default='zh-Hant', nullable=False)
    )
    op.add_column(
        'users',
        sa.Column('last_verification_email_sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('last_password_reset_email_sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL")

    # --- email_tokens -----------------------------------------------------
    op.create_table(
        'email_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('code_hash', sa.Text(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_tokens_user_id'), 'email_tokens', ['user_id'], unique=False)
    op.create_index(
        'ix_email_tokens_user_id_purpose', 'email_tokens', ['user_id', 'purpose'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_email_tokens_user_id_purpose', table_name='email_tokens')
    op.drop_index(op.f('ix_email_tokens_user_id'), table_name='email_tokens')
    op.drop_table('email_tokens')

    op.drop_column('users', 'last_password_reset_email_sent_at')
    op.drop_column('users', 'last_verification_email_sent_at')
    op.drop_column('users', 'locale')
    op.drop_column('users', 'email_verified_at')
