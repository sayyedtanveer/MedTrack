"""Store committed subcontract stock operation responses."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261117_subcontract_stock_ops"
down_revision = "20261109_1145_add_is_default"
branch_labels = None
depends_on = None



OWNERSHIP_COMMENT = "Created by Alembic revision 20261117_subcontract_stock_ops"


def _constraints(connection, table: str) -> dict[str, str]:
    return dict(connection.execute(sa.text("""
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = to_regclass(:table) AND convalidated
    """), {"table": table}).tuples().all())


def _existing_schema_is_compatible(connection) -> bool:
    rows = connection.execute(sa.text("""
        SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
                           pg_get_expr(d.adbin, d.adrelid)
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = to_regclass('subcontract_stock_operations') AND a.attnum > 0 AND NOT a.attisdropped
    """)).tuples().all()
    columns = {name: (column_type, required, default) for name, column_type, required, default in rows}
    types = {
        "tenant_id": "uuid", "subcontract_order_id": "uuid", "action": "character varying(16)",
        "operation_id": "uuid", "payload_sha256": "bytea", "response_status": "smallint",
        "response_body": "jsonb", "created_at": "timestamp with time zone",
    }
    expected_columns = {
        name: (column_type, True, "now()" if name == "created_at" else None)
        for name, column_type in types.items()
    }
    expected_constraints = {
        "pk_subcontract_stock_operations": "PRIMARY KEY (tenant_id, subcontract_order_id, action, operation_id)",
        "fk_subcontract_stock_operations_order": (
            "FOREIGN KEY (tenant_id, subcontract_order_id) REFERENCES subcontract_orders(tenant_id, id) ON DELETE RESTRICT"
        ),
        "subcontract_stock_operations_tenant_id_fkey": "FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT",
        "ck_subcontract_stock_operations_payload_hash": "CHECK ((octet_length(payload_sha256) = 32))",
        "ck_subcontract_stock_operations_status": "CHECK (((response_status >= 200) AND (response_status <= 299)))",
        "ck_subcontract_stock_operations_action": (
            "CHECK (((action)::text = ANY ((ARRAY['issue'::character varying, 'receive'::character varying, "
            "'return'::character varying])::text[])))"
        ),
    }
    actual_constraints = _constraints(connection, "subcontract_stock_operations")
    return columns == expected_columns and actual_constraints == expected_constraints


def upgrade() -> None:
    if not op.get_context().as_sql:
        connection = op.get_bind()
        order_constraint = _constraints(connection, "subcontract_orders").get("uq_subcontract_orders_tenant_id_id")
        table_exists = connection.scalar(sa.text("SELECT to_regclass('subcontract_stock_operations') IS NOT NULL"))
        if table_exists:
            if order_constraint == "UNIQUE (tenant_id, id)" and _existing_schema_is_compatible(connection):
                return
            raise RuntimeError("Existing subcontract stock operation schema differs from the approved migration")
        if order_constraint is not None:
            raise RuntimeError("Stock operation table is missing but its order constraint already exists")
    op.create_unique_constraint("uq_subcontract_orders_tenant_id_id", "subcontract_orders", ["tenant_id", "id"])
    op.create_table(
        "subcontract_stock_operations",
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("subcontract_order_id", postgresql.UUID(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("operation_id", postgresql.UUID(), nullable=False),
        sa.Column("payload_sha256", sa.LargeBinary(), nullable=False),
        sa.Column("response_status", sa.SmallInteger(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "subcontract_order_id", "action", "operation_id",
                                name="pk_subcontract_stock_operations"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "subcontract_order_id"], ["subcontract_orders.tenant_id", "subcontract_orders.id"],
                                name="fk_subcontract_stock_operations_order", ondelete="RESTRICT"),
        sa.CheckConstraint("action IN ('issue', 'receive', 'return')", name="ck_subcontract_stock_operations_action"),
        sa.CheckConstraint("octet_length(payload_sha256) = 32", name="ck_subcontract_stock_operations_payload_hash"),
        sa.CheckConstraint("response_status BETWEEN 200 AND 299", name="ck_subcontract_stock_operations_status"),
    )

    op.execute(f"COMMENT ON TABLE subcontract_stock_operations IS '{OWNERSHIP_COMMENT}'")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF obj_description('subcontract_stock_operations'::regclass) IS DISTINCT FROM
               'Created by Alembic revision 20261117_subcontract_stock_ops' THEN
                RAISE EXCEPTION 'Retain pre-existing subcontract stock operation schema on downgrade';
            END IF;
            LOCK TABLE subcontract_stock_operations IN ACCESS EXCLUSIVE MODE;
            IF EXISTS (SELECT 1 FROM subcontract_stock_operations) THEN
                RAISE EXCEPTION 'Retain committed subcontract stock replay records before downgrade';
            END IF;
        END $$;
    """)
    op.drop_table("subcontract_stock_operations")
    op.drop_constraint("uq_subcontract_orders_tenant_id_id", "subcontract_orders", type_="unique")

