"""add todos and message_references, split embedding_jobs source

Revision ID: 315d72b8728f
Revises: 1aa05751cf06
Create Date: 2026-07-29 14:27:32.608266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '315d72b8728f'
down_revision: Union[str, Sequence[str], None] = '1aa05751cf06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- todos ---------------------------------------------------------
    op.create_table(
        'todos',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_todos_user_id'), 'todos', ['user_id'], unique=False)

    # --- embedding_jobs: diary_entry_id -> source_type/source_id -------
    op.add_column('embedding_jobs', sa.Column('source_type', sa.Text(), nullable=True))
    op.add_column('embedding_jobs', sa.Column('source_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_embedding_jobs_source_id'), 'embedding_jobs', ['source_id'], unique=False)

    op.execute("UPDATE embedding_jobs SET source_type = 'diary_entry', source_id = diary_entry_id")

    op.alter_column('embedding_jobs', 'source_type', nullable=False)
    op.alter_column('embedding_jobs', 'source_id', nullable=False)

    op.drop_index(op.f('ix_embedding_jobs_diary_entry_id'), table_name='embedding_jobs')
    op.drop_constraint('embedding_jobs_diary_entry_id_fkey', 'embedding_jobs', type_='foreignkey')
    op.drop_column('embedding_jobs', 'diary_entry_id')

    # --- message_references, backfilled from cited_diary_entry_ids -----
    op.create_table(
        'message_references',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_message_references_message_id'), 'message_references', ['message_id'], unique=False
    )
    op.create_index(
        op.f('ix_message_references_source_id'), 'message_references', ['source_id'], unique=False
    )

    op.execute(
        """
        INSERT INTO message_references (id, message_id, source_type, source_id)
        SELECT gen_random_uuid(), id, 'diary_entry', unnest(cited_diary_entry_ids)
        FROM messages
        WHERE cited_diary_entry_ids IS NOT NULL
        """
    )

    op.drop_column('messages', 'cited_diary_entry_ids')


def downgrade() -> None:
    """Downgrade schema."""
    # --- messages.cited_diary_entry_ids, backfilled from message_references
    op.add_column(
        'messages',
        sa.Column('cited_diary_entry_ids', postgresql.ARRAY(sa.UUID()), nullable=True),
    )
    op.execute(
        """
        UPDATE messages
        SET cited_diary_entry_ids = sub.ids
        FROM (
            SELECT message_id, array_agg(source_id) AS ids
            FROM message_references
            WHERE source_type = 'diary_entry'
            GROUP BY message_id
        ) AS sub
        WHERE messages.id = sub.message_id
        """
    )

    op.drop_index(op.f('ix_message_references_source_id'), table_name='message_references')
    op.drop_index(op.f('ix_message_references_message_id'), table_name='message_references')
    op.drop_table('message_references')

    # --- embedding_jobs: source_type/source_id -> diary_entry_id -------
    op.add_column('embedding_jobs', sa.Column('diary_entry_id', sa.UUID(), nullable=True))
    op.execute(
        "UPDATE embedding_jobs SET diary_entry_id = source_id WHERE source_type = 'diary_entry'"
    )
    op.alter_column('embedding_jobs', 'diary_entry_id', nullable=False)
    op.create_foreign_key(
        'embedding_jobs_diary_entry_id_fkey',
        'embedding_jobs',
        'diary_entries',
        ['diary_entry_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        op.f('ix_embedding_jobs_diary_entry_id'), 'embedding_jobs', ['diary_entry_id'], unique=False
    )

    op.drop_index(op.f('ix_embedding_jobs_source_id'), table_name='embedding_jobs')
    op.drop_column('embedding_jobs', 'source_id')
    op.drop_column('embedding_jobs', 'source_type')

    # --- todos -----------------------------------------------------------
    op.drop_index(op.f('ix_todos_user_id'), table_name='todos')
    op.drop_table('todos')
