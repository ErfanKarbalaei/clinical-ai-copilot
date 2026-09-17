"""add conversation message evidence

Revision ID: ab22d66552c2
Revises: 03378aed5376
Create Date: 2026-09-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ab22d66552c2'
down_revision: Union[str, None] = '03378aed5376'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversation_messages',
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('conversation_messages', 'evidence')
