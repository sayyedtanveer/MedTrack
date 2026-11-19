-- Manual schema reconciliation for local medtrack (PostgreSQL 18).
-- Reference: checkout 6ed5356, committed schema snapshot, and migration head
-- 20261117_subcontract_stock_ops, plus the BOM SQL and the job-card mapping.
-- Back up medtrack, pause app writes, and run the whole file in pgAdmin Query Tool
-- or psql -v ON_ERROR_STOP=1. Intended for the audited schema, once.
-- Existing application rows and both migration tracking tables are preserved.
-- Foreign keys with historical violations remain NOT VALID; see the final query.
-- The live preflight found 11 affected constraints (38 references). Restore or
-- reconcile their missing parent records before validating those constraints.
-- The SQL does not import business rows or mark past data migrations as applied.

BEGIN;
SET LOCAL search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';

DO $guard$
BEGIN
    IF current_database() <> 'medtrack' THEN
        RAISE EXCEPTION 'Run this file only against the audited medtrack database';
    END IF;
    IF EXISTS (SELECT 1 FROM public.alembic_version)
        OR NOT EXISTS (
            SELECT 1 FROM public.alembic_version_medtrack_live
            WHERE version_num = 'medtrack_live_03_indexes'
        ) THEN
        RAISE EXCEPTION 'Migration history differs from the audited database';
    END IF;
END
$guard$;

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;

-- Keep the enum and existing defaults. Add the operational values from the reference.
ALTER TYPE public.work_order_status ADD VALUE IF NOT EXISTS 'IN_PROGRESS' AFTER 'RELEASED';
ALTER TYPE public.work_order_status ADD VALUE IF NOT EXISTS 'PRODUCTION_HOLD';
ALTER TYPE public.work_order_status ADD VALUE IF NOT EXISTS 'CANCELLED';
ALTER TABLE public.work_orders
    DROP CONSTRAINT ck_work_order_status,
    ADD CONSTRAINT ck_work_order_status CHECK (status::text IN (
        'PLANNED', 'RELEASED', 'MATERIAL_PENDING', 'MATERIAL_RESERVED',
        'MATERIAL_ISSUED', 'IN_PRODUCTION', 'QC_PENDING', 'QC_APPROVED',
        'QC_REJECTED', 'FG_RECEIVED', 'COMPLETED', 'CLOSED', 'REWORK',
        'REJECTED', 'PRODUCTION_HOLD', 'CANCELLED'
    ));

-- Widen columns that currently reject values supported by the mapped models.
ALTER TABLE public.materials
    ALTER COLUMN barcode TYPE varchar(120),
    ALTER COLUMN supplier_item_code TYPE varchar(120),
    ALTER COLUMN purchase_uom TYPE varchar(40);
ALTER TABLE public.work_order_lines ALTER COLUMN status TYPE varchar(50);

-- Existing tables: add missing columns, defaults and checks.

ALTER TABLE public.locations ADD COLUMN is_default boolean DEFAULT false NOT NULL;

ALTER TABLE public.material_requests ADD CONSTRAINT material_requests_item_type_check CHECK (((item_type)::text = ANY (ARRAY[('material'::character varying)::text, ('product'::character varying)::text])));

ALTER TABLE public.material_requests ADD CONSTRAINT material_requests_status_check CHECK (((status)::text = ANY (ARRAY[('open'::character varying)::text, ('partial'::character varying)::text, ('fulfilled'::character varying)::text, ('cancelled'::character varying)::text])));

ALTER TABLE public.non_conformance_reports ADD CONSTRAINT non_conformance_reports_ncr_type_check CHECK (((ncr_type)::text = ANY (ARRAY[('rework'::character varying)::text, ('scrap'::character varying)::text, ('reject'::character varying)::text])));

ALTER TABLE public.purchase_order_lines ALTER COLUMN id SET DEFAULT public.uuid_generate_v4();

ALTER TABLE public.purchase_order_lines ADD COLUMN unit_id uuid;

ALTER TABLE public.purchase_order_lines ADD CONSTRAINT purchase_order_lines_quantity_check CHECK ((quantity > (0)::numeric));

