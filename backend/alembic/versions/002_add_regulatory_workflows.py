"""Add regulatory_workflows table

Revision ID: 002
Revises: 001
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_regulatory'
down_revision = '006_add_lifecycle_tracking'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'regulatory_workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('report_type', sa.String(100), nullable=False, server_default='CIOMS_DRAFT'),
        sa.Column('due_date', sa.DateTime, nullable=False),
        sa.Column('cioms_placeholder', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('regulatory_workflows')
