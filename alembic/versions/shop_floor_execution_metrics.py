"""Shop floor execution metrics.

Revision ID: shop_floor_execution_metrics
Revises: sprint1_operational_hardening_merge
"""

from alembic import op
import sqlalchemy as sa


revision = "shop_floor_execution_metrics"
down_revision = "s1_op_hard_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_cards", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_cards", sa.Column("total_downtime_seconds", sa.Numeric(15, 3), nullable=False, server_default="0"))
    op.add_column("job_cards", sa.Column("pause_reason", sa.String(255), nullable=True))
    op.add_column("job_cards", sa.Column("operator_notes", sa.Text(), nullable=True))
    op.add_column("job_cards", sa.Column("produced_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"))
    op.add_column("job_cards", sa.Column("scrap_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"))
    op.add_column("job_cards", sa.Column("rework_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"))
    op.add_column("job_cards", sa.Column("rejected_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("job_cards", "rejected_quantity")
    op.drop_column("job_cards", "rework_quantity")
    op.drop_column("job_cards", "scrap_quantity")
    op.drop_column("job_cards", "produced_quantity")
    op.drop_column("job_cards", "operator_notes")
    op.drop_column("job_cards", "pause_reason")
    op.drop_column("job_cards", "total_downtime_seconds")
    op.drop_column("job_cards", "paused_at")
