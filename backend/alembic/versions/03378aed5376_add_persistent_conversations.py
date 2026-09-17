"""add persistent conversations

Revision ID: 03378aed5376
Revises: fe6bf890d790
Create Date: 2026-09-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03378aed5376'
down_revision: Union[str, None] = 'fe6bf890d790'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: unlike op.add_column (see previous migrations), op.create_table
    # DOES auto-create a named enum used by its columns — so no explicit
    # Enum.create() here (an explicit create + table-create would raise
    # DuplicateObject).
    chat_role = sa.Enum('user', 'assistant', name='chat_role')

    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'patient_id',
            sa.Integer(),
            sa.ForeignKey('patients.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=300), server_default='گفتگوی جدید', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conversations_patient_id', 'conversations', ['patient_id'])

    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'conversation_id',
            sa.Integer(),
            sa.ForeignKey('conversations.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('role', chat_role, server_default='user', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conversation_messages_conversation_id', 'conversation_messages', ['conversation_id'])


def downgrade() -> None:
    op.drop_index('ix_conversation_messages_conversation_id', table_name='conversation_messages')
    op.drop_table('conversation_messages')
    op.drop_index('ix_conversations_patient_id', table_name='conversations')
    op.drop_table('conversations')
    # Drop the enum explicitly so this migration is fully reversible.
    sa.Enum(name='chat_role').drop(op.get_bind(), checkfirst=True)
