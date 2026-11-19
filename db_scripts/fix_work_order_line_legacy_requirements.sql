-- Fix sales approval against the legacy work_order_lines schema.
-- Run the whole file in pgAdmin Query Tool connected to local medtrack.
-- Current application work-order lines use product_id, bom_id and quantities.
-- The legacy routing fields are not supplied by that insert.
-- Existing values are preserved. This script can be run again safely.

BEGIN;
SET LOCAL lock_timeout = '5s';

DO $guard$
BEGIN
    IF current_database() <> 'medtrack' THEN
        RAISE EXCEPTION 'Connect to the audited local medtrack database first';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'work_order_lines'
          AND column_name = 'product_id'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'work_order_lines'
          AND column_name = 'bom_id'
    ) THEN
        RAISE EXCEPTION 'Unexpected work_order_lines schema. Stop and review';
    END IF;
END
$guard$;

ALTER TABLE public.work_order_lines
    ALTER COLUMN line_number DROP NOT NULL,
    ALTER COLUMN operation_name DROP NOT NULL;

COMMIT;

-- Both rows should show is_nullable = YES.
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'work_order_lines'
  AND column_name IN ('line_number', 'operation_name')
ORDER BY column_name;
