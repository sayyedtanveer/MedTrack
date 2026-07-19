-- Sales Order approval workflow fields
-- Run manually on the MedTrack PostgreSQL database before starting the updated backend.

BEGIN;

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS approver_id UUID NULL;

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ NULL;

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ NULL;

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ NULL;

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS approval_notes VARCHAR(1000) NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_sales_orders_approver_id_users'
    ) THEN
        ALTER TABLE sales_orders
            ADD CONSTRAINT fk_sales_orders_approver_id_users
            FOREIGN KEY (approver_id)
            REFERENCES users(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_sales_orders_approver_id
    ON sales_orders (approver_id);

CREATE INDEX IF NOT EXISTS ix_sales_orders_pending_approval
    ON sales_orders (tenant_id, status, approver_id)
    WHERE is_deleted = FALSE;

COMMIT;