ALTER TABLE public.purchase_order_lines ADD CONSTRAINT purchase_order_lines_received_quantity_check CHECK ((received_quantity >= (0)::numeric));

ALTER TABLE public.purchase_orders ALTER COLUMN id SET DEFAULT public.uuid_generate_v4();

ALTER TABLE public.purchase_orders ALTER COLUMN order_date SET DEFAULT CURRENT_DATE;

ALTER TABLE public.purchase_orders ADD COLUMN currency_code character varying(3);

ALTER TABLE public.purchase_orders ADD CONSTRAINT purchase_orders_status_check CHECK (
    status IN ('draft', 'sent', 'acknowledged', 'partial', 'received', 'closed', 'cancelled')
);

ALTER TABLE public.quality_inspections ALTER COLUMN inspection_date SET DEFAULT CURRENT_DATE;

ALTER TABLE public.quality_inspections ADD CONSTRAINT quality_inspections_reference_type_check CHECK (((reference_type)::text = ANY (ARRAY[('purchase_receipt'::character varying)::text, ('work_order'::character varying)::text])));

ALTER TABLE public.quality_inspections ADD CONSTRAINT quality_inspections_result_check CHECK (((result)::text = ANY (ARRAY[('pass'::character varying)::text, ('fail'::character varying)::text, ('rework'::character varying)::text])));

ALTER TABLE public.subcontract_material_issues ADD CONSTRAINT subcontract_material_issues_quantity_check CHECK ((quantity > (0)::numeric));

ALTER TABLE public.subcontract_orders ADD CONSTRAINT subcontract_orders_product_type_check CHECK (((product_type)::text = ANY (ARRAY[('variant'::character varying)::text, ('material'::character varying)::text])));

ALTER TABLE public.subcontract_orders ADD CONSTRAINT subcontract_orders_quantity_check CHECK ((quantity > (0)::numeric));

ALTER TABLE public.subcontract_orders ADD CONSTRAINT subcontract_orders_status_check CHECK (((status)::text = ANY (ARRAY[('draft'::character varying)::text, ('approved'::character varying)::text, ('materials_issued'::character varying)::text, ('partially_received'::character varying)::text, ('completed'::character varying)::text, ('cancelled'::character varying)::text])));

ALTER TABLE public.supplier_price_history ALTER COLUMN effective_from SET DEFAULT CURRENT_DATE;

ALTER TABLE public.supplier_price_history ADD COLUMN effective_to date;

ALTER TABLE public.supplier_price_history ADD COLUMN grn_line_id uuid;

ALTER TABLE public.supplier_price_history ADD COLUMN currency_code character varying(3);

ALTER TABLE public.supplier_price_history ADD COLUMN unit_id uuid;

ALTER TABLE public.supplier_quotations ADD COLUMN rfq_id uuid;

ALTER TABLE public.supplier_quotations ALTER COLUMN quotation_number SET DEFAULT ''::character varying;

ALTER TABLE public.supplier_quotations ADD COLUMN currency_code character varying(3);

ALTER TABLE public.supplier_quotations ADD COLUMN unit_id uuid;

ALTER TABLE public.supplier_quotations ADD CONSTRAINT supplier_quotations_status_check CHECK (((status)::text = ANY (ARRAY[('draft'::character varying)::text, ('submitted'::character varying)::text, ('accepted'::character varying)::text, ('rejected'::character varying)::text])));

ALTER TABLE public.suppliers ALTER COLUMN id SET DEFAULT public.uuid_generate_v4();

ALTER TABLE public.job_cards ADD COLUMN work_order_line_id uuid;
ALTER TABLE public.job_cards
    ADD CONSTRAINT fk_job_card_line FOREIGN KEY (work_order_line_id)
    REFERENCES public.work_order_lines (id) ON DELETE SET NULL;

