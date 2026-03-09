"""Add lifecycle tracking tables

Revision ID: 006_add_lifecycle_tracking
Revises: 005_add_governance_fields
Create Date: 2025-02-14

Feature-4: Follow-Up Lifecycle Tracking System
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_lifecycle_tracking'
down_revision = '005_add_governance_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Create followup_lifecycle table
    op.create_table(
        'followup_lifecycle',
        sa.Column('lifecycle_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE'), unique=True, nullable=False),
        
        # Reporter segmentation
        sa.Column('reporter_type', sa.String(20), default='NON_HCP'),
        sa.Column('reporter_subtype', sa.String(50), nullable=True),
        
        # Attempt lifecycle
        sa.Column('attempt_count', sa.Integer, default=0),
        sa.Column('max_attempts', sa.Integer, default=3),
        sa.Column('last_attempt_at', sa.DateTime, nullable=True),
        sa.Column('next_reminder_due', sa.DateTime, nullable=True),
        sa.Column('reminder_interval_hours', sa.Integer, default=24),
        
        # Response tracking
        sa.Column('response_status', sa.String(20), default='pending'),
        sa.Column('last_response_at', sa.DateTime, nullable=True),
        sa.Column('total_questions_sent', sa.Integer, default=0),
        sa.Column('total_questions_answered', sa.Integer, default=0),
        
        # Question limits
        sa.Column('questions_per_round', sa.Integer, default=3),
        
        # Escalation
        sa.Column('escalation_status', sa.String(50), default='none'),
        sa.Column('escalation_reason', sa.Text, nullable=True),
        sa.Column('escalated_at', sa.DateTime, nullable=True),
        sa.Column('escalated_to', sa.String(100), nullable=True),
        
        # Regulatory deadlines
        sa.Column('seriousness_level', sa.String(20), default='medium'),
        sa.Column('regulatory_deadline', sa.DateTime, nullable=False),
        sa.Column('days_remaining', sa.Integer, nullable=True),
        sa.Column('deadline_type', sa.String(20), default='15_day'),
        
        # Completion metrics
        sa.Column('completeness_score', sa.Float, default=0.0),
        sa.Column('safety_confidence_score', sa.Float, default=0.0),
        sa.Column('target_completeness', sa.Float, default=0.85),
        sa.Column('mandatory_fields_complete', sa.Boolean, default=False),
        
        # Closure
        sa.Column('dead_case_flag', sa.Boolean, default=False),
        sa.Column('closure_reason', sa.Text, nullable=True),
        sa.Column('closed_at', sa.DateTime, nullable=True),
        sa.Column('closed_by', sa.String(100), nullable=True),
        
        # Lifecycle status
        sa.Column('lifecycle_status', sa.String(30), default='active'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index on case_id
    op.create_index('ix_followup_lifecycle_case_id', 'followup_lifecycle', ['case_id'])
    op.create_index('ix_followup_lifecycle_status', 'followup_lifecycle', ['lifecycle_status'])
    op.create_index('ix_followup_lifecycle_deadline', 'followup_lifecycle', ['regulatory_deadline'])
    
    # Create lifecycle_attempts table
    op.create_table(
        'lifecycle_attempts',
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('lifecycle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('followup_lifecycle.lifecycle_id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False),
        
        # Attempt details
        sa.Column('attempt_number', sa.Integer, nullable=False),
        sa.Column('attempt_type', sa.String(50), default='followup'),
        
        # Channel
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('sent_to', sa.String(255), nullable=True),
        
        # Questions
        sa.Column('questions_sent', postgresql.JSON, nullable=True),
        sa.Column('questions_count', sa.Integer, default=0),
        
        # Timing
        sa.Column('sent_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('reminder_sent', sa.Boolean, default=False),
        sa.Column('reminder_sent_at', sa.DateTime, nullable=True),
        
        # Response
        sa.Column('response_received', sa.Boolean, default=False),
        sa.Column('response_received_at', sa.DateTime, nullable=True),
        sa.Column('response_type', sa.String(30), nullable=True),
        sa.Column('questions_answered', sa.Integer, default=0),
        
        # Compliance
        sa.Column('compliance_24h_met', sa.Boolean, default=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_lifecycle_attempts_lifecycle_id', 'lifecycle_attempts', ['lifecycle_id'])
    op.create_index('ix_lifecycle_attempts_case_id', 'lifecycle_attempts', ['case_id'])
    
    # Create lifecycle_audit_log table
    op.create_table(
        'lifecycle_audit_log',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('lifecycle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('followup_lifecycle.lifecycle_id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE'), nullable=False),
        
        # Action details
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('action_description', sa.Text, nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        
        # Actor
        sa.Column('actor', sa.String(100), default='system'),
        sa.Column('actor_type', sa.String(50), default='system'),
        
        # State snapshot
        sa.Column('previous_state', postgresql.JSON, nullable=True),
        sa.Column('new_state', postgresql.JSON, nullable=True),
        
        # Policy reference
        sa.Column('policy_applied', sa.String(100), nullable=True),
        
        # Timestamp
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_lifecycle_audit_log_lifecycle_id', 'lifecycle_audit_log', ['lifecycle_id'])
    op.create_index('ix_lifecycle_audit_log_case_id', 'lifecycle_audit_log', ['case_id'])
    op.create_index('ix_lifecycle_audit_log_timestamp', 'lifecycle_audit_log', ['timestamp'])
    op.create_index('ix_lifecycle_audit_log_action_type', 'lifecycle_audit_log', ['action_type'])
    
    # Create reporter_policies table
    op.create_table(
        'reporter_policies',
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), primary_key=True),
        
        # Policy name
        sa.Column('policy_name', sa.String(50), unique=True, nullable=False),
        sa.Column('reporter_type', sa.String(20), nullable=False),
        
        # Attempt limits
        sa.Column('max_attempts', sa.Integer, default=3),
        sa.Column('reminder_interval_hours', sa.Integer, default=24),
        
        # Question limits
        sa.Column('questions_per_round', sa.Integer, default=3),
        sa.Column('max_questions_total', sa.Integer, default=15),
        
        # Escalation rules
        sa.Column('escalation_after_attempts', sa.Integer, default=3),
        sa.Column('escalate_to', sa.String(100), default='supervisor'),
        sa.Column('allow_auto_dead_case', sa.Boolean, default=True),
        
        # Deadline rules
        sa.Column('deadline_warning_days', sa.Integer, default=2),
        
        # Active flag
        sa.Column('is_active', sa.Boolean, default=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Insert default policies
    op.execute("""
        INSERT INTO reporter_policies (policy_id, policy_name, reporter_type, max_attempts, reminder_interval_hours, 
                                       questions_per_round, max_questions_total, escalation_after_attempts, 
                                       escalate_to, allow_auto_dead_case, deadline_warning_days, is_active)
        VALUES 
            (gen_random_uuid(), 'HCP_POLICY', 'HCP', 4, 24, 5, 20, 3, 'medical_team', false, 2, true),
            (gen_random_uuid(), 'NON_HCP_POLICY', 'NON_HCP', 3, 24, 2, 10, 2, 'supervisor', true, 2, true)
    """)


def downgrade():
    op.drop_table('reporter_policies')
    op.drop_table('lifecycle_audit_log')
    op.drop_table('lifecycle_attempts')
    op.drop_table('followup_lifecycle')
