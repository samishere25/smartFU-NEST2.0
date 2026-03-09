"""Make fields_requested and questions_sent nullable

Revision ID: 004
Revises: 003
Create Date: 2026-01-30 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Make fields_requested nullable
    op.alter_column('followup_attempts', 'fields_requested',
                    existing_type=sa.JSON,
                    nullable=True)
    
    # Make questions_sent nullable
    op.alter_column('followup_attempts', 'questions_sent',
                    existing_type=sa.JSON,
                    nullable=True)


def downgrade():
    # Revert fields_requested to not nullable
    op.alter_column('followup_attempts', 'fields_requested',
                    existing_type=sa.JSON,
                    nullable=False)
    
    # Revert questions_sent to not nullable
    op.alter_column('followup_attempts', 'questions_sent',
                    existing_type=sa.JSON,
                    nullable=False)