-- Apply the BOM making charge definitions and one-active-version indexes.
ALTER TABLE public.boms
    ADD COLUMN making_charge numeric(18, 4),
    ADD COLUMN making_charge_basis varchar(20),
    ADD CONSTRAINT chk_bom_making_charge_nonneg CHECK (making_charge >= 0),
    ADD CONSTRAINT chk_bom_making_charge_basis_valid CHECK (making_charge_basis = 'PER_PIECE'),
    ADD CONSTRAINT chk_bom_making_charge_paired
        CHECK ((making_charge IS NULL) = (making_charge_basis IS NULL));

CREATE UNIQUE INDEX uq_bom_one_active_per_variant
    ON public.boms (tenant_id, variant_id)
    WHERE is_active AND NOT is_deleted AND variant_id IS NOT NULL;
CREATE UNIQUE INDEX uq_bom_one_active_per_template
    ON public.boms (tenant_id, template_id)
    WHERE is_active AND NOT is_deleted AND template_id IS NOT NULL;

CREATE FUNCTION public.prevent_material_cost_history_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION 'material_cost_history is append-only; add a reversal entry';
        END;
        $$;

CREATE SEQUENCE public.invoice_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.material_cost_history (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    old_cost numeric(18,6),
    new_cost numeric(18,6) NOT NULL,
    change_type character varying(30) NOT NULL,
    source_type character varying(20) NOT NULL,
    source_id character varying(255),
    approved_by uuid,
    notes text,
    created_at timestamp with time zone NOT NULL
);

CREATE SEQUENCE public.payment_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.price_override_records (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    supplier_id uuid,
    purchase_order_line_id uuid,
    grn_id uuid,
    suggested_price numeric(18,6) NOT NULL,
    override_price numeric(18,6) NOT NULL,
    variance_percent numeric(8,2),
    override_reason character varying(50),
    pricing_source character varying(40),
    currency_code character varying(3),
    unit_id uuid,
    override_by uuid NOT NULL,
    notes text,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);

CREATE TABLE public.quarantine_releases (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    ncr_id uuid NOT NULL,
    released_by uuid,
    released_at timestamp with time zone DEFAULT now() NOT NULL,
    new_location_id uuid,
    reason text
);

CREATE TABLE public.standard_cost_revisions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    requested_by uuid NOT NULL,
    requested_cost numeric(18,6) NOT NULL,
    current_cost numeric(18,6) NOT NULL,
    variance_percent numeric(8,2),
    reason character varying(50) NOT NULL,
    notes text,
    status character varying(20) NOT NULL,
    approved_by uuid,
    approved_at timestamp with time zone,
    rejection_reason text,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);

CREATE TABLE public.subcontract_stock_operations (
    tenant_id uuid NOT NULL,
    subcontract_order_id uuid NOT NULL,
    action character varying(16) NOT NULL,
    operation_id uuid NOT NULL,
    payload_sha256 bytea NOT NULL,
    response_status smallint NOT NULL,
    response_body jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_subcontract_stock_operations_action CHECK (((action)::text = ANY ((ARRAY['issue'::character varying, 'receive'::character varying, 'return'::character varying])::text[]))),
    CONSTRAINT ck_subcontract_stock_operations_payload_hash CHECK ((octet_length(payload_sha256) = 32)),
    CONSTRAINT ck_subcontract_stock_operations_status CHECK (((response_status >= 200) AND (response_status <= 299)))
);

COMMENT ON TABLE public.subcontract_stock_operations IS 'Created by Alembic revision 20261117_subcontract_stock_ops';

CREATE SEQUENCE public.supplier_invoice_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE SEQUENCE public.supplier_payment_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.supplier_price_agreements (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    material_id uuid NOT NULL,
    status character varying(20) NOT NULL,
    base_price numeric(18,6) NOT NULL,
    currency_code character varying(3) NOT NULL,
    purchase_uom_id uuid,
    minimum_order_quantity numeric(18,6),
    quantity_tier text,
    effective_from timestamp with time zone NOT NULL,
    effective_to timestamp with time zone,
    notes text,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_by uuid,
    updated_by uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);

