"""add otp login (otp_requests table + users.phone)

Revision ID: 49c86fd969f2
Revises: 9a1c78a56f1a
Create Date: 2026-09-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '49c86fd969f2'
down_revision: Union[str, None] = '9a1c78a56f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'otp_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts_left', sa.Integer(), server_default='5', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_otp_requests_phone', 'otp_requests', ['phone'])
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=200), nullable=True)
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_phone', table_name='users')
    op.drop_column('users', 'phone')
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=200), nullable=False)
    op.drop_index('ix_otp_requests_phone', table_name='otp_requests')
    op.drop_table('otp_requests')
