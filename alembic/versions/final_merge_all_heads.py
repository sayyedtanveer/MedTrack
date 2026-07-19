"""Final merge: unify sc_foundation and shop_floor_execution_metrics heads.

Revision ID: final_merge
Revises: sc_foundation, shop_floor_execution_metrics
"""

revision = "final_merge"
down_revision = ("sc_foundation", "shop_floor_execution_metrics")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
