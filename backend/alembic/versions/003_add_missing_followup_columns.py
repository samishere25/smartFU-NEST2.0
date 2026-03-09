"""Add missing columns to followup_attempts table

Revision ID: 003
Revises: 002
Create Date: 2026-01-30 18:27:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to followup_attempts table
    op.add_column('followup_attempts', sa.Column('iteration_number', sa.Integer, nullable=False, server_default='1'))
    op.add_column('followup_attempts', sa.Column('safety_confidence', sa.Float, nullable=True))
    op.add_column('followup_attempts', sa.Column('data_completeness', sa.Float, nullable=True))
    op.add_column('followup_attempts', sa.Column('risk_score', sa.Float, nullable=True))
    op.add_column('followup_attempts', sa.Column('response_probability', sa.Float, nullable=True))
    op.add_column('followup_attempts', sa.Column('questions_count', sa.Integer, nullable=True))
    op.add_column('followup_attempts', sa.Column('sent_method', sa.String(50), nullable=True))
    op.add_column('followup_attempts', sa.Column('sent_to', sa.String(255), nullable=True))
    op.add_column('followup_attempts', sa.Column('decision', sa.String(50), nullable=True))
    op.add_column('followup_attempts', sa.Column('reasoning', sa.Text, nullable=True))
    op.add_column('followup_attempts', sa.Column('response_received', sa.Boolean, default=False, server_default='false'))
    op.add_column('followup_attempts', sa.Column('response_received_at', sa.DateTime, nullable=True))
    op.add_column('followup_attempts', sa.Column('response_data', postgresql.JSON, nullable=True))
    op.add_column('followup_attempts', sa.Column('status', sa.String(50), nullable=True))
    op.add_column('followup_attempts', sa.Column('information_gained', sa.Text, nullable=True))
    op.add_column('followup_attempts', sa.Column('updated_at', sa.DateTime, nullable=True))
    
    # Alter questions_sent from Integer to JSON
    op.alter_column('followup_attempts', 'questions_sent',
                    type_=postgresql.JSON,
                    existing_type=sa.Integer,
                    postgresql_using='questions_sent::text::json',
                    nullable=False)
    
    # Alter response_time_hours from Integer to Float
    op.alter_column('followup_attempts', 'response_time_hours',
                    type_=sa.Float,
                    existing_type=sa.Integer)


def downgrade():
    # Remove added columns
    op.drop_column('followup_attempts', 'updated_at')
    op.drop_column('followup_attempts', 'information_gained')
    op.drop_column('followup_attempts', 'status')
    op.drop_column('followup_attempts', 'response_data')
    op.drop_column('followup_attempts', 'response_received_at')
    op.drop_column('followup_attempts', 'response_received')
    op.drop_column('followup_attempts', 'reasoning')
    op.drop_column('followup_attempts', 'decision')
    op.drop_column('followup_attempts', 'sent_to')
    op.drop_column('followup_attempts', 'sent_method')
    op.drop_column('followup_attempts', 'questions_count')
    op.drop_column('followup_attempts', 'response_probability')
    op.drop_column('followup_attempts', 'risk_score')
    op.drop_column('followup_attempts', 'data_completeness')
    op.drop_column('followup_attempts', 'safety_confidence')
    op.drop_column('followup_attempts', 'iteration_number')
    
    # Revert questions_sent back to Integer
    op.alter_column('followup_attempts', 'questions_sent',
                    type_=sa.Integer,
                    existing_type=postgresql.JSON,
                    postgresql_using='0',
                    nullable=False)
    
    # Revert response_time_hours back to Integer
    op.alter_column('followup_attempts', 'response_time_hours',
                    type_=sa.Integer,
                    existing_type=sa.Float)
