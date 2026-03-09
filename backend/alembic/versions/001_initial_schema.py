"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Remove pgvector extension - not needed for demo
    # op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    # op.execute('CREATE EXTENSION IF NOT EXISTS "pgvector"')
    
    # Users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(500), nullable=False),
        sa.Column('full_name', sa.String(200)),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('department', sa.String(100)),
        sa.Column('organization', sa.String(200)),
        sa.Column('permissions', postgresql.JSON, default=[]),
        sa.Column('can_approve_high_risk', sa.Boolean, default=False),
        sa.Column('mfa_enabled', sa.Boolean, default=False),
        sa.Column('failed_login_attempts', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_login', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # AE Cases table
    op.create_table(
        'ae_cases',
        sa.Column('case_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('primaryid', sa.Integer, nullable=False, unique=True, index=True),
        sa.Column('receipt_date', sa.DateTime),
        sa.Column('patient_age', sa.Integer),
        sa.Column('patient_sex', sa.String(10)),
        sa.Column('patient_age_group', sa.String(20)),
        sa.Column('suspect_drug', sa.String(500), nullable=False),
        sa.Column('drug_route', sa.String(100)),
        sa.Column('drug_dose', sa.String(500)),
        sa.Column('adverse_event', sa.String(1000), nullable=False),
        sa.Column('event_date', sa.DateTime),
        sa.Column('event_outcome', sa.String(100)),
        sa.Column('reporter_type', sa.String(10)),
        sa.Column('reporter_country', sa.String(5)),
        sa.Column('seriousness_score', sa.Float, default=0.0),
        sa.Column('data_completeness_score', sa.Float, default=0.0),
        sa.Column('case_priority', sa.String(20)),
        sa.Column('case_status', sa.String(50), default='INITIAL_RECEIVED'),
        sa.Column('is_serious', sa.Boolean, default=False),
        sa.Column('requires_followup', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Missing Fields table
    op.create_table(
        'missing_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE')),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_category', sa.String(50)),
        sa.Column('is_missing', sa.Boolean, default=True),
        sa.Column('is_unclear', sa.Boolean, default=False),
        sa.Column('is_inconsistent', sa.Boolean, default=False),
        sa.Column('safety_criticality', sa.String(20)),
        sa.Column('regulatory_requirement', sa.Boolean, default=False),
        sa.Column('should_follow_up', sa.Boolean, default=True),
        sa.Column('followup_priority', sa.Integer),
        sa.Column('question_value_score', sa.Float),
        sa.Column('missing_reason', sa.Text),
        sa.Column('impact_explanation', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # FollowUp Decisions table
    op.create_table(
        'followup_decisions',
        sa.Column('decision_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE')),
        sa.Column('decision_type', sa.String(50), nullable=False),
        sa.Column('decision_reason', sa.Text, nullable=False),
        sa.Column('agent_name', sa.String(100)),
        sa.Column('confidence_score', sa.Float),
        sa.Column('predicted_response_probability', sa.Float),
        sa.Column('optimal_timing_hours', sa.Integer),
        sa.Column('recommended_channel', sa.String(50)),
        sa.Column('case_risk_level', sa.String(20)),
        sa.Column('escalation_required', sa.Boolean, default=False),
        sa.Column('human_override', sa.Boolean, default=False),
        sa.Column('override_reason', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # FollowUp Attempts table
    op.create_table(
        'followup_attempts',
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE')),
        sa.Column('decision_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('followup_decisions.decision_id')),
        sa.Column('attempt_number', sa.Integer, nullable=False),
        sa.Column('sent_at', sa.DateTime, nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('recipient_email', sa.String(255)),
        sa.Column('secure_token', sa.String(500), unique=True),
        sa.Column('questions_sent', sa.Integer, nullable=False),
        sa.Column('fields_requested', postgresql.JSON, nullable=False),
        sa.Column('response_status', sa.String(50), default='SENT'),
        sa.Column('responded_at', sa.DateTime),
        sa.Column('response_time_hours', sa.Integer),
        sa.Column('questions_answered', sa.Integer, default=0),
        sa.Column('data_quality_score', sa.Float),
        sa.Column('stop_followup', sa.Boolean, default=False),
        sa.Column('stop_reason', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # FollowUp Responses table
    op.create_table(
        'followup_responses',
        sa.Column('response_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('followup_attempts.attempt_id', ondelete='CASCADE')),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ae_cases.case_id', ondelete='CASCADE')),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_value', sa.Text),
        sa.Column('value_type', sa.String(50)),
        sa.Column('is_complete', sa.Boolean, default=False),
        sa.Column('is_validated', sa.Boolean, default=False),
        sa.Column('needs_clarification', sa.Boolean, default=False),
        sa.Column('ai_extracted_value', sa.Text),
        sa.Column('extraction_confidence', sa.Float),
        sa.Column('responded_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('activity_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50)),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True)),
        sa.Column('user_id', sa.String(100)),
        sa.Column('user_role', sa.String(50)),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('before_state', postgresql.JSON),
        sa.Column('after_state', postgresql.JSON),
        sa.Column('change_description', sa.Text),
        sa.Column('regulatory_impact', sa.Boolean, default=False),
        sa.Column('gdpr_relevant', sa.Boolean, default=False),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now(), index=True)
    )
    
    # Safety Signals table
    op.create_table(
        'safety_signals',
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('drug_name', sa.String(500)),
        sa.Column('adverse_event', sa.String(1000)),
        sa.Column('signal_type', sa.String(50)),
        sa.Column('case_count', sa.Integer),
        sa.Column('reporting_rate', sa.Float),
        sa.Column('proportional_reporting_ratio', sa.Float),
        sa.Column('temporal_pattern', sa.Text),
        sa.Column('demographic_pattern', sa.Text),
        sa.Column('signal_strength', sa.String(20)),
        sa.Column('clinical_significance', sa.Text),
        sa.Column('signal_status', sa.String(50), default='DETECTED'),
        sa.Column('detected_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime),
        sa.Column('reviewed_by', sa.String(100))
    )


def downgrade():
    op.drop_table('safety_signals')
    op.drop_table('audit_logs')
    op.drop_table('followup_responses')
    op.drop_table('followup_attempts')
    op.drop_table('followup_decisions')
    op.drop_table('missing_fields')
    op.drop_table('ae_cases')
    op.drop_table('users')