ALTER TABLE ONLY public.material_cost_history
    ADD CONSTRAINT material_cost_history_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.subcontract_stock_operations
    ADD CONSTRAINT pk_subcontract_stock_operations PRIMARY KEY (tenant_id, subcontract_order_id, action, operation_id);

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.standard_cost_revisions
    ADD CONSTRAINT standard_cost_revisions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.supplier_price_agreements
    ADD CONSTRAINT supplier_price_agreements_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.subcontract_orders
    ADD CONSTRAINT uq_subcontract_orders_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE ONLY public.supplier_price_history
    ADD CONSTRAINT uq_supplier_price_history_grn_line UNIQUE (tenant_id, grn_line_id);

CREATE INDEX ix_insp_det_inspection ON public.inspection_details USING btree (inspection_id);

CREATE INDEX ix_insp_tpl_tenant ON public.inspection_templates USING btree (tenant_id);

CREATE INDEX ix_location_tenant_default ON public.locations USING btree (tenant_id, is_default) WHERE ((is_default = true) AND (is_deleted = false) AND (is_active = true));

CREATE INDEX ix_material_cost_history_change_type ON public.material_cost_history USING btree (change_type);

CREATE INDEX ix_material_cost_history_created_at ON public.material_cost_history USING btree (created_at);

CREATE INDEX ix_material_cost_history_material_id ON public.material_cost_history USING btree (material_id);

CREATE INDEX ix_material_cost_history_tenant_id ON public.material_cost_history USING btree (tenant_id);

CREATE INDEX ix_ncr_tenant ON public.non_conformance_reports USING btree (tenant_id);

CREATE INDEX ix_price_override_records_created_at ON public.price_override_records USING btree (created_at);

CREATE INDEX ix_price_override_records_grn_id ON public.price_override_records USING btree (grn_id);

CREATE INDEX ix_price_override_records_material_id ON public.price_override_records USING btree (material_id);

CREATE INDEX ix_price_override_records_override_by ON public.price_override_records USING btree (override_by);

CREATE INDEX ix_price_override_records_purchase_order_line_id ON public.price_override_records USING btree (purchase_order_line_id);

CREATE INDEX ix_price_override_records_tenant_id ON public.price_override_records USING btree (tenant_id);

CREATE INDEX ix_qr_ncr ON public.quarantine_releases USING btree (ncr_id);

CREATE INDEX ix_smi_order ON public.subcontract_material_issues USING btree (subcontract_order_id);

CREATE INDEX ix_sph_material ON public.supplier_price_history USING btree (material_id);

CREATE INDEX ix_sph_supplier ON public.supplier_price_history USING btree (supplier_id);

CREATE INDEX ix_sq_status ON public.supplier_quotations USING btree (status);

CREATE INDEX ix_standard_cost_revisions_approved_by ON public.standard_cost_revisions USING btree (approved_by);

CREATE INDEX ix_standard_cost_revisions_created_at ON public.standard_cost_revisions USING btree (created_at);

CREATE INDEX ix_standard_cost_revisions_material_id ON public.standard_cost_revisions USING btree (material_id);

CREATE INDEX ix_standard_cost_revisions_requested_by ON public.standard_cost_revisions USING btree (requested_by);

CREATE INDEX ix_standard_cost_revisions_status ON public.standard_cost_revisions USING btree (status);

CREATE INDEX ix_standard_cost_revisions_tenant_id ON public.standard_cost_revisions USING btree (tenant_id);

CREATE INDEX ix_supplier_price_agreements_effective_from ON public.supplier_price_agreements USING btree (effective_from);

CREATE INDEX ix_supplier_price_agreements_is_deleted ON public.supplier_price_agreements USING btree (is_deleted);

CREATE INDEX ix_supplier_price_agreements_material_id ON public.supplier_price_agreements USING btree (material_id);

CREATE INDEX ix_supplier_price_agreements_status ON public.supplier_price_agreements USING btree (status);

CREATE INDEX ix_supplier_price_agreements_supplier_id ON public.supplier_price_agreements USING btree (supplier_id);

CREATE INDEX ix_supplier_price_agreements_tenant_id ON public.supplier_price_agreements USING btree (tenant_id);

CREATE INDEX ix_suppliers_active ON public.suppliers USING btree (tenant_id, is_active) WHERE (is_deleted = false);

CREATE INDEX ix_work_orders_sales_order_id ON public.work_orders USING btree (sales_order_id);

