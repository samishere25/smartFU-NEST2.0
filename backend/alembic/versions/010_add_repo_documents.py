"""Add repo_documents table for global document repository

Revision ID: 010_add_repo_documents
Revises: 009_add_pv_audit_trail
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "010_add_repo_documents"
down_revision = "009_add_pv_audit_trail"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "repo_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("form_type", sa.String(50), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("uploaded_by", sa.String(200), nullable=True),
        sa.Column("uploaded_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("extracted_questions", postgresql.JSONB, nullable=True),
        sa.Column("extraction_status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("extraction_error", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("description", sa.Text, nullable=True),
    )

    op.create_index("ix_repo_documents_active", "repo_documents", ["is_active"])
    op.create_index("ix_repo_documents_type_active", "repo_documents", ["form_type", "is_active"])


def downgrade():
    op.drop_index("ix_repo_documents_type_active", table_name="repo_documents")
    op.drop_index("ix_repo_documents_active", table_name="repo_documents")
    op.drop_table("repo_documents")
