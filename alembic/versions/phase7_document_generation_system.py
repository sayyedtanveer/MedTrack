"""Add enterprise document generation system.

Revision ID: phase7_document_generation_system
Revises: phase6_item_code_system
Create Date: 2026-05-11 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "p7_doc_gen_system"
down_revision = "phase6_item_code_system"
branch_labels = None
depends_on = 'sc_foundation'


def upgrade() -> None:
    # Add branding fields to tenants table
    op.add_column(
        "tenants",
        sa.Column("company_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("logo_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("gst_number", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("address", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("phone", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("footer_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("signature_image_url", sa.String(length=500), nullable=True),
    )

    # Add item_code column to materials table
    op.add_column(
        "materials",
        sa.Column("item_code", sa.String(length=50), nullable=True),
    )

    # Add quotation_number column to supplier_quotations table
    op.add_column(
        "supplier_quotations",
        sa.Column("quotation_number", sa.String(length=40), nullable=False, server_default=""),
    )

    # Create documents table for versioning and audit trail
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_entity", "documents", ["document_type", "entity_id"])
    op.create_index("ix_documents_is_deleted", "documents", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_documents_is_deleted", table_name="documents")
    op.drop_index("ix_documents_entity", table_name="documents")
    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")
    
    op.drop_column("supplier_quotations", "quotation_number")
    op.drop_column("materials", "item_code")
    
    op.drop_column("tenants", "signature_image_url")
    op.drop_column("tenants", "footer_text")
    op.drop_column("tenants", "email")
    op.drop_column("tenants", "phone")
    op.drop_column("tenants", "address")
    op.drop_column("tenants", "gst_number")
    op.drop_column("tenants", "logo_url")
    op.drop_column("tenants", "company_name")