CREATE INDEX ix_work_orders_sales_order_line_id ON public.work_orders USING btree (sales_order_line_id);

CREATE TRIGGER trg_material_cost_history_append_only BEFORE DELETE OR UPDATE ON public.material_cost_history FOR EACH ROW EXECUTE FUNCTION public.prevent_material_cost_history_mutation();

ALTER TABLE ONLY public.document_associations
    ADD CONSTRAINT document_associations_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT fk_purchase_order_lines_unit_id FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.subcontract_stock_operations
    ADD CONSTRAINT fk_subcontract_stock_operations_order FOREIGN KEY (tenant_id, subcontract_order_id) REFERENCES public.subcontract_orders(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.supplier_price_history
    ADD CONSTRAINT fk_supplier_price_history_grn_line_id FOREIGN KEY (grn_line_id) REFERENCES public.grn_lines(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.supplier_price_history
    ADD CONSTRAINT fk_supplier_price_history_unit_id FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT fk_supplier_quotations_unit_id FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES public.purchase_orders(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.grn_lines
    ADD CONSTRAINT grn_lines_po_line_id_fkey FOREIGN KEY (po_line_id) REFERENCES public.purchase_order_lines(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.job_cards
    ADD CONSTRAINT job_cards_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.material_consumption_records
    ADD CONSTRAINT material_consumption_records_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.material_cost_history
    ADD CONSTRAINT material_cost_history_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.material_cost_history
    ADD CONSTRAINT material_cost_history_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.material_cost_history
    ADD CONSTRAINT material_cost_history_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.material_shortages
    ADD CONSTRAINT material_shortages_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_inspection_template_id_fkey FOREIGN KEY (inspection_template_id) REFERENCES public.inspection_templates(id) NOT VALID;

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT pick_lists_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_grn_id_fkey FOREIGN KEY (grn_id) REFERENCES public.goods_receipt_notes(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_override_by_fkey FOREIGN KEY (override_by) REFERENCES public.users(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_purchase_order_line_id_fkey FOREIGN KEY (purchase_order_line_id) REFERENCES public.purchase_order_lines(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.price_override_records
    ADD CONSTRAINT price_override_records_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.production_records
    ADD CONSTRAINT production_records_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_linked_po_id_fkey FOREIGN KEY (linked_po_id) REFERENCES public.purchase_orders(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_ncr_id_fkey FOREIGN KEY (ncr_id) REFERENCES public.non_conformance_reports(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_new_location_id_fkey FOREIGN KEY (new_location_id) REFERENCES public.locations(id);

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_released_by_fkey FOREIGN KEY (released_by) REFERENCES public.users(id);

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.supplier_quotations(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_awarded_po_id_fkey FOREIGN KEY (awarded_po_id) REFERENCES public.purchase_orders(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_awarded_supplier_id_fkey FOREIGN KEY (awarded_supplier_id) REFERENCES public.suppliers(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_material_request_id_fkey FOREIGN KEY (material_request_id) REFERENCES public.material_requests(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.standard_cost_revisions
    ADD CONSTRAINT standard_cost_revisions_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.standard_cost_revisions
    ADD CONSTRAINT standard_cost_revisions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.standard_cost_revisions
    ADD CONSTRAINT standard_cost_revisions_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.standard_cost_revisions
    ADD CONSTRAINT standard_cost_revisions_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.standard_cost_revisions
    ADD CONSTRAINT standard_cost_revisions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.standard_cost_revisions
    ADD CONSTRAINT standard_cost_revisions_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.subcontract_order_lines
    ADD CONSTRAINT subcontract_order_lines_subcontract_order_id_fkey FOREIGN KEY (subcontract_order_id) REFERENCES public.subcontract_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.subcontract_stock_operations
    ADD CONSTRAINT subcontract_stock_operations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT supplier_invoices_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES public.purchase_orders(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT supplier_invoices_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.supplier_payments
    ADD CONSTRAINT supplier_payments_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE ONLY public.supplier_price_agreements
    ADD CONSTRAINT supplier_price_agreements_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.supplier_price_agreements
    ADD CONSTRAINT supplier_price_agreements_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.supplier_price_agreements
    ADD CONSTRAINT supplier_price_agreements_purchase_uom_id_fkey FOREIGN KEY (purchase_uom_id) REFERENCES public.units_of_measure(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.supplier_price_agreements
    ADD CONSTRAINT supplier_price_agreements_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.supplier_price_agreements
    ADD CONSTRAINT supplier_price_agreements_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.supplier_price_agreements
    ADD CONSTRAINT supplier_price_agreements_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT supplier_quotations_rfq_id_fkey FOREIGN KEY (rfq_id) REFERENCES public.rfqs(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE SET NULL NOT VALID;

ALTER TABLE ONLY public.work_order_materials
    ADD CONSTRAINT work_order_materials_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE NOT VALID;

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT work_orders_sales_order_line_id_fkey FOREIGN KEY (sales_order_line_id) REFERENCES public.sales_order_lines(id) ON DELETE SET NULL NOT VALID;

-- Validate existing rows where possible. Preserve historical orphans for manual review.
DO $validate$
DECLARE
    fk record;
BEGIN
    FOR fk IN SELECT * FROM (VALUES
        ('document_associations', 'document_associations_work_order_id_fkey'),
        ('purchase_order_lines', 'fk_purchase_order_lines_unit_id'),
        ('supplier_price_history', 'fk_supplier_price_history_grn_line_id'),
        ('supplier_price_history', 'fk_supplier_price_history_unit_id'),
        ('supplier_quotations', 'fk_supplier_quotations_unit_id'),
        ('goods_receipt_notes', 'goods_receipt_notes_purchase_order_id_fkey'),
        ('goods_receipt_notes', 'goods_receipt_notes_supplier_id_fkey'),
        ('grn_lines', 'grn_lines_po_line_id_fkey'),
        ('job_cards', 'job_cards_work_order_id_fkey'),
        ('material_consumption_records', 'material_consumption_records_work_order_id_fkey'),
        ('material_shortages', 'material_shortages_work_order_id_fkey'),
        ('materials', 'materials_inspection_template_id_fkey'),
        ('pick_lists', 'pick_lists_work_order_id_fkey'),
        ('production_records', 'production_records_work_order_id_fkey'),
        ('purchase_requisitions', 'purchase_requisitions_linked_po_id_fkey'),
        ('purchase_requisitions', 'purchase_requisitions_work_order_id_fkey'),
        ('rfq_suppliers', 'rfq_suppliers_quotation_id_fkey'),
        ('rfq_suppliers', 'rfq_suppliers_supplier_id_fkey'),
        ('rfqs', 'rfqs_awarded_po_id_fkey'),
        ('rfqs', 'rfqs_awarded_supplier_id_fkey'),
        ('rfqs', 'rfqs_material_request_id_fkey'),
        ('subcontract_order_lines', 'subcontract_order_lines_subcontract_order_id_fkey'),
        ('supplier_invoices', 'supplier_invoices_purchase_order_id_fkey'),
        ('supplier_invoices', 'supplier_invoices_supplier_id_fkey'),
        ('supplier_payments', 'supplier_payments_supplier_id_fkey'),
        ('supplier_quotations', 'supplier_quotations_rfq_id_fkey'),
        ('users', 'users_supplier_id_fkey'),
        ('work_order_materials', 'work_order_materials_work_order_id_fkey'),
        ('work_orders', 'work_orders_sales_order_line_id_fkey')
    ) AS constraints_to_validate(table_name, constraint_name)
    LOOP
        BEGIN
            EXECUTE format('ALTER TABLE public.%I VALIDATE CONSTRAINT %I',
                fk.table_name, fk.constraint_name);
        EXCEPTION WHEN foreign_key_violation THEN
            RAISE NOTICE 'Existing orphans: %.% remains NOT VALID',
                fk.table_name, fk.constraint_name;
        END;
    END LOOP;
END
$validate$;

COMMIT;

SELECT conrelid::regclass AS table_name, conname AS constraint_name
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace AND NOT convalidated
ORDER BY 1, 2;
