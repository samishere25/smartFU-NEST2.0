"""Add PV audit trail table and signal enhancement columns

Revision ID: 009_add_pv_audit_trail
Revises: 008_add_cioms_fields
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009_add_pv_audit_trail'
down_revision = '008_add_cioms_fields'
branch_labels = None
depends_on = None


def upgrade():
    # ── PV Audit Trail (immutable, append-only) ──
    op.create_table(
        'pv_audit_trail',
        sa.Column('audit_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('actor_type', sa.String(20), nullable=False),
        sa.Column('actor_id', sa.String(200), nullable=True),
        sa.Column('action_type', sa.String(100), nullable=False, index=True),
        sa.Column('previous_value', postgresql.JSON(), nullable=True),
        sa.Column('new_value', postgresql.JSON(), nullable=True),
        sa.Column('decision_metadata', postgresql.JSON(), nullable=True),
        sa.Column('model_version', sa.String(100), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('regulatory_impact', sa.Boolean(), default=False),
    )

    # Composite indexes
    op.create_index('ix_pv_audit_case_action', 'pv_audit_trail', ['case_id', 'action_type'])
    op.create_index('ix_pv_audit_case_time', 'pv_audit_trail', ['case_id', 'timestamp'])
    op.create_index('ix_pv_audit_actor_time', 'pv_audit_trail', ['actor_type', 'timestamp'])
    op.create_index('ix_pv_audit_signal_action', 'pv_audit_trail', ['signal_id', 'action_type'])

    # ── Signal model enhancements ──
    op.add_column('safety_signals', sa.Column('seriousness_ratio', sa.Float(), nullable=True))
    op.add_column('safety_signals', sa.Column('risk_priority', sa.String(20), nullable=True))
    op.add_column('safety_signals', sa.Column('review_note', sa.Text(), nullable=True))
    op.add_column('safety_signals', sa.Column('frozen_snapshot', postgresql.JSON(), nullable=True))


def downgrade():
    op.drop_column('safety_signals', 'frozen_snapshot')
    op.drop_column('safety_signals', 'review_note')
    op.drop_column('safety_signals', 'risk_priority')
    op.drop_column('safety_signals', 'seriousness_ratio')

    op.drop_index('ix_pv_audit_signal_action', table_name='pv_audit_trail')
    op.drop_index('ix_pv_audit_actor_time', table_name='pv_audit_trail')
    op.drop_index('ix_pv_audit_case_time', table_name='pv_audit_trail')
    op.drop_index('ix_pv_audit_case_action', table_name='pv_audit_trail')
    op.drop_table('pv_audit_trail')
