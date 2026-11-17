-- MedTrack Gate 1. Run manually against the intended PostgreSQL database.
-- Assumes the MedTrack tables are in public. This script does not stamp Alembic.
BEGIN;
SET LOCAL search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';

DO $gate1$
DECLARE
    order_unique text;
    operation_columns jsonb;
    operation_constraints jsonb;
BEGIN
    IF to_regclass('public.subcontract_orders') IS NULL OR to_regclass('public.tenants') IS NULL THEN
        RAISE EXCEPTION 'Expected MedTrack tables in public; verify the target database';
    END IF;

    SELECT pg_get_constraintdef(oid) INTO order_unique
    FROM pg_constraint
    WHERE conrelid = 'public.subcontract_orders'::regclass
      AND conname = 'uq_subcontract_orders_tenant_id_id'
      AND convalidated;

    IF to_regclass('public.subcontract_stock_operations') IS NOT NULL THEN
        SELECT jsonb_object_agg(a.attname, jsonb_build_array(
            format_type(a.atttypid, a.atttypmod), a.attnotnull, pg_get_expr(d.adbin, d.adrelid)
        )) INTO operation_columns
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = 'public.subcontract_stock_operations'::regclass
          AND a.attnum > 0 AND NOT a.attisdropped;

        SELECT jsonb_object_agg(conname, pg_get_constraintdef(oid)) INTO operation_constraints
        FROM pg_constraint
        WHERE conrelid = 'public.subcontract_stock_operations'::regclass AND convalidated;

        IF order_unique IS DISTINCT FROM 'UNIQUE (tenant_id, id)'
           OR operation_columns IS DISTINCT FROM '{
                "tenant_id":["uuid",true,null],
                "subcontract_order_id":["uuid",true,null],
                "action":["character varying(16)",true,null],
                "operation_id":["uuid",true,null],
                "payload_sha256":["bytea",true,null],
                "response_status":["smallint",true,null],
                "response_body":["jsonb",true,null],
                "created_at":["timestamp with time zone",true,"now()"]
           }'::jsonb
           OR operation_constraints IS DISTINCT FROM jsonb_build_object(
                'pk_subcontract_stock_operations', 'PRIMARY KEY (tenant_id, subcontract_order_id, action, operation_id)',
                'fk_subcontract_stock_operations_order', 'FOREIGN KEY (tenant_id, subcontract_order_id) REFERENCES subcontract_orders(tenant_id, id) ON DELETE RESTRICT',
                'subcontract_stock_operations_tenant_id_fkey', 'FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT',
                'ck_subcontract_stock_operations_action', 'CHECK (((action)::text = ANY ((ARRAY[''issue''::character varying, ''receive''::character varying, ''return''::character varying])::text[])))',
                'ck_subcontract_stock_operations_payload_hash', 'CHECK ((octet_length(payload_sha256) = 32))',
                'ck_subcontract_stock_operations_status', 'CHECK (((response_status >= 200) AND (response_status <= 299)))'
           ) THEN
            RAISE EXCEPTION 'Existing operation schema differs from the approved Gate 1 schema';
        END IF;
        RAISE NOTICE 'Gate 1 operation schema already present and validated';
        RETURN;
    END IF;

    IF order_unique IS NOT NULL THEN
        RAISE EXCEPTION 'Order constraint exists without the operation table; review the partial install';
    END IF;

    ALTER TABLE public.subcontract_orders
        ADD CONSTRAINT uq_subcontract_orders_tenant_id_id UNIQUE (tenant_id, id);

    CREATE TABLE public.subcontract_stock_operations (
        tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
        subcontract_order_id UUID NOT NULL,
        action VARCHAR(16) NOT NULL,
        operation_id UUID NOT NULL,
        payload_sha256 BYTEA NOT NULL,
        response_status SMALLINT NOT NULL,
        response_body JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT pk_subcontract_stock_operations
            PRIMARY KEY (tenant_id, subcontract_order_id, action, operation_id),
        CONSTRAINT fk_subcontract_stock_operations_order
            FOREIGN KEY (tenant_id, subcontract_order_id)
            REFERENCES public.subcontract_orders(tenant_id, id) ON DELETE RESTRICT,
        CONSTRAINT ck_subcontract_stock_operations_action
            CHECK (action IN ('issue', 'receive', 'return')),
        CONSTRAINT ck_subcontract_stock_operations_payload_hash
            CHECK (octet_length(payload_sha256) = 32),
        CONSTRAINT ck_subcontract_stock_operations_status
            CHECK (response_status BETWEEN 200 AND 299)
    );
    RAISE NOTICE 'Gate 1 operation schema installed';
END;
$gate1$;

COMMIT;

