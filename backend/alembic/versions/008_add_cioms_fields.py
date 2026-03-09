"""Add CIOMS Form-I fields to ae_cases

Revision ID: 008_add_cioms_fields
Revises: 007_add_intake_source
Create Date: 2026-02-17

Adds CIOMS-specific columns to ae_cases for structured pharmacovigilance
data from CIOMS Form-I PDF ingestion. All columns are nullable to maintain
backward compatibility with existing CSV-based cases.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_add_cioms_fields'
down_revision = '007_add_intake_source'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ae_cases', sa.Column('patient_initials', sa.String(20), nullable=True))
    op.add_column('ae_cases', sa.Column('indication', sa.String(500), nullable=True))
    op.add_column('ae_cases', sa.Column('therapy_start', sa.DateTime(), nullable=True))
    op.add_column('ae_cases', sa.Column('therapy_end', sa.DateTime(), nullable=True))
    op.add_column('ae_cases', sa.Column('therapy_duration', sa.Integer(), nullable=True))
    op.add_column('ae_cases', sa.Column('dechallenge', sa.String(50), nullable=True))
    op.add_column('ae_cases', sa.Column('rechallenge', sa.String(50), nullable=True))
    op.add_column('ae_cases', sa.Column('concomitant_drugs', sa.Text(), nullable=True))
    op.add_column('ae_cases', sa.Column('medical_history', sa.Text(), nullable=True))
    op.add_column('ae_cases', sa.Column('report_type', sa.String(50), nullable=True))
    op.add_column('ae_cases', sa.Column('reporter_email', sa.String(200), nullable=True))
    op.add_column('ae_cases', sa.Column('reporter_phone', sa.String(50), nullable=True))
    op.add_column('ae_cases', sa.Column('manufacturer_name', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('ae_cases', 'manufacturer_name')
    op.drop_column('ae_cases', 'reporter_phone')
    op.drop_column('ae_cases', 'reporter_email')
    op.drop_column('ae_cases', 'report_type')
    op.drop_column('ae_cases', 'medical_history')
    op.drop_column('ae_cases', 'concomitant_drugs')
    op.drop_column('ae_cases', 'rechallenge')
    op.drop_column('ae_cases', 'dechallenge')
    op.drop_column('ae_cases', 'therapy_duration')
    op.drop_column('ae_cases', 'therapy_end')
    op.drop_column('ae_cases', 'therapy_start')
    op.drop_column('ae_cases', 'indication')
    op.drop_column('ae_cases', 'patient_initials')
