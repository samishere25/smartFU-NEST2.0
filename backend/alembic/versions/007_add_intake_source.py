"""Add intake_source and source_filename to ae_cases

Revision ID: 007_add_intake_source
Revises: 006_add_lifecycle_tracking
Create Date: 2026-02-16

Track whether a case was created from CSV upload, PDF upload, or manual entry.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_intake_source'
down_revision = '002_regulatory'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ae_cases', sa.Column('intake_source', sa.String(20), server_default='CSV', nullable=True))
    op.add_column('ae_cases', sa.Column('source_filename', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('ae_cases', 'source_filename')
    op.drop_column('ae_cases', 'intake_source')
