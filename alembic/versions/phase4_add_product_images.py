"""Add product images support.

Revision ID: phase4_add_product_images
Revises: phase4_add_product_lifecycle
Create Date: 2026-04-15 00:00:00.000000

This migration creates the product_images table to support multi-image gallery
for product templates and variants, with support for primary/thumbnail images
and custom ordering.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase4_add_product_images'
down_revision = 'phase4_add_product_lifecycle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_images table
    op.create_table(
        'product_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_mime_type', sa.String(50), nullable=False),
        sa.Column('image_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes
    op.create_index(
        'ix_product_images_tenant_template',
        'product_images',
        ['tenant_id', 'template_id'],
    )
    op.create_index(
        'ix_product_images_tenant_variant',
        'product_images',
        ['tenant_id', 'variant_id'],
    )
    op.create_index(
        'ix_product_images_order',
        'product_images',
        ['template_id', 'variant_id', 'image_order'],
    )


def downgrade() -> None:
    op.drop_table('product_images')
