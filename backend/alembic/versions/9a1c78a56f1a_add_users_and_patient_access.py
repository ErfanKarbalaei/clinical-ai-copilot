"""add users and patient user access

Revision ID: 9a1c78a56f1a
Revises: ab22d66552c2
Create Date: 2026-09-17 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1c78a56f1a'
down_revision: Union[str, None] = 'ab22d66552c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create_table auto-creates the native enum (unlike add_column)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('password_hash', sa.String(length=200), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('role', sa.Enum('doctor', 'admin', name='user_role'), server_default='doctor', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'patient_user_access',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_id', 'user_id', name='uq_patient_user'),
    )
    op.create_index('ix_patient_user_access_patient_id', 'patient_user_access', ['patient_id'])
    op.create_index('ix_patient_user_access_user_id', 'patient_user_access', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_patient_user_access_user_id', table_name='patient_user_access')
    op.drop_index('ix_patient_user_access_patient_id', table_name='patient_user_access')
    op.drop_table('patient_user_access')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=True)
