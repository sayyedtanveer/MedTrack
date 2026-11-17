-- Repair the missing work-order line schema from Alembic revision c5d9f2b1e8a3.
-- Run manually against the intended MedTrack PostgreSQL database after review.
-- No Alembic stamp, sales approvals, or changes to existing work-order headers.
BEGIN;
SET LOCAL search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';

DO $repair$
BEGIN
    IF to_regclass('public.work_orders') IS NULL OR to_regclass('public.item_variants') IS NULL
       OR to_regclass('public.boms') IS NULL OR to_regclass('public.work_order_materials') IS NULL
       OR to_regclass('public.job_cards') IS NULL THEN
        RAISE EXCEPTION 'Required MedTrack tables are missing. Verify the database target.';
    END IF;

    IF to_regclass('public.work_order_lines') IS NULL THEN
        IF EXISTS (
            SELECT 1 FROM work_orders AS wo
            LEFT JOIN item_variants AS variant ON variant.id = wo.product_id AND variant.tenant_id = wo.tenant_id
            LEFT JOIN boms AS bom ON bom.id = wo.bom_id AND bom.tenant_id = wo.tenant_id
            WHERE wo.is_deleted = FALSE AND (variant.id IS NULL OR bom.id IS NULL)
        ) THEN
            RAISE EXCEPTION 'Existing work orders with incompatible product or BOM references require review';
        END IF;

        CREATE TABLE public.work_order_lines (
            id UUID PRIMARY KEY,
            work_order_id UUID NOT NULL,
            tenant_id UUID NOT NULL,
            product_id UUID NOT NULL,
            bom_id UUID NOT NULL,
            planned_quantity NUMERIC(15, 3) NOT NULL,
            produced_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
            scrap_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
            status VARCHAR(50) NOT NULL DEFAULT 'PLANNED',
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            deleted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_wo_line_work_order FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE,
            CONSTRAINT fk_wo_line_product FOREIGN KEY (product_id) REFERENCES public.item_variants(id) ON DELETE RESTRICT,
            CONSTRAINT fk_wo_line_bom FOREIGN KEY (bom_id) REFERENCES public.boms(id) ON DELETE RESTRICT
        );

        INSERT INTO public.work_order_lines (
            id, work_order_id, tenant_id, product_id, bom_id, planned_quantity,
            produced_quantity, scrap_quantity, status, is_deleted, created_at, updated_at
        )
        SELECT gen_random_uuid(), id, tenant_id, product_id, bom_id, planned_quantity,
               produced_quantity, scrap_quantity, status::text, is_deleted, created_at, updated_at
        FROM public.work_orders
        WHERE is_deleted = FALSE;
    END IF;

    ALTER TABLE public.work_order_materials ADD COLUMN IF NOT EXISTS work_order_line_id UUID;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.work_order_materials'::regclass AND conname = 'fk_wo_mat_line'
    ) THEN
        ALTER TABLE public.work_order_materials ADD CONSTRAINT fk_wo_mat_line
            FOREIGN KEY (work_order_line_id) REFERENCES public.work_order_lines(id) ON DELETE SET NULL;
    END IF;

    ALTER TABLE public.job_cards ADD COLUMN IF NOT EXISTS work_order_line_id UUID;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.job_cards'::regclass AND conname = 'fk_job_card_line'
    ) THEN
        ALTER TABLE public.job_cards ADD CONSTRAINT fk_job_card_line
            FOREIGN KEY (work_order_line_id) REFERENCES public.work_order_lines(id) ON DELETE SET NULL;
    END IF;
END;
$repair$;

CREATE INDEX IF NOT EXISTS ix_work_order_lines_work_order_id ON public.work_order_lines(work_order_id);
CREATE INDEX IF NOT EXISTS ix_work_order_lines_tenant_id ON public.work_order_lines(tenant_id);
COMMIT;

