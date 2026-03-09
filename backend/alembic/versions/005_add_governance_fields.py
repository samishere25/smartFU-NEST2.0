"""
Feature 7: Add human oversight fields to ae_cases

Revision ID: 005_add_governance_fields
Revises: 004
Create Date: 2026-01-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '005_add_governance_fields'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Add human oversight and governance fields"""
    
    # Add governance fields to ae_cases table
    op.add_column('ae_cases', sa.Column('human_reviewed', sa.Boolean(), default=False))
    op.add_column('ae_cases', sa.Column('reviewed_by', sa.String(100), nullable=True))
    op.add_column('ae_cases', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('ae_cases', sa.Column('review_notes', sa.Text(), nullable=True))
    op.add_column('ae_cases', sa.Column('risk_level', sa.String(20), nullable=True))
    op.add_column('ae_cases', sa.Column('priority_score', sa.String(20), nullable=True))


def downgrade():
    """Remove governance fields"""
    
    op.drop_column('ae_cases', 'priority_score')
    op.drop_column('ae_cases', 'risk_level')
    op.drop_column('ae_cases', 'review_notes')
    op.drop_column('ae_cases', 'reviewed_at')
    op.drop_column('ae_cases', 'reviewed_by')
    op.drop_column('ae_cases', 'human_reviewed')
