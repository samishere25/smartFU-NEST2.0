"""Add case_confidence_history table

Revision ID: 002
Revises: 001
Create Date: 2026-01-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Case Confidence History table
    op.create_table(
        'case_confidence_history',
        sa.Column('history_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('safety_confidence', sa.Float, nullable=False),
        sa.Column('data_completeness', sa.Float, nullable=False),
        sa.Column('risk_assessment_confidence', sa.Float, nullable=False),
        sa.Column('overall_confidence', sa.Float, nullable=False),
        sa.Column('trigger_event', sa.String(100)),
        sa.Column('fields_updated', postgresql.JSON),
        sa.Column('information_gain', sa.Float),
        sa.Column('continue_followup', sa.Boolean, nullable=False),
        sa.Column('reason', sa.Text),
        sa.Column('recorded_at', sa.DateTime, server_default=sa.func.now(), index=True)
    )
    
    # Adaptive Loop Sessions table
    op.create_table(
        'adaptive_loop_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('total_iterations', sa.Integer, default=0),
        sa.Column('initial_confidence', sa.Float, nullable=False),
        sa.Column('initial_completeness', sa.Float, nullable=False),
        sa.Column('target_confidence', sa.Float, default=0.85),
        sa.Column('final_confidence', sa.Float),
        sa.Column('final_completeness', sa.Float),
        sa.Column('confidence_gain', sa.Float),
        sa.Column('converged', sa.Boolean, default=False),
        sa.Column('convergence_reason', sa.String(100)),
        sa.Column('questions_sent_total', sa.Integer, default=0),
        sa.Column('responses_received', sa.Integer, default=0),
        sa.Column('response_rate', sa.Float),
        sa.Column('information_per_question', sa.Float),
        sa.Column('cost_benefit_ratio', sa.Float),
        sa.Column('status', sa.String(50), default='ACTIVE'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )


def downgrade():
    op.drop_table('adaptive_loop_sessions')
    op.drop_table('case_confidence_history')
