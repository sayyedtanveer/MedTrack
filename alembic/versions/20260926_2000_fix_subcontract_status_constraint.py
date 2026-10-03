"""Fix subcontract_orders status constraint to match model definition.

Revision ID: 20260926_2000
Revises: c5d9f2b1e8a3
Create Date: 2026-09-26 20:00:00

"""
from __future__ import annotations

from alembic import op

revision = "20260926_2000"
down_revision = "c5d9f2b1e8a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old constraint that only allowed: draft, issued, in_progress, received, closed
    op.execute("""
        ALTER TABLE subcontract_orders 
        DROP CONSTRAINT IF EXISTS subcontract_orders_status_check
    """)
    
    # Add the new constraint matching the model lifecycle:
    # draft → approved → materials_issued → partially_received → completed
    #                  ↘                                          ↗
    #                   cancelled
    op.execute("""
        ALTER TABLE subcontract_orders 
        ADD CONSTRAINT subcontract_orders_status_check 
        CHECK (status IN (
            'draft', 
            'approved', 
            'materials_issued', 
            'partially_received', 
            'completed', 
            'cancelled'
        ))
    """)


def downgrade() -> None:
    # Restore the old constraint
    op.execute("""
        ALTER TABLE subcontract_orders 
        DROP CONSTRAINT IF EXISTS subcontract_orders_status_check
    """)
    
    op.execute("""
        ALTER TABLE subcontract_orders 
        ADD CONSTRAINT subcontract_orders_status_check 
        CHECK (status IN (
            'draft', 
            'issued', 
            'in_progress', 
            'received', 
            'closed'
        ))
    """)
