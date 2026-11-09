--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: work_order_priority; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.work_order_priority AS ENUM (
    'LOW',
    'NORMAL',
    'HIGH',
    'URGENT'
);


--
-- Name: work_order_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.work_order_status AS ENUM (
    'PLANNED',
    'RELEASED',
    'IN_PROGRESS',
    'COMPLETED',
    'CLOSED',
    'MATERIAL_PENDING',
    'MATERIAL_RESERVED',
    'MATERIAL_ISSUED',
    'IN_PRODUCTION',
    'QC_PENDING',
    'QC_APPROVED',
    'QC_REJECTED',
    'FG_RECEIVED',
    'REWORK',
    'REJECTED',
    'PRODUCTION_HOLD',
    'CANCELLED'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(255) NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid NOT NULL,
    tenant_id uuid,
    user_id uuid,
    action character varying(50) NOT NULL,
    entity_type character varying(100),
    entity_id uuid,
    before_value jsonb,
    after_value jsonb,
    ip_address character varying(45),
    correlation_id uuid,
    extra jsonb,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: background_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.background_jobs (
    id uuid NOT NULL,
    tenant_id uuid,
    job_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    payload jsonb,
    result jsonb,
    error text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batches (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    batch_number character varying(100) NOT NULL,
    quantity numeric(18,4) NOT NULL,
    expiry_date date,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    remaining_quantity numeric(18,4),
    location_id uuid,
    status character varying(20) DEFAULT 'in_stock'::character varying NOT NULL,
    original_quantity numeric(18,4),
    reserved_quantity numeric(18,4) DEFAULT 0 NOT NULL,
    consumed_quantity numeric(18,4) DEFAULT 0 NOT NULL,
    returned_quantity numeric(18,4) DEFAULT 0 NOT NULL
);


--
-- Name: bom_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bom_lines (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    bom_id uuid NOT NULL,
    material_id uuid,
    template_id uuid,
    variant_id uuid,
    quantity numeric(15,6) NOT NULL,
    scrap_percentage numeric(5,2) NOT NULL,
    unit_id uuid,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT chk_bom_line_component CHECK ((((
CASE
    WHEN (material_id IS NULL) THEN 0
    ELSE 1
END +
CASE
    WHEN (template_id IS NULL) THEN 0
    ELSE 1
END) +
CASE
    WHEN (variant_id IS NULL) THEN 0
    ELSE 1
END) = 1)),
    CONSTRAINT chk_bom_line_qty_positive CHECK ((quantity > (0)::numeric))
);


--
-- Name: bom_operations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bom_operations (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    bom_id uuid NOT NULL,
    operation_id uuid NOT NULL,
    sequence integer NOT NULL,
    is_deleted boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: boms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.boms (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    template_id uuid,
    variant_id uuid,
    version character varying(50) NOT NULL,
    is_active boolean NOT NULL,
    valid_from timestamp with time zone NOT NULL,
    valid_to timestamp with time zone,
    created_by uuid NOT NULL,
    approved_by uuid,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT chk_bom_product_target CHECK ((((template_id IS NOT NULL) AND (variant_id IS NULL)) OR ((template_id IS NULL) AND (variant_id IS NOT NULL))))
);


--
-- Name: chart_of_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chart_of_accounts (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(255) NOT NULL,
    account_type character varying(20) NOT NULL,
    category character varying(50),
    normal_balance character varying(10) NOT NULL,
    is_system boolean NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: client_addresses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client_addresses (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    client_id uuid NOT NULL,
    type character varying(20) NOT NULL,
    label character varying(100),
    contact_name character varying(255),
    address_line1 text NOT NULL,
    address_line2 text,
    city character varying(100),
    state character varying(100),
    postal_code character varying(30),
    country character varying(100),
    phone character varying(30),
    email character varying(255),
    is_default boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_client_addresses_type CHECK (((type)::text = ANY ((ARRAY['billing'::character varying, 'shipping'::character varying])::text[])))
);


--
-- Name: client_notification_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client_notification_settings (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    client_id uuid NOT NULL,
    user_id uuid NOT NULL,
    order_confirmed boolean DEFAULT true NOT NULL,
    order_shipped boolean DEFAULT true NOT NULL,
    order_delivered boolean DEFAULT true NOT NULL,
    invoice_overdue boolean DEFAULT true NOT NULL,
    low_credit boolean DEFAULT true NOT NULL,
    marketing boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: dashboard_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dashboard_metrics (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    metric_key character varying(100) NOT NULL,
    metric_value numeric(18,2) NOT NULL,
    period_start character varying(10) NOT NULL,
    period_end character varying(10) NOT NULL,
    metadata jsonb,
    cached_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    is_deleted boolean,
    deleted_at timestamp without time zone
);


--
-- Name: delivery_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.delivery_lines (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    delivery_order_id uuid NOT NULL,
    sales_order_line_id uuid NOT NULL,
    variant_id uuid NOT NULL,
    quantity numeric(18,4) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT delivery_lines_quantity_check CHECK ((quantity > (0)::numeric))
);


--
-- Name: delivery_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.delivery_orders (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    delivery_number character varying(50) NOT NULL,
    sales_order_id uuid NOT NULL,
    status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    carrier character varying(120),
    tracking_number character varying(120),
    shipped_at timestamp with time zone,
    delivered_at timestamp with time zone,
    notes text,
    created_by uuid NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    cancelled_at timestamp with time zone,
    cancelled_by uuid,
    cancellation_reason character varying(500),
    packed_at timestamp with time zone,
    CONSTRAINT ck_delivery_order_status CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'PACKING'::character varying, 'SHIPPED'::character varying, 'DELIVERED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: document_associations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_associations (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    revision_id uuid NOT NULL,
    work_order_id uuid,
    variant_id uuid,
    template_id uuid,
    is_print_package_included boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    work_order_line_id uuid,
    show_on_wo boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_document_association_target_exactly_one CHECK ((((work_order_id IS NOT NULL) AND (variant_id IS NULL) AND (template_id IS NULL)) OR ((work_order_id IS NULL) AND (variant_id IS NOT NULL) AND (template_id IS NULL)) OR ((work_order_id IS NULL) AND (variant_id IS NULL) AND (template_id IS NOT NULL))))
);


--
-- Name: document_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_revisions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    document_id uuid NOT NULL,
    file_attachment_id uuid NOT NULL,
    revision_code character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    notes character varying(1000),
    created_at timestamp with time zone NOT NULL,
    created_by_id uuid NOT NULL
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    document_type character varying(50) NOT NULL,
    entity_id uuid NOT NULL,
    version_number integer DEFAULT 1 NOT NULL,
    file_path character varying(500) NOT NULL,
    generated_by uuid,
    generated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: error_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.error_logs (
    id uuid NOT NULL,
    trace_id uuid NOT NULL,
    correlation_id character varying(36),
    tenant_id uuid,
    user_id uuid,
    ip_address character varying(45),
    path character varying(2048) NOT NULL,
    method character varying(10) NOT NULL,
    status_code integer NOT NULL,
    error_code character varying(50) NOT NULL,
    error_type character varying(255) NOT NULL,
    error_message character varying(500) NOT NULL,
    file_name character varying(255),
    line_number integer,
    stack_trace text,
    request_body text,
    request_body_truncated boolean NOT NULL,
    query_params jsonb,
    headers jsonb,
    "timestamp" timestamp with time zone NOT NULL
);


--
-- Name: failed_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.failed_tasks (
    id uuid NOT NULL,
    tenant_id uuid,
    task_name character varying(255) NOT NULL,
    arguments_json jsonb,
    error_message text NOT NULL,
    retry_count integer NOT NULL,
    failed_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: file_attachments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.file_attachments (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    file_size_bytes integer NOT NULL,
    content_type character varying(100) NOT NULL,
    cloudinary_public_id character varying(500) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    uploaded_by_id uuid NOT NULL
);


--
-- Name: financial_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.financial_transactions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    reference_type character varying(30) NOT NULL,
    reference_id uuid NOT NULL,
    account_type character varying(30) NOT NULL,
    debit numeric(15,2) NOT NULL,
    credit numeric(15,2) NOT NULL,
    description text,
    meta jsonb,
    created_by uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: goods_receipt_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.goods_receipt_notes (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    grn_number character varying(40) NOT NULL,
    purchase_order_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    scheduled_delivery_date timestamp with time zone,
    actual_receipt_date timestamp with time zone DEFAULT now() NOT NULL,
    warehouse_location_id uuid,
    status character varying(20) DEFAULT 'pending_receipt'::character varying NOT NULL,
    driver_name character varying(255),
    vehicle_number character varying(50),
    transport_company character varying(255),
    tracking_number character varying(100),
    remarks text,
    created_by uuid NOT NULL,
    updated_by uuid,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: grn_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grn_lines (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    grn_id uuid NOT NULL,
    po_line_id uuid NOT NULL,
    material_id uuid NOT NULL,
    po_quantity numeric(15,3) NOT NULL,
    received_quantity numeric(15,3) NOT NULL,
    accepted_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    rejected_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    unit_price numeric(18,4) NOT NULL,
    inventory_transaction_id uuid,
    remarks text,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: import_session_rows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import_session_rows (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    row_number integer NOT NULL,
    is_valid boolean NOT NULL,
    data_json jsonb NOT NULL,
    errors_json jsonb NOT NULL
);


--
-- Name: import_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import_sessions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    module character varying(50) NOT NULL,
    status character varying(30) NOT NULL,
    duplicate_strategy character varying(30) NOT NULL,
    total_rows integer NOT NULL,
    valid_rows integer NOT NULL,
    error_rows integer NOT NULL,
    duration_ms integer,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


--
-- Name: inspection_details; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inspection_details (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    inspection_id uuid NOT NULL,
    parameter character varying(255) NOT NULL,
    measured_value character varying(255),
    tolerance_min numeric(18,6),
    tolerance_max numeric(18,6),
    is_passed boolean DEFAULT false NOT NULL
);


--
-- Name: inspection_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inspection_templates (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    parameters jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: inventory_reservations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_reservations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    reference_type character varying(40) NOT NULL,
    reference_id uuid NOT NULL,
    material_id uuid NOT NULL,
    batch_id uuid,
    quantity numeric(15,3) NOT NULL,
    status character varying(20) DEFAULT 'RESERVED'::character varying NOT NULL,
    unit_id uuid,
    issued_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    consumed_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    returned_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: inventory_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_transactions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    transaction_type character varying(20) NOT NULL,
    quantity numeric(15,3) NOT NULL,
    unit_id uuid,
    from_location_id uuid,
    to_location_id uuid,
    reference_type character varying(50),
    reference_id uuid,
    remarks text,
    created_by uuid NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    batch_id uuid
);


--
-- Name: invoice_disputes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_disputes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    supplier_invoice_id uuid NOT NULL,
    disputed_amount numeric(15,2) NOT NULL,
    reason text NOT NULL,
    status character varying(20) DEFAULT 'open'::character varying NOT NULL,
    resolution_notes text,
    raised_by_supplier boolean DEFAULT true NOT NULL,
    resolved_by uuid,
    resolved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: invoice_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_lines (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    product_id uuid NOT NULL,
    product_type character varying(20) NOT NULL,
    description text,
    quantity integer NOT NULL,
    unit_price numeric(15,2) NOT NULL,
    discount_amount numeric(15,2) NOT NULL,
    tax_rate numeric(5,2) NOT NULL,
    tax_amount numeric(15,2) NOT NULL,
    total numeric(15,2) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: invoice_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.invoice_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoices (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_number character varying(50) NOT NULL,
    sales_order_id uuid,
    client_id uuid NOT NULL,
    client_name character varying(255) NOT NULL,
    client_address text,
    client_gst_number character varying(50),
    status character varying(20) NOT NULL,
    invoice_date date NOT NULL,
    due_date date NOT NULL,
    subtotal numeric(15,2) NOT NULL,
    discount_amount numeric(15,2) NOT NULL,
    tax_amount numeric(15,2) NOT NULL,
    grand_total numeric(15,2) NOT NULL,
    paid_amount numeric(15,2) NOT NULL,
    notes text,
    terms text,
    created_by uuid,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: item_code_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_code_sequences (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    item_type character varying(10) NOT NULL,
    category_id uuid NOT NULL,
    next_number integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: item_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_templates (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    category_id uuid,
    base_unit_id uuid,
    attributes jsonb NOT NULL,
    is_active boolean NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    code_locked boolean DEFAULT true NOT NULL
);


--
-- Name: item_variants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_variants (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    template_id uuid NOT NULL,
    code character varying(255) NOT NULL,
    name character varying(500) NOT NULL,
    variant_key character varying(500) NOT NULL,
    attribute_values jsonb NOT NULL,
    base_unit_id uuid,
    standard_cost numeric(18,4) NOT NULL,
    selling_price numeric(18,4),
    is_active boolean NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    material_id uuid,
    code_locked boolean DEFAULT true NOT NULL
);


--
-- Name: job_cards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_cards (
    id uuid NOT NULL,
    work_order_id uuid NOT NULL,
    operation_id uuid NOT NULL,
    sequence integer NOT NULL,
    assigned_to uuid,
    status character varying(20) NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    remarks text,
    pause_reason character varying(255),
    operator_notes text,
    paused_at timestamp with time zone,
    total_downtime_seconds numeric(15,3) DEFAULT 0 NOT NULL,
    produced_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    scrap_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    rework_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    rejected_quantity numeric(15,3) DEFAULT 0 NOT NULL
);


--
-- Name: journal_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.journal_entries (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    entry_number character varying(50) NOT NULL,
    entry_date date NOT NULL,
    reference_type character varying(50) NOT NULL,
    reference_id uuid NOT NULL,
    memo text,
    status character varying(20) NOT NULL,
    reverses_entry_id uuid,
    meta jsonb,
    created_by uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: journal_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.journal_lines (
    id uuid NOT NULL,
    journal_entry_id uuid NOT NULL,
    account_id uuid NOT NULL,
    description text,
    debit numeric(15,2) NOT NULL,
    credit numeric(15,2) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locations (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    type character varying(20) NOT NULL,
    parent_location_id uuid,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    code character varying(50)
);


--
-- Name: material_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_categories (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    description character varying,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    code_prefix character varying(20) DEFAULT 'GEN'::character varying NOT NULL
);


--
-- Name: material_consumption_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_consumption_records (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    work_order_id uuid NOT NULL,
    material_id uuid NOT NULL,
    production_record_id uuid,
    operation_id uuid,
    batch_id uuid,
    planned_quantity numeric(15,3) NOT NULL,
    actual_quantity numeric(15,3) NOT NULL,
    variance_quantity numeric(15,3) NOT NULL,
    scrap_quantity numeric(15,3) NOT NULL,
    unit_id uuid,
    recorded_by uuid NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    remarks character varying(500)
);


--
-- Name: material_import_mappings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_import_mappings (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    mapping_json text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: material_onboarding_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_onboarding_profiles (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    defaults_json text NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: material_onboarding_rows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_onboarding_rows (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    row_number integer NOT NULL,
    raw_json text NOT NULL,
    normalized_json text NOT NULL,
    validation_json text NOT NULL,
    protected_changes_json text NOT NULL,
    classification character varying(40) NOT NULL,
    status character varying(40) NOT NULL,
    result_material_id uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: material_onboarding_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_onboarding_sessions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    uploaded_by uuid NOT NULL,
    filename character varying(255) NOT NULL,
    status character varying(40) NOT NULL,
    dry_run boolean NOT NULL,
    protected_changes_confirmed boolean NOT NULL,
    original_headers_json text NOT NULL,
    mapping_json text NOT NULL,
    summary_json text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: material_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_requests (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    item_id uuid NOT NULL,
    item_type character varying(30) NOT NULL,
    required_quantity numeric(15,3) NOT NULL,
    fulfilled_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    required_by date,
    status character varying(20) DEFAULT 'open'::character varying NOT NULL,
    source_ref_type character varying(40),
    source_ref_id uuid,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT material_requests_item_type_check CHECK (((item_type)::text = ANY ((ARRAY['material'::character varying, 'product'::character varying])::text[]))),
    CONSTRAINT material_requests_status_check CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'partial'::character varying, 'fulfilled'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: material_shortages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_shortages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    work_order_id uuid NOT NULL,
    material_id uuid NOT NULL,
    required_quantity numeric(15,3) NOT NULL,
    available_quantity numeric(15,3) NOT NULL,
    shortage_quantity numeric(15,3) NOT NULL,
    status character varying(20) DEFAULT 'open'::character varying NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: materials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.materials (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description character varying,
    category_id uuid,
    base_unit_id uuid,
    material_type character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    current_stock numeric(18,4) NOT NULL,
    reserved_stock numeric(18,4) NOT NULL,
    reorder_level numeric(18,4),
    location_id uuid,
    is_batch_tracked boolean NOT NULL,
    is_serialized boolean NOT NULL,
    current_cost numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    inspection_required boolean DEFAULT false NOT NULL,
    inspection_template_id uuid,
    safety_stock numeric(18,4),
    lead_time_days integer,
    created_by uuid,
    updated_by uuid,
    code_locked boolean DEFAULT true NOT NULL,
    item_code character varying(50),
    length_uom character varying(20),
    length_per_unit numeric(18,4),
    weight_per_unit numeric(18,4),
    dimension_spec text,
    preferred_supplier_id uuid,
    hazardous_flag boolean DEFAULT false,
    qc_required_flag boolean DEFAULT false,
    barcode character varying(100),
    traceability_enabled boolean DEFAULT false,
    batch_rule character varying(50),
    expiry_tracking boolean DEFAULT false,
    shelf_life_days integer,
    quarantine_required boolean DEFAULT false,
    cuttable_inventory boolean DEFAULT false,
    remaining_quantity_tracking boolean DEFAULT false,
    reusable_remainder boolean DEFAULT false,
    decimal_precision integer,
    supplier_item_code character varying(100),
    purchase_uom character varying(20),
    min_stock numeric(18,4),
    max_stock numeric(18,4),
    reorder_quantity numeric(18,4),
    moq numeric(18,4)
);


--
-- Name: mrp_suggestions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mrp_suggestions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    material_code character varying(100) NOT NULL,
    material_name character varying(255) NOT NULL,
    gross_requirement numeric(18,4) DEFAULT 0 NOT NULL,
    current_stock numeric(18,4) DEFAULT 0 NOT NULL,
    open_po_qty numeric(18,4) DEFAULT 0 NOT NULL,
    reserved_stock numeric(18,4) DEFAULT 0 NOT NULL,
    net_requirement numeric(18,4) DEFAULT 0 NOT NULL,
    suggested_qty numeric(18,4) DEFAULT 0 NOT NULL,
    lead_time_days integer DEFAULT 7 NOT NULL,
    order_by_date date NOT NULL,
    need_by_date date NOT NULL,
    supplier_id uuid,
    supplier_name character varying(255) DEFAULT 'Unknown'::character varying NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    po_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: non_conformance_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.non_conformance_reports (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    inspection_id uuid,
    ncr_type character varying(20) NOT NULL,
    reason text,
    action_taken text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT non_conformance_reports_ncr_type_check CHECK (((ncr_type)::text = ANY ((ARRAY['rework'::character varying, 'scrap'::character varying, 'reject'::character varying])::text[])))
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid,
    title character varying(255) NOT NULL,
    message text NOT NULL,
    reference_type character varying(50),
    reference_id uuid,
    is_read boolean NOT NULL,
    notification_type character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    read_at timestamp with time zone,
    deep_link character varying(500),
    target_role character varying(50)
);


--
-- Name: number_series_audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.number_series_audit_log (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    entity_type character varying(30) NOT NULL,
    event_type character varying(30) NOT NULL,
    entity_id uuid,
    generated_code character varying(50),
    old_value character varying(500),
    new_value character varying(500),
    user_id uuid NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    metadata_json character varying
);


--
-- Name: number_series_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.number_series_config (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    entity_type character varying(30) NOT NULL,
    auto_generate boolean DEFAULT true NOT NULL,
    manual_override character varying(20) DEFAULT 'never'::character varying NOT NULL,
    prefix character varying(10) DEFAULT ''::character varying NOT NULL,
    include_abbreviation boolean DEFAULT false NOT NULL,
    abbreviation_length integer DEFAULT 3 NOT NULL,
    sequence_length integer DEFAULT 6 NOT NULL,
    separator character varying(5) DEFAULT '-'::character varying NOT NULL,
    lock_after_save boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: number_series_prefixes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.number_series_prefixes (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    entity_type character varying(30) NOT NULL,
    sub_type character varying(30) NOT NULL,
    prefix character varying(10) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: number_series_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.number_series_sequences (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    entity_type character varying(30) NOT NULL,
    prefix character varying(20) NOT NULL,
    next_number integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: operations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operations (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    workstation_id uuid,
    setup_time numeric(10,2) DEFAULT 0 NOT NULL,
    run_time numeric(10,2) DEFAULT 0 NOT NULL,
    description character varying,
    is_active boolean NOT NULL,
    is_deleted boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    operation_code character varying(10),
    operation_type character varying(32) DEFAULT 'other'::character varying,
    default_sequence integer DEFAULT 10,
    estimated_time_minutes numeric(10,2),
    qc_required boolean DEFAULT false,
    color character varying(20),
    icon_code character varying(50),
    created_by uuid,
    deleted_at timestamp with time zone
);


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(128) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: payment_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payment_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    payment_number character varying(50) NOT NULL,
    invoice_id uuid NOT NULL,
    client_id uuid NOT NULL,
    amount numeric(15,2) NOT NULL,
    payment_date date NOT NULL,
    payment_method character varying(30) NOT NULL,
    reference_number character varying(100),
    notes text,
    created_by uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: pick_list_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pick_list_lines (
    id uuid NOT NULL,
    pick_list_id uuid NOT NULL,
    material_id uuid NOT NULL,
    location_id uuid,
    quantity numeric(15,3) NOT NULL,
    sequence integer NOT NULL,
    batch_id uuid
);


--
-- Name: pick_lists; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pick_lists (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    work_order_id uuid NOT NULL,
    pick_list_number character varying(40) NOT NULL,
    warehouse_id uuid,
    status character varying(20) NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: po_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.po_number_sequences (
    tenant_id uuid NOT NULL,
    current_value integer DEFAULT 0 NOT NULL
);


--
-- Name: product_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_images (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    template_id uuid NOT NULL,
    variant_id uuid,
    file_name character varying(255) NOT NULL,
    file_path text NOT NULL,
    file_size integer NOT NULL,
    file_mime_type character varying(50) NOT NULL,
    image_order integer NOT NULL,
    is_primary boolean NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: production_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.production_records (
    id uuid NOT NULL,
    work_order_id uuid NOT NULL,
    produced_quantity numeric(15,3) NOT NULL,
    scrap_quantity numeric(15,3) NOT NULL,
    recorded_by uuid NOT NULL,
    notes text,
    recorded_at timestamp with time zone NOT NULL
);


--
-- Name: purchase_order_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchase_order_lines (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    purchase_order_id uuid NOT NULL,
    material_id uuid NOT NULL,
    quantity numeric(15,3) NOT NULL,
    received_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    unit_price numeric(18,4) DEFAULT 0 NOT NULL,
    line_total numeric(18,4) DEFAULT 0 NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT purchase_order_lines_quantity_check CHECK ((quantity > (0)::numeric)),
    CONSTRAINT purchase_order_lines_received_quantity_check CHECK ((received_quantity >= (0)::numeric))
);


--
-- Name: purchase_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchase_orders (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    po_number character varying(40) NOT NULL,
    supplier_id uuid NOT NULL,
    order_date date DEFAULT CURRENT_DATE NOT NULL,
    expected_delivery date,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    total_amount numeric(18,4) DEFAULT 0 NOT NULL,
    notes text,
    created_by uuid NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT purchase_orders_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'sent'::character varying, 'acknowledged'::character varying, 'partial'::character varying, 'received'::character varying, 'closed'::character varying])::text[])))
);


--
-- Name: purchase_requisitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchase_requisitions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    requisition_number character varying(50) NOT NULL,
    status character varying(30) DEFAULT 'PENDING_APPROVAL'::character varying NOT NULL,
    material_id uuid NOT NULL,
    work_order_id uuid,
    required_quantity numeric(15,3) NOT NULL,
    shortage_quantity numeric(15,3) NOT NULL,
    created_by uuid NOT NULL,
    approved_by uuid,
    linked_po_id uuid,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: quality_inspections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quality_inspections (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    reference_type character varying(40) NOT NULL,
    reference_id uuid NOT NULL,
    inspection_date date DEFAULT CURRENT_DATE NOT NULL,
    inspector_id uuid,
    result character varying(20) NOT NULL,
    remarks text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT quality_inspections_reference_type_check CHECK (((reference_type)::text = ANY ((ARRAY['purchase_receipt'::character varying, 'work_order'::character varying])::text[]))),
    CONSTRAINT quality_inspections_result_check CHECK (((result)::text = ANY ((ARRAY['pass'::character varying, 'fail'::character varying, 'rework'::character varying])::text[])))
);


--
-- Name: quarantine_releases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quarantine_releases (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    ncr_id uuid NOT NULL,
    released_by uuid,
    released_at timestamp with time zone DEFAULT now() NOT NULL,
    new_location_id uuid,
    reason text
);


--
-- Name: report_executions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_executions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    report_id uuid NOT NULL,
    executed_by uuid NOT NULL,
    export_format character varying(20) NOT NULL,
    execution_time_ms integer NOT NULL,
    row_count integer,
    file_url character varying(500),
    file_size_kb integer,
    status character varying(50),
    error_message text,
    created_at timestamp without time zone NOT NULL,
    is_deleted boolean,
    deleted_at timestamp without time zone
);


--
-- Name: report_schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_schedules (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    created_by uuid NOT NULL,
    report_id uuid NOT NULL,
    schedule_type character varying(50) NOT NULL,
    schedule_time character varying(5) NOT NULL,
    day_of_week character varying(20),
    day_of_month integer,
    recipients character varying[],
    is_active boolean,
    created_at timestamp without time zone NOT NULL,
    last_executed_at timestamp without time zone,
    is_deleted boolean,
    deleted_at timestamp without time zone
);


--
-- Name: rfq_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rfq_lines (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    rfq_id uuid NOT NULL,
    material_id uuid NOT NULL,
    quantity numeric(15,3) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: rfq_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rfq_number_sequences (
    tenant_id uuid NOT NULL,
    current_value bigint DEFAULT 0 NOT NULL
);


--
-- Name: rfq_suppliers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rfq_suppliers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    rfq_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    status character varying(20) DEFAULT 'invited'::character varying NOT NULL,
    quotation_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: rfqs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rfqs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    rfq_number character varying(40) NOT NULL,
    material_request_id uuid,
    title character varying(255),
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    deadline date,
    notes text,
    awarded_supplier_id uuid,
    awarded_po_id uuid,
    created_by uuid NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sales_clients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales_clients (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(255),
    phone character varying(20),
    address character varying(500),
    gst_number character varying(50),
    credit_limit numeric(18,4),
    credit_used numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    payment_terms_days integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    default_price_list_id uuid
);


--
-- Name: sales_order_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales_order_lines (
    id uuid NOT NULL,
    sales_order_id uuid NOT NULL,
    product_id uuid NOT NULL,
    product_type character varying(50) NOT NULL,
    uom_id uuid NOT NULL,
    quantity numeric(18,4) NOT NULL,
    unit_price numeric(18,4) NOT NULL,
    tax_rate numeric(5,2) DEFAULT '0'::numeric NOT NULL,
    tax_amount numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    line_total numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    allocated_quantity numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    shipped_quantity numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    backorder_quantity numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    work_order_id uuid,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    notes character varying(500),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    dispatched_quantity numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    line_status character varying(30) DEFAULT 'PENDING'::character varying NOT NULL,
    shortfall_quantity numeric(18,4) DEFAULT 0 NOT NULL,
    production_required boolean DEFAULT false NOT NULL
);


--
-- Name: sales_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales_orders (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    order_number character varying(50) NOT NULL,
    client_id uuid NOT NULL,
    order_date character varying NOT NULL,
    delivery_date character varying NOT NULL,
    status character varying(32) DEFAULT 'DRAFT'::character varying NOT NULL,
    payment_status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    subtotal numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    discount_amount numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    tax_amount numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    grand_total numeric(18,4) DEFAULT '0'::numeric NOT NULL,
    notes character varying(1000),
    created_by character varying(100),
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    approver_id uuid,
    submitted_at timestamp with time zone,
    approved_at timestamp with time zone,
    rejected_at timestamp with time zone,
    approval_notes character varying(1000),
    estimated_completion_date date,
    expected_dispatch_date date,
    expected_delivery_date date,
    confirmed_at timestamp with time zone,
    confirmed_by character varying(255),
    ready_at timestamp with time zone,
    priority character varying(20) DEFAULT 'NORMAL'::character varying NOT NULL,
    CONSTRAINT ck_sales_order_priority CHECK (((priority)::text = ANY ((ARRAY['LOW'::character varying, 'NORMAL'::character varying, 'HIGH'::character varying, 'URGENT'::character varying])::text[])))
);


--
-- Name: sales_price_list_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales_price_list_lines (
    id uuid NOT NULL,
    price_list_id uuid NOT NULL,
    product_id uuid NOT NULL,
    product_type character varying(50) NOT NULL,
    unit_price numeric(18,4) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: sales_price_lists; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales_price_lists (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: saved_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saved_reports (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    created_by uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    report_type character varying(50) NOT NULL,
    query_config jsonb NOT NULL,
    is_public boolean,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_deleted boolean,
    deleted_at timestamp without time zone
);


--
-- Name: serial_numbers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.serial_numbers (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    serial_number character varying(255) NOT NULL,
    status character varying(20) NOT NULL,
    current_location_id uuid,
    reference_id uuid,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: stock_ledger_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stock_ledger_entries (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    location_id uuid,
    transaction_date timestamp with time zone NOT NULL,
    transaction_type character varying(50) NOT NULL,
    quantity_change numeric(15,3) NOT NULL,
    running_balance numeric(15,3) NOT NULL,
    unit_cost numeric(18,4),
    total_value numeric(18,4),
    reference_type character varying(50),
    reference_id uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: stock_levels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stock_levels (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    location_id uuid NOT NULL,
    stock_status character varying(30) NOT NULL,
    quantity numeric(18,4) DEFAULT 0 NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT stock_levels_quantity_check CHECK ((quantity >= (0)::numeric)),
    CONSTRAINT stock_levels_stock_status_check CHECK (((stock_status)::text = ANY ((ARRAY['available'::character varying, 'pending_inspection'::character varying, 'quarantine'::character varying])::text[])))
);


--
-- Name: stock_reservations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stock_reservations (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    material_id uuid NOT NULL,
    location_id uuid,
    quantity numeric(15,3) NOT NULL,
    status character varying(20) NOT NULL,
    reference_type character varying(50),
    reference_id uuid,
    notes text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: subcontract_material_issues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subcontract_material_issues (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    subcontract_order_id uuid NOT NULL,
    material_id uuid NOT NULL,
    quantity numeric(15,3) NOT NULL,
    batch_number character varying(80),
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    batch_id uuid,
    returned_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    from_location_id uuid,
    issued_by uuid,
    CONSTRAINT subcontract_material_issues_quantity_check CHECK ((quantity > (0)::numeric))
);


--
-- Name: subcontract_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subcontract_number_sequences (
    tenant_id uuid NOT NULL,
    current_value integer DEFAULT 0 NOT NULL
);


--
-- Name: subcontract_order_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subcontract_order_lines (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    subcontract_order_id uuid NOT NULL,
    material_id uuid NOT NULL,
    required_quantity numeric(15,3) NOT NULL,
    issued_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    returned_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    consumed_quantity numeric(15,3) DEFAULT 0 NOT NULL
);


--
-- Name: subcontract_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subcontract_orders (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    order_number character varying(40) NOT NULL,
    supplier_id uuid NOT NULL,
    product_id uuid NOT NULL,
    product_type character varying(20) DEFAULT 'variant'::character varying NOT NULL,
    quantity numeric(15,3) NOT NULL,
    status character varying(30) DEFAULT 'draft'::character varying NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    bom_id uuid,
    due_date date,
    notes text,
    output_batch_id uuid,
    received_quantity numeric(15,3) DEFAULT 0 NOT NULL,
    created_by uuid,
    approved_by uuid,
    approved_at timestamp with time zone,
    CONSTRAINT subcontract_orders_product_type_check CHECK (((product_type)::text = ANY ((ARRAY['variant'::character varying, 'material'::character varying])::text[]))),
    CONSTRAINT subcontract_orders_quantity_check CHECK ((quantity > (0)::numeric)),
    CONSTRAINT subcontract_orders_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'materials_issued'::character varying, 'partially_received'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: supplier_invoice_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supplier_invoice_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supplier_invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_invoices (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_number character varying(50) NOT NULL,
    supplier_invoice_ref character varying(100),
    purchase_order_id uuid,
    supplier_id uuid NOT NULL,
    supplier_name character varying(255) NOT NULL,
    status character varying(20) NOT NULL,
    invoice_date date NOT NULL,
    due_date date NOT NULL,
    subtotal numeric(15,2) NOT NULL,
    tax_amount numeric(15,2) NOT NULL,
    grand_total numeric(15,2) NOT NULL,
    paid_amount numeric(15,2) NOT NULL,
    notes text,
    created_by uuid,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: supplier_payment_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supplier_payment_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supplier_payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_payments (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    payment_number character varying(50) NOT NULL,
    supplier_invoice_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    amount numeric(15,2) NOT NULL,
    payment_date date NOT NULL,
    payment_method character varying(30) NOT NULL,
    reference_number character varying(100),
    notes text,
    created_by uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: supplier_price_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_price_history (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    material_id uuid NOT NULL,
    unit_price numeric(18,4) NOT NULL,
    effective_from date DEFAULT CURRENT_DATE NOT NULL,
    effective_to date,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: supplier_quotations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supplier_quotations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    supplier_id uuid NOT NULL,
    purchase_order_id uuid,
    material_id uuid NOT NULL,
    quantity numeric(15,3) NOT NULL,
    unit_price numeric(18,4) NOT NULL,
    valid_until date,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    rfq_id uuid,
    quotation_number character varying(40) DEFAULT ''::character varying NOT NULL,
    CONSTRAINT supplier_quotations_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'submitted'::character varying, 'accepted'::character varying, 'rejected'::character varying])::text[])))
);


--
-- Name: suppliers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.suppliers (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    contact_person character varying(255),
    email character varying(255),
    phone character varying(50),
    address text,
    gst character varying(50),
    payment_terms character varying(100),
    performance_rating numeric(5,2),
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid
);


--
-- Name: technical_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.technical_documents (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    document_number character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    document_category character varying(50) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: tenant_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_audit_logs (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    action character varying(50) NOT NULL,
    reason text,
    acted_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: tenant_finance_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_finance_settings (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    invoice_prefix character varying(20) NOT NULL,
    supplier_invoice_prefix character varying(20) NOT NULL,
    payment_prefix character varying(20) NOT NULL,
    supplier_payment_prefix character varying(20) NOT NULL,
    invoice_template character varying(50) NOT NULL,
    default_tax_rate numeric(5,2) NOT NULL,
    default_payment_terms_days integer NOT NULL,
    gst_number character varying(50),
    logo_url character varying(500),
    custom_template jsonb,
    ar_account_code character varying(20) NOT NULL,
    bank_account_code character varying(20) NOT NULL,
    ap_account_code character varying(20) NOT NULL,
    revenue_account_code character varying(20) NOT NULL,
    expense_account_code character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: tenant_role_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_role_permissions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    role_id uuid NOT NULL,
    permission character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: tenant_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_roles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(50) NOT NULL,
    label character varying(100) NOT NULL,
    description text,
    is_system boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    plan character varying(50) DEFAULT 'starter'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    currency_code character varying(10),
    currency_symbol character varying(5),
    company_name character varying(255),
    logo_url character varying(500),
    gst_number character varying(50),
    address text,
    phone character varying(50),
    email character varying(255),
    footer_text text,
    signature_image_url character varying(500),
    timezone character varying(100),
    default_warehouse_name character varying(100),
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    is_system_tenant boolean DEFAULT false NOT NULL
);


--
-- Name: units_of_measure; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.units_of_measure (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(100) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    "precision" integer NOT NULL
);


--
-- Name: uom_conversions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uom_conversions (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    from_uom_id uuid NOT NULL,
    to_uom_id uuid NOT NULL,
    conversion_factor numeric(15,6) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: user_devices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_devices (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    device_fingerprint character varying(255) NOT NULL,
    device_name character varying(255),
    ip_address character varying(50),
    trusted_until timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    role character varying(50) DEFAULT 'operator'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    supplier_id uuid,
    client_id uuid,
    totp_secret character varying(32),
    totp_enabled boolean DEFAULT false NOT NULL,
    backup_codes jsonb DEFAULT '[]'::jsonb NOT NULL
);


--
-- Name: warehouse_zones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.warehouse_zones (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    warehouse_location_id uuid NOT NULL,
    zone_name character varying(100) NOT NULL,
    zone_type character varying(50) NOT NULL,
    capacity numeric(15,3),
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: wo_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wo_number_sequences (
    tenant_id uuid NOT NULL,
    current_value integer NOT NULL
);


--
-- Name: work_order_materials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_order_materials (
    id uuid NOT NULL,
    work_order_id uuid NOT NULL,
    material_id uuid NOT NULL,
    unit_id uuid NOT NULL,
    required_quantity numeric(15,3) NOT NULL,
    issued_quantity numeric(15,3) NOT NULL
);


--
-- Name: work_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_orders (
    id uuid NOT NULL,
    wo_number character varying(30) NOT NULL,
    tenant_id uuid NOT NULL,
    product_id uuid NOT NULL,
    bom_id uuid NOT NULL,
    sales_order_id uuid,
    planned_quantity numeric(15,3) NOT NULL,
    produced_quantity numeric(15,3) NOT NULL,
    scrap_quantity numeric(15,3) NOT NULL,
    status public.work_order_status NOT NULL,
    priority public.work_order_priority NOT NULL,
    start_date date NOT NULL,
    due_date date NOT NULL,
    notes text,
    created_by uuid NOT NULL,
    is_deleted boolean NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    sales_order_line_id uuid,
    hold_reason character varying(500),
    hold_started_at timestamp with time zone
);


--
-- Name: workstations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workstations (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    capacity_hours_per_day numeric(10,2) NOT NULL,
    hourly_rate numeric(14,2) NOT NULL,
    is_active boolean NOT NULL,
    is_deleted boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
c84cb0239a28
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, tenant_id, user_id, action, entity_type, entity_id, before_value, after_value, ip_address, correlation_id, extra, occurred_at) FROM stdin;
d2eb4d4d-f019-4ee3-8e5a-e356259c4386	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	1a985f72-2af6-4e03-b06d-823a8e92f04b	{"path": "/api/v1/documents/invoice/d94d0a9c-8975-4615-857f-0bd2137e61b3/generate", "method": "POST", "source": "http_write", "status_code": 500}	2026-08-16 22:40:11.476759+05:30
508e545e-df1f-48ae-8da8-3b51bdb78b3e	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	ac788438-7dc9-4010-9445-882d7544a0ba	{"path": "/api/v1/documents/invoice/d94d0a9c-8975-4615-857f-0bd2137e61b3/generate", "method": "POST", "source": "http_write", "status_code": 500}	2026-08-16 22:40:30.996242+05:30
09dd6e27-9799-4532-b7a8-3debffb87bb9	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	936ab3a6-42e1-4b62-946d-9911be7a824b	{"path": "/api/v1/products/9468e99f-757a-4a99-920e-758d967c9b2a/boms", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 17:55:08.864453+05:30
0bbbca75-8834-46b6-b72c-ca2a0d2515f1	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_CREATED	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	null	{"status": "draft", "po_number": "PO-20260929-0001", "line_count": 1, "supplier_id": "96ad7e79-2424-4d35-8960-c471b942ff16", "total_amount": 100.0}	127.0.0.1	84b42d5e-38af-47d9-bd42-4e1f6d40a274	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0001 created", "document_no": "PO-20260929-0001", "business_step": "Purchase order"}	2026-09-29 17:57:32.109366+05:30
a6638c2c-4f0a-454f-ac8e-129856b56b5b	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	purchase_order	\N	null	null	127.0.0.1	845abb61-84cd-4e26-9284-cf88c95541f8	{"path": "/api/v1/purchase-orders", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 17:57:32.168739+05:30
eaa274da-46ff-40f5-a17d-48eca65ebb7a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	baa1cd74-7fba-4f2d-9aad-25258c4f58b4	{"path": "/api/v1/inventory/material-onboarding/sessions", "method": "POST", "source": "http_write", "status_code": 201}	2026-10-01 14:55:46.240982+05:30
c508ba6f-3b7e-47a2-9491-0d38baa03242	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	5d9e6e6f-efb0-4e3f-ba5c-0beb2826ee51	{"path": "/api/v1/inventory/material-onboarding/sessions/f5227610-9ad4-4afd-bee3-9a35db48e8dc/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 14:59:19.60185+05:30
4c05aa8b-1e6e-49d5-b311-9f59ee88c2c2	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	8cfcdb3f-6ffc-49ff-961b-76d73bdafd0a	{"path": "/api/v1/documents/invoice/d94d0a9c-8975-4615-857f-0bd2137e61b3/generate", "method": "POST", "source": "http_write", "status_code": 200}	2026-08-16 22:42:41.686441+05:30
bffb8136-95b2-4738-ba6c-4a08840a1945	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	3854fe0b-6bab-413e-b1be-a96ab9c68c71	{"path": "/api/v1/documents/invoice/d94d0a9c-8975-4615-857f-0bd2137e61b3/generate", "method": "POST", "source": "http_write", "status_code": 200}	2026-08-16 22:42:49.806865+05:30
96af5100-f28f-426b-9276-926c368b2c74	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	e2e5b59c-0b7c-4710-8c01-86f2b57da470	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 18:55:41.122907+05:30
f55e39bd-a59a-4593-8073-08b7c9dd08ef	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_CREATED	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	null	{"status": "draft", "po_number": "PO-20260929-0002", "line_count": 1, "supplier_id": "96ad7e79-2424-4d35-8960-c471b942ff16", "total_amount": 40.0}	127.0.0.1	6df9c2a8-9c95-43dd-b98c-4513c7374a71	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0002 created", "document_no": "PO-20260929-0002", "business_step": "Purchase order"}	2026-09-29 17:58:07.594138+05:30
74ba431a-b86a-42f2-881a-273e909f9c4d	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	null	null	127.0.0.1	1852570e-f234-4de5-b082-79a0bbe6f91a	{"path": "/api/v1/purchase-orders/8876707a-a8a8-43b0-bbc9-ffc5b4d37a10/send", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 17:58:19.704111+05:30
fc697d2e-9eaf-4167-9f6e-eb5c36fa991b	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	549ec6f9-b689-42b9-84b2-67373659c01b	{"path": "/api/v1/subcontract/orders/4412fe8e-b123-4b2f-a766-b2d15db2c89e/issue", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 18:25:32.460299+05:30
35384047-c394-470e-b67f-37d1f55289d7	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	null	null	127.0.0.1	3fea164b-731a-4ec5-ac1f-2b65cdd9fdf5	{"path": "/api/v1/purchase-orders/d960f23e-c7ec-4cd3-95ec-88b01e3f4bab/send", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:27:39.91959+05:30
ecf3f8eb-d03c-473f-b332-23d5674ac94f	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	6926336e-794d-413e-8fbe-b08b28aa0207	{"path": "/api/v1/inventory/material-onboarding/sessions/f5227610-9ad4-4afd-bee3-9a35db48e8dc/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 14:56:52.514418+05:30
3e2eec2d-acb6-4f32-b672-beba1256e479	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_template	0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53	null	null	127.0.0.1	0724aeae-b067-4e27-ad8d-abd66bd72df2	{"path": "/api/v1/products/templates/0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53", "method": "PUT", "source": "http_write", "status_code": 200}	2026-08-16 22:43:55.691128+05:30
6c14ed57-cf7e-4933-a234-0ea8d1dff3d1	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	7f43ae46-587e-4ffb-b43d-465a65d40b95	{"path": "/api/v1/forgot-password/request", "method": "POST", "source": "http_write", "status_code": 200}	2026-08-23 23:50:31.052723+05:30
54c7cfa4-ad77-4e2a-a205-325cd7e9e7dd	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	0fe1a2d0-d1cf-4f31-97d1-45c01519b45b	{"path": "/api/v1/forgot-password/reset", "method": "POST", "source": "http_write", "status_code": 200}	2026-08-23 23:50:54.002911+05:30
7cb574df-2e95-4750-889e-3d99b5f0d16b	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	1250470c-96d9-4961-b222-31065a760e0c	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 401}	2026-08-23 23:51:31.787987+05:30
5b017e94-1b23-4692-80eb-f9bb035d3951	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	2efaf667-76f1-4e76-b0d9-7ee81db1ff8a	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 401}	2026-08-23 23:51:33.254796+05:30
88541da3-ee34-4f4d-955c-8735367585a3	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	0c829c99-4fce-484e-ad56-7e6b525a8e79	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 401}	2026-08-23 23:51:50.075175+05:30
970aaa0c-a4fb-4d68-901e-f7c644318ceb	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	d803c646-6988-4be5-acea-88cebf6d245f	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 401}	2026-08-23 23:51:53.010377+05:30
3f087718-8546-462c-89c8-81e3d1577e04	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	1624b0d0-9c8d-4494-b6d8-03b41aa7b5c4	{"path": "/api/v1/forgot-password/request", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-14 17:44:02.953549+05:30
693728a6-5258-416c-b6e6-90f329547634	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	e76a7b73-5fa7-41ef-b541-9f07bf4eefcd	{"path": "/api/v1/forgot-password/reset", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-14 17:44:20.337705+05:30
32888d4f-aa3f-4b0b-ab03-c5c225d594d1	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	a5b9453b-a4fb-44ea-8e0b-3a29ee247c9f	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-14 17:44:25.800906+05:30
69bc6472-fc5a-46c9-bfce-6b6947df88d5	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	427c301b-4a2f-4ba6-94ca-d64bea99ad63	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-25 20:36:12.723709+05:30
20891dc7-493d-4b30-bba8-90fafe0b1672	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	6d7f26b3-1cad-4900-9158-423183fc3d29	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 20:09:19.239414+05:30
d42f497e-2152-498f-8d1f-fb0cfc74f9e6	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	4674a9d2-6615-40a7-af7c-f7b902ac0734	null	null	127.0.0.1	f4c96f7c-14dc-4f74-96a1-64b2bf21ac69	{"path": "/api/v1/boms/4674a9d2-6615-40a7-af7c-f7b902ac0734", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-28 20:10:29.636968+05:30
ae8cd90e-9819-405f-9443-96563d4b02d8	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	cb82bfa1-c28d-4d84-bbd6-de0067536982	{"path": "/api/v1/products/8f8e2199-ffd0-412d-9f67-7636bca74a82/boms", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 20:12:00.319673+05:30
0ce6368f-54ac-43a1-9050-738f0b54ff59	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	purchase_order	\N	null	null	127.0.0.1	2aae5ac1-a04e-4db9-a73b-9b314123a573	{"path": "/api/v1/purchase-orders", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 17:58:07.667997+05:30
b9c8ab91-216b-4b1d-bfc4-878a7b9745c7	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	{"status": "draft"}	{"status": "sent"}	127.0.0.1	ae435e77-b657-497c-955c-977cefbaaac0	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0001 sent to supplier", "document_no": "PO-20260929-0001", "business_step": "Supplier collaboration"}	2026-09-29 17:58:19.621906+05:30
eaa14e78-6d17-4a06-9f94-553f860b67fc	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_CREATED	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	null	{"status": "draft", "po_number": "PO-20260929-0004", "line_count": 1, "supplier_id": "96ad7e79-2424-4d35-8960-c471b942ff16", "total_amount": 1000.0}	127.0.0.1	19c63ff4-fccc-4224-96b3-1bc7e5caa478	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0004 created", "document_no": "PO-20260929-0004", "business_step": "Purchase order"}	2026-09-29 18:27:27.316868+05:30
9ba3a566-4602-4b87-bab0-e6e843f00bfe	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	{"status": "draft"}	{"status": "sent"}	127.0.0.1	4c5e8ed3-558c-4c49-8e26-f25102d2cc24	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0002 sent to supplier", "document_no": "PO-20260929-0002", "business_step": "Supplier collaboration"}	2026-09-29 18:27:39.86473+05:30
ea1e8abb-1688-4b0c-a214-a5cc0e47837f	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	null	{"status": "received", "line_count": 1}	127.0.0.1	537ade7d-c735-47c1-b1b4-36e9ffffe40f	{"module": "procurement", "source": "business_event", "summary": "Goods received against PO PO-20260929-0002", "document_no": "PO-20260929-0002", "business_step": "Inventory receipt"}	2026-09-29 18:27:49.785147+05:30
b1b7a5ae-c8ed-4c54-991d-5ba40f5adf95	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	4019f0b3-0fbf-4323-bb05-416ce2c1ede6	{"path": "/api/v1/inventory/material-onboarding/sessions", "method": "POST", "source": "http_write", "status_code": 201}	2026-10-01 15:05:53.635729+05:30
5bb1f622-07d1-4be4-b847-8809ad52d674	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	91fee8e8-d394-44f7-b61d-fa4971690e16	{"path": "/api/v1/inventory/material-onboarding/sessions/25e78796-538e-47dd-82da-05d81a7b36fa/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 15:06:00.222084+05:30
99b55cde-80c5-4552-a085-f5529b6f5332	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	9987a192-72cc-4af5-9e14-086914ac8d18	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 19:29:28.391872+05:30
e9fc92d6-259d-4adc-8498-c3512ff7a141	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_template	0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53	null	null	127.0.0.1	ad0cd372-cfb5-4d55-95e2-f06b44677e2a	{"path": "/api/v1/products/templates/0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53", "method": "PUT", "source": "http_write", "status_code": 200}	2026-08-16 22:44:09.169626+05:30
119bf9a1-8063-4c7e-8fce-8525ad88de68	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	af48cb09-8296-42a9-a770-5c6f0e7ad639	{"path": "/api/v1/forgot-password/request", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-23 21:10:23.057731+05:30
6c242b49-3e29-4a8a-adae-108e60882cb7	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	ab22c53e-e84e-4eec-a098-c958b53a4bb9	{"path": "/api/v1/forgot-password/reset", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-23 21:10:33.47106+05:30
9d8bfd21-4b18-42cf-bc83-fc1069586848	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	5309f447-c1e3-4494-b720-3f919897e094	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-23 21:16:59.921445+05:30
20e98aa1-afc9-4060-bfab-2ff91fafa400	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	391eb233-4472-440b-8732-62d6f13b59f0	{"path": "/api/v1/technical-documents", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-25 20:37:46.423247+05:30
0e92bb84-6698-4826-8f3f-5e0c98e9a214	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	e7b03fc1-ab8c-4164-97a3-761bcc4ae481	{"path": "/api/v1/products/d18b4ef8-fa0e-47ec-bdf3-1dee4747286b/boms", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 20:09:45.820921+05:30
edca3948-77a2-4eac-a346-1c06e3d2a72a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	{"status": "sent"}	{"status": "acknowledged"}	127.0.0.1	455fbe04-5bfc-44bf-bc17-c8e24f4ae47c	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0001 acknowledged", "document_no": "PO-20260929-0001", "business_step": "Supplier collaboration"}	2026-09-29 17:58:24.301544+05:30
ee76c9d6-3944-4a8e-a05a-7a9298c6ff5b	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	null	{"status": "received", "line_count": 1}	127.0.0.1	4a540e9e-cdc6-49ad-a4ff-7193bf2d257f	{"module": "procurement", "source": "business_event", "summary": "Goods received against PO PO-20260929-0001", "document_no": "PO-20260929-0001", "business_step": "Inventory receipt"}	2026-09-29 17:58:29.310918+05:30
10a80b27-cd20-4fb0-98af-dce83e7f74d9	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	{"status": "sent"}	{"status": "acknowledged"}	127.0.0.1	a875583e-39e9-46bc-98ec-699c8d868c1b	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0002 acknowledged", "document_no": "PO-20260929-0002", "business_step": "Supplier collaboration"}	2026-09-29 18:27:41.633296+05:30
864a0bf7-be12-4cc5-95ca-3fe5e2738528	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	fc21bce9-94a7-4a21-bfd3-324c1fbf44ee	{"path": "/api/v1/inventory/material-onboarding/sessions", "method": "POST", "source": "http_write", "status_code": 201}	2026-10-01 15:08:54.623027+05:30
dbb6fb93-a1db-4b12-9a10-f58ac2121337	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	8da62ba8-2b35-4691-8b44-933379d99794	{"path": "/api/v1/inventory/material-onboarding/sessions/dd803e19-35ad-4811-a2ca-fff9b2a10fcf/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 15:08:59.411716+05:30
bc0a4bbb-e096-40c5-bca4-881dddfea3c6	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	ccb22b08-027b-41e6-b0d5-3f03a2c83162	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 20:31:05.678344+05:30
d343ca3d-e8f6-4fb0-8421-76b220bdd28b	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_template	be57c4d4-2106-4a78-856b-a385cadd90a4	null	null	127.0.0.1	97671d1e-a5c8-47ca-b4fd-eebd0b436ca4	{"path": "/api/v1/products/templates/be57c4d4-2106-4a78-856b-a385cadd90a4", "method": "PUT", "source": "http_write", "status_code": 200}	2026-08-16 22:45:20.16339+05:30
4b001bde-f79e-4170-8f08-d2d5c589586a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	e0f6fa2a-a99d-462c-94d4-79af5ecd2960	{"path": "/api/v1/technical-documents", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-23 21:52:19.765507+05:30
5f2ea937-1920-4f6c-8084-1515e25ceced	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	e20a7a0f-7d94-4ae4-b0c8-67d40ff3e6a3	{"path": "/api/v1/technical-documents/associations", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-23 21:52:19.921483+05:30
b840f0fb-eb04-4ce8-a92e-eed513833f10	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	c3eee90e-c182-4793-92a6-f616bad93934	{"path": "/api/v1/technical-documents/associations", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-25 20:37:46.594285+05:30
463cd56f-4ff2-4f98-b6c6-5e1990f5eed4	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	07ef4ef1-40d0-4934-a9ab-6a5e12805229	null	null	127.0.0.1	040d3380-7c07-4233-8e11-e239c65f7cea	{"path": "/api/v1/boms/07ef4ef1-40d0-4934-a9ab-6a5e12805229", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-28 20:15:18.797398+05:30
36c1318e-5295-4517-9909-b3b05a3a28f3	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	null	null	127.0.0.1	596685ed-c2d6-4b89-81d5-f634103bc4be	{"path": "/api/v1/purchase-orders/8876707a-a8a8-43b0-bbc9-ffc5b4d37a10/acknowledge", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 17:58:24.342248+05:30
a87ad81e-dc5b-463f-8954-c2f6fa46fd71	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	null	null	127.0.0.1	975e8c0d-6e39-4b89-bec5-454f40dd008f	{"path": "/api/v1/purchase-orders/8876707a-a8a8-43b0-bbc9-ffc5b4d37a10/receive", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 17:58:29.343465+05:30
47c1039e-1877-43ab-a968-78469e6a2f13	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	api_request	\N	null	null	127.0.0.1	0aaac526-df9f-4064-8c88-da03ae06c4c9	{"path": "/api/v1/inventory/materials/72723bde-d01b-4182-9517-bd64f80d3c5f", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 17:58:43.293492+05:30
414081bb-0d1c-4ff2-a6d1-dbd9e3089595	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	7c1d7914-1e43-4466-9f09-8ae08c4ac1df	{"path": "/api/v1/inventory/material-onboarding/sessions", "method": "POST", "source": "http_write", "status_code": 201}	2026-10-01 20:47:27.423838+05:30
6ea36f76-2c30-403c-bb63-0b01f50861a4	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	f389f67c-60d3-4fd6-a2c1-99f8f1119292	{"path": "/api/v1/inventory/material-onboarding/sessions/670a47db-3ea8-4edd-982e-93ed8ef8a2ff/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 20:47:31.772832+05:30
a3f08222-9820-4d72-a193-461fa39ea4da	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	e294110d-3809-4e48-82ab-c9c371de27ae	null	null	127.0.0.1	381e2030-911d-49eb-a3ed-e7ddb4989575	{"path": "/api/v1/boms/e294110d-3809-4e48-82ab-c9c371de27ae", "method": "PUT", "source": "http_write", "status_code": 200}	2026-08-16 22:50:52.063393+05:30
5d4e8731-94f6-445b-b9d2-7e339415a602	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	c6d9559e-f3be-4400-b693-acef647ed8f7	{"path": "/api/v1/products/8f8e2199-ffd0-412d-9f67-7636bca74a82/boms", "method": "POST", "source": "http_write", "status_code": 400}	2026-08-16 22:54:35.5354+05:30
d55aa844-300b-46e6-81f7-243041267e71	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	c4f0d03b-a4c8-458f-afc1-906500d7837b	{"path": "/api/v1/products/8f8e2199-ffd0-412d-9f67-7636bca74a82/boms", "method": "POST", "source": "http_write", "status_code": 400}	2026-08-16 22:54:53.675281+05:30
b5919c41-f035-4367-8213-caa22d8308ba	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	1fec5da0-5436-44b8-a616-2057c1f607a0	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-23 22:18:14.00614+05:30
3ce1aac3-0ed1-4656-a6de-ae7ab1ef999d	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	53ba4a76-88b5-408a-a3fe-ef5e75279237	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-25 22:59:50.254633+05:30
efecfb26-b8ee-4bde-af3a-05f696314fae	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	07ef4ef1-40d0-4934-a9ab-6a5e12805229	null	null	127.0.0.1	6319d3b1-b84e-4e89-97b8-127b6e9f7d35	{"path": "/api/v1/boms/07ef4ef1-40d0-4934-a9ab-6a5e12805229", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-28 20:16:56.624204+05:30
b1523062-e281-4048-84a6-e62c83fa5354	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	purchase_order	\N	null	null	127.0.0.1	3c1a1e7a-dac3-4bb8-be54-77cc99fec44e	{"path": "/api/v1/purchase-orders", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 18:27:27.350508+05:30
253946f3-c238-404d-8b91-29a05b1290a4	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	null	null	127.0.0.1	e50294b8-8151-489a-8c19-42318cc043ee	{"path": "/api/v1/purchase-orders/d960f23e-c7ec-4cd3-95ec-88b01e3f4bab/acknowledge", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:27:41.71958+05:30
5b631621-332c-4259-8b29-80e26a338e7a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	null	null	127.0.0.1	d4ef508b-c549-4c9e-b11b-5edfbbc80782	{"path": "/api/v1/purchase-orders/d960f23e-c7ec-4cd3-95ec-88b01e3f4bab/receive", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:27:49.845678+05:30
c3c24727-d54c-4952-998b-d5f52b0fc79d	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	5068142e-f1e4-4ce6-89a5-ebc4a5244af9	{"path": "/api/v1/inventory/material-onboarding/sessions", "method": "POST", "source": "http_write", "status_code": 201}	2026-10-01 20:50:00.099212+05:30
e48706bd-615c-4932-a918-62d79466e941	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	683de6ff-cabf-4908-9834-2af41308ed96	{"path": "/api/v1/inventory/material-onboarding/sessions/ff1605fe-b61b-400d-8008-42d56b031119/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 20:50:04.374479+05:30
2d45a6fe-318a-4a71-8b43-780c84fa4c08	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom_operation	e294110d-3809-4e48-82ab-c9c371de27ae	null	null	127.0.0.1	db16ce10-4a73-4344-800e-3897e8410ecd	{"path": "/api/v1/boms/e294110d-3809-4e48-82ab-c9c371de27ae/operations", "method": "POST", "source": "http_write", "status_code": 200}	2026-08-16 22:51:10.260168+05:30
4b08c8e0-cd16-4c71-b175-d22d08caf2b5	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	e294110d-3809-4e48-82ab-c9c371de27ae	null	null	127.0.0.1	90b0b8bb-1b90-48f4-a07c-786edee9d42f	{"path": "/api/v1/boms/e294110d-3809-4e48-82ab-c9c371de27ae/activate", "method": "POST", "source": "http_write", "status_code": 200}	2026-08-16 22:51:13.885393+05:30
714846eb-2e07-484f-8eb7-250cc8a87994	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	abab4f3f-e8b1-4dd9-b5ba-8c8e716a0043	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-26 16:14:49.217973+05:30
bd271926-fff9-4c52-b3e6-caa6cd825dc3	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	e5d51cd3-00c5-445a-9dbb-641108bb0975	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 21:11:15.252599+05:30
6d00fdc0-b053-4a1c-97bf-215c88fbc987	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	{"status": "draft"}	{"status": "sent"}	127.0.0.1	e0e77b58-e52a-41b2-9a6f-f8e53e45ecaa	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0004 sent to supplier", "document_no": "PO-20260929-0004", "business_step": "Supplier collaboration"}	2026-09-29 18:32:53.783945+05:30
882d7da7-48b1-42d6-9c4e-cbc9e6b98216	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	4178f2a6-994f-4024-bff9-a9f678199708	{"path": "/api/v1/inventory/material-onboarding/sessions/ff1605fe-b61b-400d-8008-42d56b031119/execute", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 20:50:07.107535+05:30
eabb8b84-3ade-4e81-a1c8-b2f259eb97b1	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	1a6314b4-62ec-401e-9225-8c1e07d2c8f1	{"path": "/api/v1/inventory/material-onboarding/sessions", "method": "POST", "source": "http_write", "status_code": 201}	2026-10-01 20:51:53.212003+05:30
bef25c45-fcd1-46b5-be09-8c3771137c91	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	c52e955a-e3c0-4233-9f5e-6be58f9982e9	{"path": "/api/v1/inventory/material-onboarding/sessions/8960bf77-87d3-4f2c-af55-21ec30b2d05e/execute", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 20:52:03.995787+05:30
336734c5-838b-4f48-9181-62926ff20d14	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_template	0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53	null	null	127.0.0.1	847369c7-b6be-494a-b5ef-a99e1eaccbb4	{"path": "/api/v1/products/templates/0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53", "method": "PUT", "source": "http_write", "status_code": 200}	2026-08-16 22:51:32.724131+05:30
838c1bb3-41cb-48b3-8292-0dcd27af55aa	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_template	be57c4d4-2106-4a78-856b-a385cadd90a4	null	null	127.0.0.1	daf31c6e-0e60-46c6-a0bd-e5d9e8f00ac1	{"path": "/api/v1/products/templates/be57c4d4-2106-4a78-856b-a385cadd90a4", "method": "PUT", "source": "http_write", "status_code": 200}	2026-08-16 22:52:52.991256+05:30
fe1abfd4-1185-4cd7-a49c-aa0e62a6c629	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	25a0cad0-d365-4f1f-b634-cce28ce25692	{"path": "/api/v1/products/templates", "method": "POST", "source": "http_write", "status_code": 201}	2026-08-16 22:54:27.698944+05:30
52bf0164-be69-44e0-81ec-bb4e124ca87f	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	5c94978c-362f-4fe5-9dd9-9b022c360a50	{"path": "/api/v1/products/8f8e2199-ffd0-412d-9f67-7636bca74a82/boms", "method": "POST", "source": "http_write", "status_code": 400}	2026-08-16 22:54:33.956207+05:30
9d7dcdfc-92e1-413b-9e59-da6944c956e0	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	6462ae09-b174-4044-93a2-614d0a5ad23a	{"path": "/api/v1/products/8f8e2199-ffd0-412d-9f67-7636bca74a82/boms", "method": "POST", "source": "http_write", "status_code": 400}	2026-08-16 22:54:55.57365+05:30
ce549e33-aef9-47ad-9713-9371772eef73	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	dc896077-eebc-4817-aa17-8d8c7c00b360	{"path": "/api/v1/technical-documents", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-26 16:50:57.707797+05:30
0c16b913-1101-4193-9016-91452651e6b1	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	6fac889d-cc30-4562-9d7a-8485879ecb50	null	null	127.0.0.1	556a7568-7516-4f42-88b1-fb2cdfa8998a	{"path": "/api/v1/boms/6fac889d-cc30-4562-9d7a-8485879ecb50", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-28 21:13:14.876761+05:30
06cdce31-d4db-405c-b9b3-b7daf8c3701e	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	null	null	127.0.0.1	dedb23b0-ca9a-46cd-a14f-6a16ee045cbb	{"path": "/api/v1/purchase-orders/13ee59cc-e503-43d4-83dc-44eaa53b5172/send", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:32:53.869983+05:30
e9112ca2-c3f8-487b-bb36-978ca3a3a01d	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	{"status": "sent"}	{"status": "acknowledged"}	127.0.0.1	089e8cfd-945b-468c-b4ea-c5e4eff332da	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0004 acknowledged", "document_no": "PO-20260929-0004", "business_step": "Supplier collaboration"}	2026-09-29 18:32:56.161988+05:30
9feab633-a7ff-45df-85c1-811a439c7ec2	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	null	{"status": "received", "line_count": 1}	127.0.0.1	12feeaa8-39f8-4f66-a6e8-b47cda0155f4	{"module": "procurement", "source": "business_event", "summary": "Goods received against PO PO-20260929-0004", "document_no": "PO-20260929-0004", "business_step": "Inventory receipt"}	2026-09-29 18:33:04.744546+05:30
414761d0-0586-4eb0-a43d-23ae12274815	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	api_request	\N	null	null	127.0.0.1	7b09cd72-99ca-43c5-bd7c-1d4d4947fe29	{"path": "/api/v1/inventory/materials/55c87cf5-af2f-4204-a575-2a1e8523e075", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:33:42.762594+05:30
24f7ebb1-e713-4789-994d-f48a36c9cab4	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	{"status": "draft"}	{"status": "sent"}	127.0.0.1	630f6f2e-e47f-4fbf-bca8-ef0de744df0e	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0007 sent to supplier", "document_no": "PO-20260929-0007", "business_step": "Supplier collaboration"}	2026-09-29 18:35:04.025307+05:30
e28821bb-9d77-4924-9196-9da9a5e2192b	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	68a8e6ab-6979-42cb-87bd-7257dccb92cd	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 18:47:53.354272+05:30
bd4ae02f-e996-4d91-b0c3-7883b7989af4	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	2e21ff06-63bb-4468-b05a-d4d3ed21e915	{"path": "/api/v1/inventory/material-onboarding/sessions/8960bf77-87d3-4f2c-af55-21ec30b2d05e/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 20:51:59.244799+05:30
afa232f6-09fe-41ee-b955-5143e2c75c08	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	c062e7fc-6751-4972-a391-a7bbe0ce5c3c	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-26 17:42:57.891937+05:30
9e786a7a-8c8e-4faa-9f69-40fc12002925	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_variant	6168bef7-18d4-4030-9b52-343c5f56700d	null	null	127.0.0.1	c0d087e6-2a8c-4397-80d6-21e1bafdb131	{"path": "/api/v1/products/variants/6168bef7-18d4-4030-9b52-343c5f56700d", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-28 21:24:38.797391+05:30
b474cd44-db96-4e0c-9c98-f685aa103336	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	null	null	127.0.0.1	f8384021-8c18-4e40-a5d8-c1507fc23086	{"path": "/api/v1/purchase-orders/13ee59cc-e503-43d4-83dc-44eaa53b5172/acknowledge", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:32:56.306129+05:30
9a68ca86-fc92-43ad-8893-70a372bc4cf8	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	null	null	127.0.0.1	46b3b6ff-96f9-4152-9421-a4756aeb084b	{"path": "/api/v1/purchase-orders/13ee59cc-e503-43d4-83dc-44eaa53b5172/receive", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:33:04.784665+05:30
dea39778-6190-4a53-b484-00b0743b3979	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	bb37299c-9d96-456f-a635-e21abe641d23	{"path": "/api/v1/subcontract/orders/4412fe8e-b123-4b2f-a766-b2d15db2c89e/issue", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 18:34:25.36587+05:30
fcdaf1ab-9547-4063-bbe3-b2c9e15f886d	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	purchase_order	\N	null	null	127.0.0.1	b95ff649-a968-460f-b343-ef4766300dbf	{"path": "/api/v1/purchase-orders", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 18:34:57.893414+05:30
4f6bf979-607f-4110-b5b3-832db7449975	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_SENT	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	null	null	127.0.0.1	9027ee58-c243-4480-8c62-2d325f0956fe	{"path": "/api/v1/purchase-orders/360f4ed6-0526-445c-abeb-250977dfe563/send", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:35:04.068123+05:30
dd036562-ebe9-4555-aeb0-9157336aefaa	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	null	{"status": "received", "line_count": 1}	127.0.0.1	4a2523ba-845c-434b-a56f-d40fd5a2db35	{"module": "procurement", "source": "business_event", "summary": "Goods received against PO PO-20260929-0007", "document_no": "PO-20260929-0007", "business_step": "Inventory receipt"}	2026-09-29 18:35:14.55009+05:30
f1070251-db0d-498a-b8b2-36528c0ede1d	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	00c0e796-be91-40a4-8156-d60eb9953a47	{"path": "/api/v1/subcontract/orders/4412fe8e-b123-4b2f-a766-b2d15db2c89e/receive", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 19:30:36.805861+05:30
1457433a-efed-4c85-bfa1-4ea053e41347	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	121ba898-3f5e-49fa-aa9a-b263770131a9	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 21:58:13.891011+05:30
5244d1e2-742b-4746-acbd-23557f65c855	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	af8bf141-2525-4247-837e-6a3fb62ea04c	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-27 15:02:10.786777+05:30
4a493dc7-c474-4278-9929-28f07652486b	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	f58aa73b-caec-47ea-b06a-599ec37003c9	{"path": "/api/v1/products/templates", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 21:28:19.208468+05:30
d7f39a8e-4bec-485f-af7a-9fb184c6d594	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_variant	ecc099e8-ce13-4f0c-a3ee-7ee972dfd2f7	null	null	127.0.0.1	8705639f-ba44-447b-a15a-e1481f1791d6	{"path": "/api/v1/products/variants/ecc099e8-ce13-4f0c-a3ee-7ee972dfd2f7", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-28 21:32:00.649145+05:30
6f7083e9-d8be-4256-b8c3-8dfe89382363	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	item_variant	\N	null	null	127.0.0.1	b5f6b2ef-e0b5-44ac-ad1d-8be9d96532d4	{"path": "/api/v1/products/templates/80d74378-f5a5-4a83-933c-35ee9a82bd51/variants", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 21:49:55.633102+05:30
35df578e-a67f-4a53-b4e6-b5e5b6ce8b1a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_CREATED	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	null	{"status": "draft", "po_number": "PO-20260929-0007", "line_count": 1, "supplier_id": "96ad7e79-2424-4d35-8960-c471b942ff16", "total_amount": 100.0}	127.0.0.1	0b0eae89-9285-4d48-b20a-e4ffbc1d5d3a	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0007 created", "document_no": "PO-20260929-0007", "business_step": "Purchase order"}	2026-09-29 18:34:57.819156+05:30
3eff3a1e-b494-4fec-be8e-f5dec88ba3fc	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_RECEIVED	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	null	null	127.0.0.1	9cd14a4f-aa7b-4fa5-9d2d-cc14aad50a50	{"path": "/api/v1/purchase-orders/360f4ed6-0526-445c-abeb-250977dfe563/receive", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:35:14.601873+05:30
402af068-8bf5-4e5a-a9c3-bd5262b1014e	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	api_request	\N	null	null	127.0.0.1	37293f6d-a053-42d4-92a6-0a42f4925633	{"path": "/api/v1/inventory/materials/626920a3-a4e1-41ca-af9f-fb9e2631a46f", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:35:16.556761+05:30
d8288b30-3cc3-4aa3-ad26-964070a859cf	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	e9f56b18-ff12-4173-9697-656eb1fd8795	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-03 18:15:50.265995+05:30
dbbf330a-1aad-421b-9d6f-0c2e35bd72ed	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	303185f0-9ea6-4591-be2c-5acacdc4b9fe	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-27 17:45:36.062397+05:30
5bb16f5c-826c-4906-9d4e-7fd0e3d8a9c5	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	item_variant	\N	null	null	127.0.0.1	88329f1b-92f6-4349-92e6-a6b6998d9e82	{"path": "/api/v1/products/templates/145fed75-cb52-4e0d-9407-9e9de3493e13/variants", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 21:29:02.236388+05:30
cecb7988-86f6-47a6-97ed-9dc49d44831d	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	d697ea3a-6784-4b25-befa-19f828775973	{"path": "/api/v1/products/templates", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 21:32:43.855565+05:30
c5ecef04-baf6-4dd0-8a97-18c6ca614ea0	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	{"status": "sent"}	{"status": "acknowledged"}	127.0.0.1	06d15e7b-56bf-4ad1-b941-235ffd21d162	{"module": "procurement", "source": "business_event", "summary": "Purchase order PO-20260929-0007 acknowledged", "document_no": "PO-20260929-0007", "business_step": "Supplier collaboration"}	2026-09-29 18:35:05.584257+05:30
a273b8b0-eaf5-4b41-aecb-137d95268fc7	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	1efe0b60-b4ce-4112-a380-66fc42b2bfaf	{"path": "/api/v1/subcontract/orders/4412fe8e-b123-4b2f-a766-b2d15db2c89e/issue", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 18:35:30.258708+05:30
d000f427-9a19-448d-8314-a9eac2aa2cfc	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	780623fb-ecc4-4002-9da1-2ef33ee90ecd	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-27 19:37:22.717987+05:30
c4e68444-d1da-4895-bd7d-ccd536b72037	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	item_variant	\N	null	null	127.0.0.1	966fd6ec-1f08-4e38-8206-404a12eaa11b	{"path": "/api/v1/products/templates/80d74378-f5a5-4a83-933c-35ee9a82bd51/variants", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 21:33:16.115614+05:30
368e9d5c-08d2-48b2-8999-317aefe160e9	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	PO_ACKNOWLEDGED	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	null	null	127.0.0.1	4baa3dc0-29da-452e-b549-e550bddf1ab1	{"path": "/api/v1/purchase-orders/360f4ed6-0526-445c-abeb-250977dfe563/acknowledge", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 18:35:05.629028+05:30
d18bd1b3-913c-451f-a411-271da098235f	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	5c7f36fb-901f-4061-8433-56aa3fa966ac	{"path": "/api/v1/inventory/materials", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-27 19:57:25.204064+05:30
e0207c3b-b2be-4878-9128-220c4ba06d16	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	d0c457fe-0a6d-436f-a1d7-5a654753062b	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 22:12:42.217897+05:30
f78ccba0-7ca1-4af7-aee1-aa5bbb5e71e5	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	f215031c-0872-47ff-9ba7-083c320e835c	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 22:06:20.874518+05:30
3ad8bf68-6ff4-4d9d-b3e4-2d62715e104f	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	2d27644b-9a62-489f-853b-fa77cbf8a9c6	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-27 21:43:23.531113+05:30
78377a3c-0327-4119-8a74-2e7941cc054f	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	c0a863f5-b8c1-40d7-a99a-93955a5b8de5	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 14:26:58.465289+05:30
943edb51-14e2-48e5-a63f-64c224c8d8a0	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	999899db-aaa8-4e02-aefd-475295a9c64b	null	null	127.0.0.1	ae3f2a2b-1b39-4cb4-bee8-3402e3376911	{"path": "/api/v1/boms/999899db-aaa8-4e02-aefd-475295a9c64b", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 14:44:34.488036+05:30
62590e7e-c4fa-415e-b561-4fc4aa0fe29a	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	abddad92-d6e4-488a-8fe3-3117b47d2aca	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 22:09:44.2355+05:30
76afea48-d760-4ab4-9395-d551f6334602	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	7189ec41-69ec-4b27-8872-d9e10b81d5c3	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 13:44:49.604822+05:30
5a948980-2c38-4ed4-85cd-16a6ee6df4c5	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_variant	6168bef7-18d4-4030-9b52-343c5f56700d	null	null	127.0.0.1	620e37e7-a8e3-4ce6-8ff7-290af9e8f3a0	{"path": "/api/v1/products/variants/6168bef7-18d4-4030-9b52-343c5f56700d", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 14:42:00.37674+05:30
5a8acf7a-2c03-4785-aa8d-d84c72d8b923	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	item_template	9468e99f-757a-4a99-920e-758d967c9b2a	null	null	127.0.0.1	9c116a36-0ea5-488d-b629-06cab0c9cdcd	{"path": "/api/v1/products/templates/9468e99f-757a-4a99-920e-758d967c9b2a", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 14:42:05.218621+05:30
f6a04b60-a2bc-4c4f-9046-3192339be411	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	3936d385-f8a3-4c07-b67a-525d317e1762	{"path": "/api/v1/inventory/materials", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 14:43:26.129429+05:30
07bcb26f-354a-4792-89fb-ca0b9dd30d5f	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	02b0c1bc-744e-45f0-8c08-b0a2e702bafc	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-30 13:51:31.300058+05:30
98a002bc-d2bb-41ce-949d-41bc707a890c	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	98e94ff2-3b30-4a50-aad8-916a26ecbe70	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 15:53:07.770678+05:30
d5816065-484a-4026-a8f1-aeacb2c75b67	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	9da2e772-b318-4fc6-9ade-06665daecd7b	{"path": "/api/v1/inventory/materials", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 14:43:11.203498+05:30
b1d79bc1-5e57-4bd3-9936-0dcb7e55f888	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	999899db-aaa8-4e02-aefd-475295a9c64b	null	null	127.0.0.1	56734a17-17f3-46a4-9eae-85e20247d881	{"path": "/api/v1/boms/999899db-aaa8-4e02-aefd-475295a9c64b", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 14:44:25.152807+05:30
82f213da-8f91-4978-8596-9bf58b296cc8	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	4ebc5704-56ae-4464-b635-29b16d34667d	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 13:41:52.178461+05:30
5160e27a-98bb-4491-8abf-22a0cc588144	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	bbacaf37-1df9-4429-b6cd-dfff9271020b	{"path": "/api/v1/inventory/materials", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 15:54:12.659843+05:30
1d4399a5-5650-4fa3-91c6-be132f0d97d4	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	319d2c46-419b-4ca2-a097-28eb09b0ddf7	{"path": "/api/v1/products/templates", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 15:56:05.753824+05:30
da2b1fc3-3050-43fc-8b85-7012dc726bbc	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	6c11498a-1427-415b-8cf0-8fb2dd6f9c88	{"path": "/api/v1/inventory/materials", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 14:43:44.575931+05:30
2058f3ed-cc7f-4c98-8d5b-5eece312f644	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	999899db-aaa8-4e02-aefd-475295a9c64b	null	null	127.0.0.1	1bb0c510-c325-4a9c-bf06-64261844453d	{"path": "/api/v1/boms/999899db-aaa8-4e02-aefd-475295a9c64b/activate", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 14:45:01.918786+05:30
795af907-fd0a-428e-9d91-bb459ef0a276	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	2a5c7fae-ecc4-474b-8e9a-1e5622fb571e	{"path": "/api/v1/subcontract/orders", "method": "POST", "source": "http_write", "status_code": 201}	2026-10-01 13:47:40.705205+05:30
80e6e5c3-029f-4e63-b6c9-4841ceddefa8	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	443b47b8-5be3-4527-8f61-523eaf98c691	{"path": "/api/v1/subcontract/orders/4798a3c4-8865-47af-9fc4-539f4742c39d/issue", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 13:51:21.361686+05:30
4cefb754-9552-4b0a-923f-ded218975c49	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	item_variant	\N	null	null	127.0.0.1	52124e10-e0f9-465f-9070-76fae289fb83	{"path": "/api/v1/products/templates/9468e99f-757a-4a99-920e-758d967c9b2a/variants", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 15:57:37.003795+05:30
d066d3dd-9efe-4577-a382-5ace6a02ccdf	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	999899db-aaa8-4e02-aefd-475295a9c64b	null	null	127.0.0.1	139ce3b2-c6dd-4f35-86be-d6a1b0cf7974	{"path": "/api/v1/boms/999899db-aaa8-4e02-aefd-475295a9c64b", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-29 14:44:43.97594+05:30
9f31df44-612f-499b-9808-e47706556992	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	b87c7133-8676-4c89-81c9-9cb8d59a188a	{"path": "/api/v1/subcontract/orders", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-29 14:46:34.420341+05:30
d525448f-9157-45b9-a8a9-a693b842027f	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	b97c7bfc-eb4b-4e89-93e5-3fa8d6abd1d3	{"path": "/api/v1/subcontract/orders/4798a3c4-8865-47af-9fc4-539f4742c39d/approve", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 13:48:01.264473+05:30
31661089-41b4-44ee-9f00-a5558feda9fd	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	ec369271-f4b5-45d8-9a67-4b7f928ef079	{"path": "/api/v1/subcontract/orders/4798a3c4-8865-47af-9fc4-539f4742c39d/receive", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 13:54:15.611058+05:30
7dd37a3e-ca75-410a-8d70-4f5652e8ad3d	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	d377a579-0f6c-48fa-ae65-0039bc7fdac2	{"path": "/api/v1/products/9468e99f-757a-4a99-920e-758d967c9b2a/boms", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 15:58:01.300306+05:30
9e78a015-7e24-4436-bc7a-0e477d024853	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	d347d10c-300f-4a1b-8b84-a3cfbc4beb28	null	null	127.0.0.1	8564a737-0744-4768-a881-06369244d2be	{"path": "/api/v1/boms/d347d10c-300f-4a1b-8b84-a3cfbc4beb28/activate", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 15:58:32.320601+05:30
9ed0d9bc-dbdb-432b-bcb1-fe80f3ae3172	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	7c0daae2-4b5d-4870-9e79-b61feed5f7cf	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 16:15:39.776037+05:30
57b924e4-755a-4e7e-9a94-2667db17ba6a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	610a7955-57dd-47d8-8328-b840843e015c	{"path": "/api/v1/subcontract/orders/4798a3c4-8865-47af-9fc4-539f4742c39d/issue", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 13:51:05.809559+05:30
bae5c7c5-7dab-43cb-b5ad-35aba89bc678	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	UPDATE	bom	d347d10c-300f-4a1b-8b84-a3cfbc4beb28	null	null	127.0.0.1	9fd32a5a-d646-4368-8345-69a0ff350ff5	{"path": "/api/v1/boms/d347d10c-300f-4a1b-8b84-a3cfbc4beb28", "method": "PUT", "source": "http_write", "status_code": 200}	2026-09-28 15:58:15.922381+05:30
27fa9e24-7b27-4890-8dd3-147651b55149	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	38efeb20-7fb8-4649-a2ee-031293e95e1b	{"path": "/api/v1/subcontract/orders/4412fe8e-b123-4b2f-a766-b2d15db2c89e/approve", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 16:34:57.953937+05:30
b9d4ca63-2029-4b7d-a980-230feb3b9186	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	41ba0f68-813b-40f3-a77e-0c2b0b31d071	{"path": "/api/v1/subcontract/orders/4798a3c4-8865-47af-9fc4-539f4742c39d/issue", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 13:51:36.314756+05:30
48bbc879-3410-47fb-99ca-904f81cbdac7	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	3e6fcdea-b543-4fe1-8fed-39f97ad91eff	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-28 17:14:20.004573+05:30
d357573c-97c1-427c-913e-e2379a542f9c	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	bom	\N	null	null	127.0.0.1	1e7a2133-4679-4021-bcaa-0500841472f0	{"path": "/api/v1/products/9468e99f-757a-4a99-920e-758d967c9b2a/boms", "method": "POST", "source": "http_write", "status_code": 201}	2026-09-28 17:15:13.194167+05:30
09f57031-4090-4705-9c36-1230ad172077	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	b071b285-df27-4a0c-975f-b76968b59a84	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-09-29 17:47:42.021481+05:30
5b5a5639-8f7f-4cf0-bd03-eac6c859ffa4	\N	\N	CREATE	api_request	\N	null	null	127.0.0.1	cea39702-568b-443e-bb3d-4b2ca7eb780c	{"path": "/api/v1/auth/login", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 14:50:11.410233+05:30
598bfd72-3112-445c-8f6a-435267ebe781	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	525b214a-0915-41d6-9ecb-1e924a6dee97	{"path": "/api/v1/inventory/material-onboarding/sessions/f5227610-9ad4-4afd-bee3-9a35db48e8dc/validate", "method": "POST", "source": "http_write", "status_code": 200}	2026-10-01 14:58:52.536333+05:30
62744c70-46b2-4822-b37c-0351997a53e5	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CREATE	api_request	\N	null	null	127.0.0.1	bc27e754-287f-47d1-b80d-916137057456	{"path": "/api/v1/documents/invoice/d94d0a9c-8975-4615-857f-0bd2137e61b3/generate", "method": "POST", "source": "http_write", "status_code": 500}	2026-08-16 22:37:48.607107+05:30
\.


--
-- Data for Name: background_jobs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.background_jobs (id, tenant_id, job_type, status, payload, result, error, started_at, completed_at, created_at) FROM stdin;
\.


--
-- Data for Name: batches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.batches (id, tenant_id, material_id, batch_number, quantity, expiry_date, is_deleted, deleted_at, created_at, updated_at, remaining_quantity, location_id, status, original_quantity, reserved_quantity, consumed_quantity, returned_quantity) FROM stdin;
70f2f536-55ca-4d7b-a039-fa6945235031	df413048-964e-45da-af55-91e90d7c54ee	b2876e59-29fe-4c9b-86a6-be45d3a6c479	SCO-SCO-20260929-0001	1.0000	\N	f	\N	2026-09-29 19:30:36.513981+05:30	2026-09-29 19:30:36.514007+05:30	1.0000	a7054e96-1ae5-4800-b414-d556c437b796	in_stock	1.0000	0.0000	0.0000	0.0000
0ff6d195-7859-49fb-904f-836b878de529	df413048-964e-45da-af55-91e90d7c54ee	b2876e59-29fe-4c9b-86a6-be45d3a6c479	SCO-SCO-20261001-0002	2.0000	\N	f	\N	2026-10-01 13:54:15.348822+05:30	2026-10-01 13:54:15.348829+05:30	2.0000	a7054e96-1ae5-4800-b414-d556c437b796	in_stock	2.0000	0.0000	0.0000	0.0000
\.


--
-- Data for Name: bom_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bom_lines (id, tenant_id, bom_id, material_id, template_id, variant_id, quantity, scrap_percentage, unit_id, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
8a002b3a-bd06-4f0a-b8b4-bd206b57838e	1e26d822-336a-4caf-b726-d5bc873bcd47	da32a5b5-375f-4b8f-b40f-a680cb109103	e2c1deee-51be-4698-8c4c-20aa0d7b027d	\N	\N	2.000000	0.00	533498de-dc4d-4842-840c-43ddc8206c9a	f	\N	2026-07-25 15:24:37.067691+05:30	2026-07-25 15:24:37.067691+05:30
6b0f0b1a-d57c-4e66-9218-9e33438ad59b	df413048-964e-45da-af55-91e90d7c54ee	1b22fd6c-0b9f-4ed8-8f4c-675996dd6b78	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	\N	1.000000	0.00	18f11e18-dd91-45f5-8ac1-2340161e2a4e	f	\N	2026-08-16 20:00:33.52847+05:30	2026-08-16 20:00:33.52847+05:30
b2e66b7b-fbe1-496b-a766-46e2c3bdd5e5	df413048-964e-45da-af55-91e90d7c54ee	e294110d-3809-4e48-82ab-c9c371de27ae	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	\N	1.000000	0.00	\N	f	\N	2026-08-16 22:50:51.89431+05:30	2026-08-16 22:50:51.89431+05:30
dd243393-3767-462f-aa76-37e09a54d7d3	df413048-964e-45da-af55-91e90d7c54ee	d347d10c-300f-4a1b-8b84-a3cfbc4beb28	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	\N	1.000000	0.00	\N	f	\N	2026-09-28 15:58:15.70591+05:30	2026-09-28 15:58:15.70591+05:30
cd9f548b-cc23-41f4-8377-9b6b7338902a	df413048-964e-45da-af55-91e90d7c54ee	4674a9d2-6615-40a7-af7c-f7b902ac0734	\N	9468e99f-757a-4a99-920e-758d967c9b2a	\N	1.000000	0.00	\N	f	\N	2026-09-28 20:10:29.344844+05:30	2026-09-28 20:10:29.344844+05:30
be48c866-1eb1-485c-a9d3-22d9af636e90	df413048-964e-45da-af55-91e90d7c54ee	07ef4ef1-40d0-4934-a9ab-6a5e12805229	b2876e59-29fe-4c9b-86a6-be45d3a6c479	\N	\N	1.000000	0.00	\N	f	\N	2026-09-28 20:16:56.286686+05:30	2026-09-28 20:16:56.286686+05:30
b47861db-1099-4845-8f9a-ac44c527f91f	df413048-964e-45da-af55-91e90d7c54ee	07ef4ef1-40d0-4934-a9ab-6a5e12805229	\N	9468e99f-757a-4a99-920e-758d967c9b2a	\N	1.000000	0.00	\N	f	\N	2026-09-28 20:16:56.286686+05:30	2026-09-28 20:16:56.286686+05:30
692023e5-0cac-4338-a75e-034c50ebf3a1	df413048-964e-45da-af55-91e90d7c54ee	6fac889d-cc30-4562-9d7a-8485879ecb50	b2876e59-29fe-4c9b-86a6-be45d3a6c479	\N	\N	1.000000	0.00	\N	f	\N	2026-09-28 21:13:14.712771+05:30	2026-09-28 21:13:14.712771+05:30
72a1440e-a64d-468f-b83d-a44ef8fc1d75	df413048-964e-45da-af55-91e90d7c54ee	999899db-aaa8-4e02-aefd-475295a9c64b	55c87cf5-af2f-4204-a575-2a1e8523e075	\N	\N	1.000000	0.00	\N	f	\N	2026-09-29 14:44:43.833524+05:30	2026-09-29 14:44:43.833524+05:30
54d4f861-add9-46b5-a62c-78410b2b298e	df413048-964e-45da-af55-91e90d7c54ee	999899db-aaa8-4e02-aefd-475295a9c64b	626920a3-a4e1-41ca-af9f-fb9e2631a46f	\N	\N	1.000000	0.00	\N	f	\N	2026-09-29 14:44:43.833524+05:30	2026-09-29 14:44:43.833524+05:30
ea2b99e3-755f-46de-9b61-3d38a6354ff8	df413048-964e-45da-af55-91e90d7c54ee	999899db-aaa8-4e02-aefd-475295a9c64b	72723bde-d01b-4182-9517-bd64f80d3c5f	\N	\N	1.000000	0.00	\N	f	\N	2026-09-29 14:44:43.833524+05:30	2026-09-29 14:44:43.833524+05:30
\.


--
-- Data for Name: bom_operations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bom_operations (id, tenant_id, bom_id, operation_id, sequence, is_deleted, created_at, updated_at) FROM stdin;
7cd03220-d455-4ab7-9c53-b354efc0cb7d	1e26d822-336a-4caf-b726-d5bc873bcd47	da32a5b5-375f-4b8f-b40f-a680cb109103	ada5d5a6-a6b0-41a0-ae86-d51c5de5df53	10	f	2026-07-25 17:17:23.71135+05:30	2026-07-25 17:17:23.711358+05:30
51f212e1-2fc2-46fa-a81a-d96fb19da859	df413048-964e-45da-af55-91e90d7c54ee	1b22fd6c-0b9f-4ed8-8f4c-675996dd6b78	25d80b77-9769-453c-9c7f-65abca112e78	10	f	2026-08-16 20:01:00.837771+05:30	2026-08-16 20:01:00.83778+05:30
9930a3e6-eeb9-4aa5-9706-2f534f0f0568	df413048-964e-45da-af55-91e90d7c54ee	e294110d-3809-4e48-82ab-c9c371de27ae	25d80b77-9769-453c-9c7f-65abca112e78	10	f	2026-08-16 22:51:10.244051+05:30	2026-08-16 22:51:10.244074+05:30
\.


--
-- Data for Name: boms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.boms (id, tenant_id, template_id, variant_id, version, is_active, valid_from, valid_to, created_by, approved_by, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
da32a5b5-375f-4b8f-b40f-a680cb109103	1e26d822-336a-4caf-b726-d5bc873bcd47	e226b35d-07ba-4210-aa57-5d8b480c367c	\N	v1.0	t	2026-07-25 15:24:04.271+05:30	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	\N	f	\N	2026-07-25 15:24:04.310437+05:30	2026-07-25 15:24:37.083037+05:30
e78edab3-32ad-4733-b1bd-f196064e030f	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	fb929cf7-6354-433e-b66f-d66fad60a0d5	v2.0	f	2026-07-29 22:33:28.953+05:30	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	\N	f	\N	2026-07-29 22:33:29.342523+05:30	2026-07-29 22:33:29.342535+05:30
1b22fd6c-0b9f-4ed8-8f4c-675996dd6b78	df413048-964e-45da-af55-91e90d7c54ee	0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53	\N	v1.0	t	2026-08-16 16:25:37.873+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	f	\N	2026-08-16 16:25:38.216997+05:30	2026-08-16 20:00:33.553308+05:30
e294110d-3809-4e48-82ab-c9c371de27ae	df413048-964e-45da-af55-91e90d7c54ee	be57c4d4-2106-4a78-856b-a385cadd90a4	\N	v1.0	t	2026-08-16 14:25:54.511+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	f	\N	2026-08-16 14:25:54.74493+05:30	2026-08-16 22:50:51.933718+05:30
4674a9d2-6615-40a7-af7c-f7b902ac0734	df413048-964e-45da-af55-91e90d7c54ee	\N	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	v2.0	f	2026-09-28 20:09:45.526+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	f	\N	2026-09-28 20:09:45.666299+05:30	2026-09-28 20:10:29.358803+05:30
07ef4ef1-40d0-4934-a9ab-6a5e12805229	df413048-964e-45da-af55-91e90d7c54ee	8f8e2199-ffd0-412d-9f67-7636bca74a82	\N	v1.0	f	2026-09-28 20:12:00.027+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	f	\N	2026-09-28 20:12:00.1913+05:30	2026-09-28 20:16:56.325061+05:30
d347d10c-300f-4a1b-8b84-a3cfbc4beb28	df413048-964e-45da-af55-91e90d7c54ee	9468e99f-757a-4a99-920e-758d967c9b2a	\N	v1.0	f	2026-09-28 15:58:00.634+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	f	\N	2026-09-28 15:58:01.08822+05:30	2026-09-29 14:45:01.850751+05:30
6fac889d-cc30-4562-9d7a-8485879ecb50	df413048-964e-45da-af55-91e90d7c54ee	9468e99f-757a-4a99-920e-758d967c9b2a	\N	v2.0	f	2026-09-28 17:15:12.869+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	f	\N	2026-09-28 17:15:13.027627+05:30	2026-09-29 14:45:01.850751+05:30
999899db-aaa8-4e02-aefd-475295a9c64b	df413048-964e-45da-af55-91e90d7c54ee	9468e99f-757a-4a99-920e-758d967c9b2a	\N	v3.0	t	2026-09-28 17:55:08.615+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	f	\N	2026-09-28 17:55:08.758088+05:30	2026-09-29 14:44:43.850553+05:30
\.


--
-- Data for Name: chart_of_accounts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.chart_of_accounts (id, tenant_id, code, name, account_type, category, normal_balance, is_system, is_active, created_at, updated_at) FROM stdin;
949a5f7b-0353-404f-bd63-dc49ef36171a	1e26d822-336a-4caf-b726-d5bc873bcd47	1000	Bank	ASSET	CURRENT_ASSET	DEBIT	t	t	2026-07-25 23:09:03.146861+05:30	2026-07-25 23:09:03.146864+05:30
7f59c97d-4952-44be-a11b-bec47b3116eb	1e26d822-336a-4caf-b726-d5bc873bcd47	1100	Accounts Receivable	ASSET	CURRENT_ASSET	DEBIT	t	t	2026-07-25 23:09:03.146868+05:30	2026-07-25 23:09:03.146868+05:30
f32acca9-b0ec-4e02-b7cd-f379bb84eb38	1e26d822-336a-4caf-b726-d5bc873bcd47	2000	Accounts Payable	LIABILITY	CURRENT_LIABILITY	CREDIT	t	t	2026-07-25 23:09:03.146871+05:30	2026-07-25 23:09:03.146871+05:30
bff96e41-e93b-4e3e-bc5c-6bdbb69522f2	1e26d822-336a-4caf-b726-d5bc873bcd47	3000	Retained Earnings	EQUITY	EQUITY	CREDIT	t	t	2026-07-25 23:09:03.146874+05:30	2026-07-25 23:09:03.146874+05:30
db61979f-30b7-4547-b2ee-4f8fe3272733	1e26d822-336a-4caf-b726-d5bc873bcd47	4000	Sales Revenue	INCOME	OPERATING_REVENUE	CREDIT	t	t	2026-07-25 23:09:03.146876+05:30	2026-07-25 23:09:03.146876+05:30
1e5f11e0-83fe-4144-b4a2-08d5942575d1	1e26d822-336a-4caf-b726-d5bc873bcd47	5000	Procurement Expense	EXPENSE	COST_OF_GOODS_SOLD	DEBIT	t	t	2026-07-25 23:09:03.146878+05:30	2026-07-25 23:09:03.146878+05:30
21d2f626-566b-478d-a7a4-86fcd023d4f7	df413048-964e-45da-af55-91e90d7c54ee	1000	Bank	ASSET	CURRENT_ASSET	DEBIT	t	t	2026-08-16 20:54:00.526023+05:30	2026-08-16 20:54:00.526029+05:30
ab21f7d0-2b01-4200-a4be-7ccc2eebdb92	df413048-964e-45da-af55-91e90d7c54ee	1100	Accounts Receivable	ASSET	CURRENT_ASSET	DEBIT	t	t	2026-08-16 20:54:00.526035+05:30	2026-08-16 20:54:00.526036+05:30
13bc1b19-eba0-44f5-ac41-8ef710b25c00	df413048-964e-45da-af55-91e90d7c54ee	2000	Accounts Payable	LIABILITY	CURRENT_LIABILITY	CREDIT	t	t	2026-08-16 20:54:00.526038+05:30	2026-08-16 20:54:00.526039+05:30
afff1b97-2db3-4544-be6d-33ff086a4a7a	df413048-964e-45da-af55-91e90d7c54ee	3000	Retained Earnings	EQUITY	EQUITY	CREDIT	t	t	2026-08-16 20:54:00.526043+05:30	2026-08-16 20:54:00.526043+05:30
6d5dbc4b-22ea-4902-ba84-1c77c840e0bd	df413048-964e-45da-af55-91e90d7c54ee	4000	Sales Revenue	INCOME	OPERATING_REVENUE	CREDIT	t	t	2026-08-16 20:54:00.526045+05:30	2026-08-16 20:54:00.526046+05:30
ea94bf8b-5af9-4af4-8fe1-309ec8ae200f	df413048-964e-45da-af55-91e90d7c54ee	5000	Procurement Expense	EXPENSE	COST_OF_GOODS_SOLD	DEBIT	t	t	2026-08-16 20:54:00.526048+05:30	2026-08-16 20:54:00.526049+05:30
\.


--
-- Data for Name: client_addresses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.client_addresses (id, tenant_id, client_id, type, label, contact_name, address_line1, address_line2, city, state, postal_code, country, phone, email, is_default, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: client_notification_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.client_notification_settings (id, tenant_id, client_id, user_id, order_confirmed, order_shipped, order_delivered, invoice_overdue, low_credit, marketing, created_at, updated_at) FROM stdin;
89e34941-1e1d-4f94-a26c-e3cef1447e18	1e26d822-336a-4caf-b726-d5bc873bcd47	8566fc0d-5da9-4655-9342-1c1cf9b4f261	50a4b4fa-eb2a-4e40-a864-34989d88b429	t	t	t	t	t	f	2026-07-25 17:20:05.071998+05:30	2026-07-25 17:20:05.072007+05:30
\.


--
-- Data for Name: dashboard_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dashboard_metrics (id, tenant_id, metric_key, metric_value, period_start, period_end, metadata, cached_at, expires_at, is_deleted, deleted_at) FROM stdin;
\.


--
-- Data for Name: delivery_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.delivery_lines (id, tenant_id, delivery_order_id, sales_order_line_id, variant_id, quantity, created_at) FROM stdin;
fa17f042-5576-47b7-86ce-a322844dd5df	1e26d822-336a-4caf-b726-d5bc873bcd47	6b9f2002-244c-4fee-982e-001921626a7f	c7c8d198-17b8-4fac-9a7b-40ea353726e2	fb929cf7-6354-433e-b66f-d66fad60a0d5	1.0000	2026-07-25 21:56:45.357625+05:30
bc45a13f-0258-4e99-8d1b-11935f6da54e	1e26d822-336a-4caf-b726-d5bc873bcd47	de92a9ec-0770-46af-a928-e5fea19d03a0	cdab60e1-50bb-4870-93fd-80da6daf549b	fb929cf7-6354-433e-b66f-d66fad60a0d5	5.0000	2026-07-25 23:59:19.414939+05:30
41df713e-e76f-4b93-8b42-96285f78a249	df413048-964e-45da-af55-91e90d7c54ee	fceb4de7-aba8-4b62-aea5-3ebf670aed86	33c5204f-d592-4f17-9f19-e8987fe60caf	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	1.0000	2026-08-16 20:50:04.163709+05:30
24233239-48fc-46c2-a8e7-c4703c8b8ab7	df413048-964e-45da-af55-91e90d7c54ee	edbc0253-d95f-4bf2-a242-7f19cb7c1c3b	6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	1.0000	2026-08-16 22:11:34.201359+05:30
\.


--
-- Data for Name: delivery_orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.delivery_orders (id, tenant_id, delivery_number, sales_order_id, status, carrier, tracking_number, shipped_at, delivered_at, notes, created_by, is_deleted, deleted_at, created_at, updated_at, cancelled_at, cancelled_by, cancellation_reason, packed_at) FROM stdin;
6b9f2002-244c-4fee-982e-001921626a7f	1e26d822-336a-4caf-b726-d5bc873bcd47	DO-000001	b0e1d83e-fd9b-4b77-b53c-04568725f32b	DELIVERED	fedex	724	2026-07-25 22:12:48.946091+05:30	2026-07-25 23:09:03.111572+05:30	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 21:56:45.344058+05:30	2026-07-25 23:09:03.111578+05:30	\N	\N	\N	\N
de92a9ec-0770-46af-a928-e5fea19d03a0	1e26d822-336a-4caf-b726-d5bc873bcd47	DO-000002	d13e28dd-d1db-4710-a628-1cf7cfb3d596	DELIVERED	ups	1234656	2026-07-26 00:03:37.05165+05:30	2026-07-26 00:03:40.807147+05:30	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:59:19.402306+05:30	2026-07-26 00:03:40.807178+05:30	\N	\N	\N	\N
fceb4de7-aba8-4b62-aea5-3ebf670aed86	df413048-964e-45da-af55-91e90d7c54ee	DO-000001	cdea16ef-befb-4d97-a598-25fa710f6ce8	DELIVERED	fedex	123546876	2026-08-16 20:53:42.662165+05:30	2026-08-16 20:54:00.448231+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:50:04.159298+05:30	2026-08-16 20:54:00.448244+05:30	\N	\N	\N	\N
edbc0253-d95f-4bf2-a242-7f19cb7c1c3b	df413048-964e-45da-af55-91e90d7c54ee	DO-000002	bbe75209-17d6-4626-ad3e-df0bbdce24f9	DELIVERED	ups	1234567	2026-08-16 22:11:36.264665+05:30	2026-08-16 22:11:38.036388+05:30	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 22:11:34.194841+05:30	2026-08-16 22:11:38.036417+05:30	\N	\N	\N	\N
\.


--
-- Data for Name: document_associations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.document_associations (id, tenant_id, revision_id, work_order_id, variant_id, template_id, is_print_package_included, created_at, work_order_line_id, show_on_wo) FROM stdin;
92b30a8d-6bfc-475e-a969-5d1a970fcac0	df413048-964e-45da-af55-91e90d7c54ee	4b270c0f-ac82-4b35-8a46-edfbb5e6fbb1	66863c47-2254-44a6-b93e-6f9c7633c58b	\N	\N	t	2026-09-23 21:52:19.834557+05:30	\N	t
52c98d3e-52c7-4f91-90f3-49249e138c8f	df413048-964e-45da-af55-91e90d7c54ee	d1b0ee92-a2e4-478b-b1cd-46612ffab607	66863c47-2254-44a6-b93e-6f9c7633c58b	\N	\N	t	2026-09-25 20:37:46.496645+05:30	\N	t
\.


--
-- Data for Name: document_revisions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.document_revisions (id, tenant_id, document_id, file_attachment_id, revision_code, status, notes, created_at, created_by_id) FROM stdin;
4b270c0f-ac82-4b35-8a46-edfbb5e6fbb1	df413048-964e-45da-af55-91e90d7c54ee	3f79bde3-7063-469e-97ff-ee3bc820a7df	616b91aa-c82c-44c1-96bb-a7de6bec4790	A	APPROVED		2026-09-23 21:52:19.683967+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec
d1b0ee92-a2e4-478b-b1cd-46612ffab607	df413048-964e-45da-af55-91e90d7c54ee	ace3aa15-2518-40a3-b96d-9318bc587288	ba3a17be-2943-46bc-b699-50a510ce1f8c	A	APPROVED		2026-09-25 20:37:46.346996+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec
a7d210aa-d6fd-40f6-af60-b59c79c3d7ad	df413048-964e-45da-af55-91e90d7c54ee	c4ac909a-718a-4e3b-a33b-636c2c1e4679	df26d0f4-6f85-4bee-abb5-73c5934d9894	A	APPROVED		2026-09-26 16:50:57.620912+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documents (id, tenant_id, document_type, entity_id, version_number, file_path, generated_by, generated_at, is_deleted, deleted_at) FROM stdin;
\.


--
-- Data for Name: error_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.error_logs (id, trace_id, correlation_id, tenant_id, user_id, ip_address, path, method, status_code, error_code, error_type, error_message, file_name, line_number, stack_trace, request_body, request_body_truncated, query_params, headers, "timestamp") FROM stdin;
5e5c1d46-0ce8-4ceb-b3dc-bed5a9d566e6	d6edefda-5413-40fa-a42f-ddc8f3070597	b2cc7d0c-3b31-4970-8313-e9f0a961aa43	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:23:24.925954+05:30
109620e3-96de-4676-a97e-e3e7dee3d0b0	e5197a47-0bc4-4027-91f3-5f7eb05d1b21	7262ba86-7de4-4e32-bd5b-656e7be101a3	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:23:26.283474+05:30
f35a46c4-2468-4839-bb8e-dda4f8e05c25	7f9e3015-dce3-4abf-a296-8295c26cc528	fb5c018f-28c0-4222-9b09-6c9b3a99699a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:24:15.137406+05:30
4316c055-f110-4ee1-8e02-98735c3cff86	60251dde-c78b-4108-a552-0a6e5f701612	ab4eee8b-bd00-47b8-9583-9ed7396cd827	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:24:16.330842+05:30
80bd4cd6-4254-4b60-978c-d9128383406f	160ccb7f-c932-4db3-b4af-6ef9fafbcdb6	5f8d2944-599c-48d2-aaa7-359c4f7bd43f	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:27:06.331895+05:30
0fa8b5c1-71a6-4767-9426-9c681eecbe95	9d7d5688-969f-4707-849f-b61d8868565f	a4f5f748-85ba-4d13-9e51-2c49188c6530	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:27:07.902233+05:30
6679bf20-35c0-40dd-9ff1-8fb4969f8c69	eec7c496-8ca4-4f64-86d6-80f251b96e35	d5fce440-1b92-4585-b66a-a81093f249ea	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:28:26.005584+05:30
35be144f-45d7-4bdb-9863-e35942d99778	5a3070f2-b28c-4f1c-a972-fda5030d23fe	3588b700-e49b-43ec-8d8e-3360c039d03e	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:28:27.142008+05:30
ee60e24c-0517-4314-bcde-b3842a607986	4d861773-f22f-4e71-8294-7e922de6f353	6451e49a-22ba-46b2-970c-fe3f742f5a84	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:33:46.153078+05:30
2f798b81-3d92-4f30-9d0e-3104a2aa52e1	c30e01b8-2215-4b00-b6b4-6f2a02624041	6b1d8663-3f19-425b-a209-06c20b58c920	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	127.0.0.1	/api/v1/delivery/dispatch-queue	GET	500	INTERNAL_ERROR	ProgrammingError	(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column sales_orders.priority does not exist\n[SQL: SELECT sales_orders.id, sales_orders.tenant_id, sales_orders.order_number, sales_orders.client_id, sales_orders.order_date, sales_orders.delivery_date, sales_orders.status, sales_orders.payment_status, sales_orders.priority, sales_orders.subtotal, sales_orders.discount_amount, sales_orders.tax_amount, sales_orders.grand_total, sales_orders.estimated_completion_date, sales_orders.expected_d	asyncpg.py	850	FROM sales_orders \nWHERE sales_orders.tenant_id = $1::UUID AND sales_orders.status = $2::VARCHAR AND sales_orders.is_deleted IS false ORDER BY sales_orders.delivery_date ASC]\n[parameters: (UUID('df413048-964e-45da-af55-91e90d7c54ee'), 'READY_FOR_DISPATCH')]\n(Background on this error at: https://sqlalche.me/e/21/f405)	\N	f	null	{"host": "127.0.0.1:8001", "accept": "application/json, text/plain, */*", "pragma": "no-cache", "referer": "http://localhost:5000/dashboard", "sec-ch-ua": "\\"Chromium\\";v=\\"154\\", \\"Google Chrome\\";v=\\"154\\", \\"Not A(Brand\\";v=\\"99\\"", "connection": "close", "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "x-tenant-id": "df413048-964e-45da-af55-91e90d7c54ee", "cache-control": "no-cache", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "en-US,en;q=0.9,ar;q=0.8,hi;q=0.7", "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": "\\"iOS\\""}	2026-10-03 18:33:47.502514+05:30
\.


--
-- Data for Name: failed_tasks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.failed_tasks (id, tenant_id, task_name, arguments_json, error_message, retry_count, failed_at, created_at) FROM stdin;
\.


--
-- Data for Name: file_attachments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.file_attachments (id, tenant_id, file_name, file_size_bytes, content_type, cloudinary_public_id, created_at, uploaded_by_id) FROM stdin;
616b91aa-c82c-44c1-96bb-a7de6bec4790	df413048-964e-45da-af55-91e90d7c54ee	Tanveer_Sayyed_Executive_CV_Final_Reviewed.pdf	355222	application/pdf	medtrack/df413048-964e-45da-af55-91e90d7c54ee/technical_documents/4b270c0f-ac82-4b35-8a46-edfbb5e6fbb1_v1_20260923_162215.pdf	2026-09-23 21:52:19.668775+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec
ba3a17be-2943-46bc-b699-50a510ce1f8c	df413048-964e-45da-af55-91e90d7c54ee	WO-WO-20260913-0004.pdf	1123708	application/pdf	medtrack/df413048-964e-45da-af55-91e90d7c54ee/technical_documents/d1b0ee92-a2e4-478b-b1cd-46612ffab607_v1_20260925_150739.pdf	2026-09-25 20:37:46.326696+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec
df26d0f4-6f85-4bee-abb5-73c5934d9894	df413048-964e-45da-af55-91e90d7c54ee	WhatsApp Image 2026-09-24 at 9.42.04 PM _1_.jpeg	154617	image/jpeg	medtrack/df413048-964e-45da-af55-91e90d7c54ee/technical_documents/a7d210aa-d6fd-40f6-af60-b59c79c3d7ad_v1_20260926_112054.jpeg	2026-09-26 16:50:57.604103+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec
\.


--
-- Data for Name: financial_transactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.financial_transactions (id, tenant_id, reference_type, reference_id, account_type, debit, credit, description, meta, created_by, created_at) FROM stdin;
02b0b79e-e73c-4d41-b55a-e3881070cd53	1e26d822-336a-4caf-b726-d5bc873bcd47	invoice	1cc3df73-6266-4e93-b6e3-60755454f576	RECEIVABLE	500.00	0.00	Accounts receivable for INV-000001	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "7aa78ca2-351f-4276-8a5f-ae413bca59f6"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:09:03.191225+05:30
2a9ecd4d-f276-4202-8f9e-b224e526b410	1e26d822-336a-4caf-b726-d5bc873bcd47	invoice	1cc3df73-6266-4e93-b6e3-60755454f576	REVENUE	0.00	500.00	Revenue for INV-000001	{"account_code": "4000", "account_name": "Sales Revenue", "journal_entry_id": "7aa78ca2-351f-4276-8a5f-ae413bca59f6"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:09:03.200504+05:30
09b63af2-3af2-492b-ad3a-b791910732cc	1e26d822-336a-4caf-b726-d5bc873bcd47	payment	b142a464-d55d-48e0-b9b6-d321e0763b55	CASH	500.00	0.00	Cash received for INV-000001	{"account_code": "1000", "account_name": "Bank", "journal_entry_id": "482c17b5-602b-4b74-8eac-a56f1d4a415b"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:20:04.2313+05:30
1d47abcc-6d9a-429c-bf9c-7977540b9012	1e26d822-336a-4caf-b726-d5bc873bcd47	payment	b142a464-d55d-48e0-b9b6-d321e0763b55	RECEIVABLE	0.00	500.00	Receivable cleared for INV-000001	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "482c17b5-602b-4b74-8eac-a56f1d4a415b"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:20:04.250179+05:30
e812f796-ecd5-45b6-a7c0-b6fcd2536dfe	1e26d822-336a-4caf-b726-d5bc873bcd47	invoice	03871f18-778b-4c1b-8ba4-0d2cf6fef04a	RECEIVABLE	2500.00	0.00	Accounts receivable for INV-000002	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "bb9b4e07-ce43-4ea3-a697-93cbd514f0e6"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:03:40.965352+05:30
1cf34d47-bfcf-4552-a9aa-1a42bd330f67	1e26d822-336a-4caf-b726-d5bc873bcd47	invoice	03871f18-778b-4c1b-8ba4-0d2cf6fef04a	REVENUE	0.00	2500.00	Revenue for INV-000002	{"account_code": "4000", "account_name": "Sales Revenue", "journal_entry_id": "bb9b4e07-ce43-4ea3-a697-93cbd514f0e6"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:03:40.980833+05:30
d25a3b60-233c-40f6-b428-b8986586b788	1e26d822-336a-4caf-b726-d5bc873bcd47	payment	8bcd307e-34d2-47bb-a1cb-0e67fdb5ae35	CASH	2500.00	0.00	Cash received for INV-000002	{"account_code": "1000", "account_name": "Bank", "journal_entry_id": "557aedfb-af87-4f9b-9ee3-f3b47d5b469e"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:04:38.766988+05:30
506b6d1b-d938-4e22-8230-d8286f02cd2d	1e26d822-336a-4caf-b726-d5bc873bcd47	payment	8bcd307e-34d2-47bb-a1cb-0e67fdb5ae35	RECEIVABLE	0.00	2500.00	Receivable cleared for INV-000002	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "557aedfb-af87-4f9b-9ee3-f3b47d5b469e"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:04:38.779045+05:30
95818e61-5ac9-4d91-be07-d60eaf59c638	df413048-964e-45da-af55-91e90d7c54ee	invoice	d94d0a9c-8975-4615-857f-0bd2137e61b3	RECEIVABLE	10000.00	0.00	Accounts receivable for INV-000001	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "e340c139-8fd8-4180-b5a6-a37a53b8b6f3"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:54:00.707182+05:30
5c1b1cff-a147-440d-b78e-da554b58e38d	df413048-964e-45da-af55-91e90d7c54ee	invoice	d94d0a9c-8975-4615-857f-0bd2137e61b3	REVENUE	0.00	10000.00	Revenue for INV-000001	{"account_code": "4000", "account_name": "Sales Revenue", "journal_entry_id": "e340c139-8fd8-4180-b5a6-a37a53b8b6f3"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:54:00.740107+05:30
6a358497-a9d0-4f0c-b771-7952903f1061	df413048-964e-45da-af55-91e90d7c54ee	payment	82284836-2e58-403f-ac23-a6866e64db79	CASH	10000.00	0.00	Cash received for INV-000001	{"account_code": "1000", "account_name": "Bank", "journal_entry_id": "a0d33eb5-177c-4c64-a832-6067bb9459dd"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:56:45.918959+05:30
d6f0e21e-ac5d-44a9-bd97-03e776d8a501	df413048-964e-45da-af55-91e90d7c54ee	payment	82284836-2e58-403f-ac23-a6866e64db79	RECEIVABLE	0.00	10000.00	Receivable cleared for INV-000001	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "a0d33eb5-177c-4c64-a832-6067bb9459dd"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:56:45.927757+05:30
e898373a-00e4-404b-8a1e-ddf7787a455d	df413048-964e-45da-af55-91e90d7c54ee	invoice	72e65e59-bd98-46c0-9c63-d103ea1e0989	RECEIVABLE	10000.00	0.00	Accounts receivable for INV-000002	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "67a1c129-39e2-4ce2-a523-8c2ab493210d"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:11:38.218418+05:30
34e28062-6ce0-4b72-b035-2d09124226ee	df413048-964e-45da-af55-91e90d7c54ee	invoice	72e65e59-bd98-46c0-9c63-d103ea1e0989	REVENUE	0.00	10000.00	Revenue for INV-000002	{"account_code": "4000", "account_name": "Sales Revenue", "journal_entry_id": "67a1c129-39e2-4ce2-a523-8c2ab493210d"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:11:38.233218+05:30
3ce5ba53-4517-43e7-8e74-af621a5b8194	df413048-964e-45da-af55-91e90d7c54ee	payment	ae4af7ba-8919-4189-b98d-5ff7bbca7243	CASH	10000.00	0.00	Cash received for INV-000002	{"account_code": "1000", "account_name": "Bank", "journal_entry_id": "c2a1607f-3e59-4b44-ae5c-a721d3f37668"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:22:12.672422+05:30
2b143838-9a0d-4ccf-879f-ae50f80bca1b	df413048-964e-45da-af55-91e90d7c54ee	payment	ae4af7ba-8919-4189-b98d-5ff7bbca7243	RECEIVABLE	0.00	10000.00	Receivable cleared for INV-000002	{"account_code": "1100", "account_name": "Accounts Receivable", "journal_entry_id": "c2a1607f-3e59-4b44-ae5c-a721d3f37668"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:22:12.689175+05:30
\.


--
-- Data for Name: goods_receipt_notes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.goods_receipt_notes (id, tenant_id, grn_number, purchase_order_id, supplier_id, scheduled_delivery_date, actual_receipt_date, warehouse_location_id, status, driver_name, vehicle_number, transport_company, tracking_number, remarks, created_by, updated_by, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
88ee3423-a4fe-4a78-b6a3-8658b0cde888	1e26d822-336a-4caf-b726-d5bc873bcd47	GRN-PO-20260726-0002	68d8baa0-90bc-4078-92f1-ec5d95ce6847	1fbed590-c8a6-4215-86ee-7b6cb61629b3	\N	2026-07-26 00:31:01.535852+05:30	732e6349-8c10-4a9b-ac52-19d1c83ea805	received	\N	\N	\N	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-26 00:31:01.535857+05:30	2026-07-26 00:31:01.642715+05:30
352e62e0-06e1-479f-b724-31a91a3c3646	df413048-964e-45da-af55-91e90d7c54ee	GRN-PO-20260929-0003	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	96ad7e79-2424-4d35-8960-c471b942ff16	\N	2026-09-29 17:58:29.095316+05:30	a7054e96-1ae5-4800-b414-d556c437b796	received	\N	\N	\N	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 17:58:29.095327+05:30	2026-09-29 17:58:29.219322+05:30
11e00646-e68d-49b1-bfa3-eb7e1fbcc626	df413048-964e-45da-af55-91e90d7c54ee	GRN-PO-20260929-0005	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	96ad7e79-2424-4d35-8960-c471b942ff16	\N	2026-09-29 18:27:49.680242+05:30	a7054e96-1ae5-4800-b414-d556c437b796	received	\N	\N	\N	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:27:49.680256+05:30	2026-09-29 18:27:49.748628+05:30
3b015ba7-c7e4-4dec-8a77-1cd30ace412f	df413048-964e-45da-af55-91e90d7c54ee	GRN-PO-20260929-0006	13ee59cc-e503-43d4-83dc-44eaa53b5172	96ad7e79-2424-4d35-8960-c471b942ff16	\N	2026-09-29 18:33:04.564798+05:30	a7054e96-1ae5-4800-b414-d556c437b796	received	\N	\N	\N	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:33:04.564811+05:30	2026-09-29 18:33:04.673481+05:30
ddd620f1-8b92-4e99-bd13-939b3ff97df5	df413048-964e-45da-af55-91e90d7c54ee	GRN-PO-20260929-0008	360f4ed6-0526-445c-abeb-250977dfe563	96ad7e79-2424-4d35-8960-c471b942ff16	\N	2026-09-29 18:35:14.453789+05:30	a7054e96-1ae5-4800-b414-d556c437b796	received	\N	\N	\N	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:35:14.453803+05:30	2026-09-29 18:35:14.513025+05:30
\.


--
-- Data for Name: grn_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.grn_lines (id, tenant_id, grn_id, po_line_id, material_id, po_quantity, received_quantity, accepted_quantity, rejected_quantity, unit_price, inventory_transaction_id, remarks, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
98f8fc3b-fc16-4d06-af8c-b35e35c5cdf4	1e26d822-336a-4caf-b726-d5bc873bcd47	88ee3423-a4fe-4a78-b6a3-8658b0cde888	830391b9-e210-4b48-94e1-83a06c757ee8	e2c1deee-51be-4698-8c4c-20aa0d7b027d	100.000	100.000	100.000	0.000	60.0000	\N	\N	f	\N	2026-07-26 00:31:01.684529+05:30	2026-07-26 00:31:01.684541+05:30
5e3e9268-f688-44f8-9971-7c6f1a35c8eb	df413048-964e-45da-af55-91e90d7c54ee	352e62e0-06e1-479f-b724-31a91a3c3646	4700df5e-da34-4e97-b27f-e94112ec2183	72723bde-d01b-4182-9517-bd64f80d3c5f	10.000	10.000	10.000	0.000	10.0000	\N	\N	f	\N	2026-09-29 17:58:29.290702+05:30	2026-09-29 17:58:29.290742+05:30
d5a75441-7bb6-41fa-89ac-ddb407bd549b	df413048-964e-45da-af55-91e90d7c54ee	11e00646-e68d-49b1-bfa3-eb7e1fbcc626	5c156afe-f018-44a5-9322-e3cb6c7f0020	55c87cf5-af2f-4204-a575-2a1e8523e075	10.000	10.000	10.000	0.000	4.0000	\N	\N	f	\N	2026-09-29 18:27:49.7772+05:30	2026-09-29 18:27:49.777209+05:30
eaa41510-7a4b-47c1-8aaa-200dd09a5078	df413048-964e-45da-af55-91e90d7c54ee	3b015ba7-c7e4-4dec-8a77-1cd30ace412f	752cc22c-0088-484a-8e2c-2f79be19437c	55c87cf5-af2f-4204-a575-2a1e8523e075	10.000	10.000	10.000	0.000	100.0000	\N	\N	f	\N	2026-09-29 18:33:04.732137+05:30	2026-09-29 18:33:04.732147+05:30
64bc774b-ef52-445d-9ee8-81569c70984f	df413048-964e-45da-af55-91e90d7c54ee	ddd620f1-8b92-4e99-bd13-939b3ff97df5	305a2d19-ea88-4831-a4e9-ad2c614abd6a	626920a3-a4e1-41ca-af9f-fb9e2631a46f	10.000	10.000	10.000	0.000	10.0000	\N	\N	f	\N	2026-09-29 18:35:14.541487+05:30	2026-09-29 18:35:14.541498+05:30
\.


--
-- Data for Name: import_session_rows; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.import_session_rows (id, session_id, row_number, is_valid, data_json, errors_json) FROM stdin;
131cb5d6-3595-4076-bd20-c6b402bc33e9	c7347687-3ec9-43a4-9aac-7c0cb915a14b	2	f	{"Code*": null, "Email": "test@gamil.com", "Name*": "test", "Phone": 1231231231, "Address": "test", "GST Number": null, "Credit Limit": null, "Payment Terms (Days)": null}	[{"error": "Code is mandatory", "value": "", "column": "Code*"}]
1d49c5ec-c3a8-4612-869e-da1e127ab896	e975c551-08bc-4881-9175-ae9dea39a4ea	2	t	{"Code*": null, "Email": "test@gamil.com", "Name*": "test", "Phone": 1231231231, "Address": "test", "GST Number": null, "Credit Limit": null, "Payment Terms (Days)": null}	[]
4c30b6e0-dccc-4a72-9c89-64e70875fa7c	5531a3e4-f36e-4e78-beda-ec6e45757c36	2	t	{"Code*": null, "Email": "test1@gmail.com", "Name*": "test1", "Phone": 9878987868, "Address": "kurla", "GST Number": null, "Payment Terms": null, "Contact Person": "test1", "Performance Rating": null}	[]
\.


--
-- Data for Name: import_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.import_sessions (id, tenant_id, user_id, module, status, duplicate_strategy, total_rows, valid_rows, error_rows, duration_ms, created_at, expires_at) FROM stdin;
c7347687-3ec9-43a4-9aac-7c0cb915a14b	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CLIENTS	PREVIEW	SKIP	1	0	1	\N	2026-08-11 19:31:56.713369+05:30	2026-08-12 19:31:56.713374+05:30
e975c551-08bc-4881-9175-ae9dea39a4ea	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	CLIENTS	COMPLETED	SKIP	1	1	0	41	2026-08-11 20:07:56.344422+05:30	2026-08-12 20:07:56.344426+05:30
5531a3e4-f36e-4e78-beda-ec6e45757c36	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	SUPPLIERS	COMPLETED	SKIP	1	1	0	121	2026-08-16 13:54:49.934077+05:30	2026-08-17 13:54:49.934086+05:30
\.


--
-- Data for Name: inspection_details; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inspection_details (id, tenant_id, inspection_id, parameter, measured_value, tolerance_min, tolerance_max, is_passed) FROM stdin;
\.


--
-- Data for Name: inspection_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inspection_templates (id, tenant_id, name, parameters, is_active, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: inventory_reservations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory_reservations (id, tenant_id, reference_type, reference_id, material_id, batch_id, quantity, status, unit_id, issued_quantity, consumed_quantity, returned_quantity, created_at, updated_at) FROM stdin;
2ee75c46-5f4c-4a50-8e3e-a55cfb15423c	1e26d822-336a-4caf-b726-d5bc873bcd47	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	e2c1deee-51be-4698-8c4c-20aa0d7b027d	\N	2.000	CONSUMED	533498de-dc4d-4842-840c-43ddc8206c9a	2.000	2.000	0.000	2026-07-25 19:06:08.874318+05:30	2026-07-25 20:08:09.918258+05:30
bb2d1e07-cd5b-4aed-9652-69e800e1a85e	1e26d822-336a-4caf-b726-d5bc873bcd47	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	e2c1deee-51be-4698-8c4c-20aa0d7b027d	\N	10.000	CONSUMED	533498de-dc4d-4842-840c-43ddc8206c9a	10.000	10.000	0.000	2026-07-25 23:45:20.768426+05:30	2026-07-25 23:56:27.363704+05:30
5165e015-e257-4b1b-b128-158af0561287	1e26d822-336a-4caf-b726-d5bc873bcd47	sales_order_line	cdab60e1-50bb-4870-93fd-80da6daf549b	0104ddea-8623-463e-aa8c-000a8ce0b8f9	\N	5.000	RESERVED	533498de-dc4d-4842-840c-43ddc8206c9a	0.000	0.000	0.000	2026-07-25 23:57:17.314652+05:30	2026-07-25 23:57:17.31468+05:30
e5a6a62f-2ea0-41d0-a1cb-eb0d95967e76	df413048-964e-45da-af55-91e90d7c54ee	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	1.000	CONSUMED	18f11e18-dd91-45f5-8ac1-2340161e2a4e	1.000	1.000	0.000	2026-08-16 20:02:24.888361+05:30	2026-08-16 20:04:44.996345+05:30
facdc0ee-ee0a-4d0e-94be-cbc09b69b9cd	df413048-964e-45da-af55-91e90d7c54ee	sales_order_line	33c5204f-d592-4f17-9f19-e8987fe60caf	1c172b0b-ce97-415b-89aa-96c489f24560	\N	1.000	RESERVED	18f11e18-dd91-45f5-8ac1-2340161e2a4e	0.000	0.000	0.000	2026-08-16 20:49:04.839235+05:30	2026-08-16 20:49:04.839247+05:30
f27b9154-2aa4-48a4-b91f-877bd3ce5d0e	df413048-964e-45da-af55-91e90d7c54ee	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	1.000	CONSUMED	18f11e18-dd91-45f5-8ac1-2340161e2a4e	1.000	1.000	0.000	2026-08-16 21:01:48.594152+05:30	2026-08-16 22:10:35.585865+05:30
ec11e29d-bf7b-4b5d-bd74-253fcabf9cc1	df413048-964e-45da-af55-91e90d7c54ee	sales_order_line	6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	1c172b0b-ce97-415b-89aa-96c489f24560	\N	1.000	RESERVED	18f11e18-dd91-45f5-8ac1-2340161e2a4e	0.000	0.000	0.000	2026-08-16 22:11:03.671656+05:30	2026-08-16 22:11:03.671664+05:30
\.


--
-- Data for Name: inventory_transactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory_transactions (id, tenant_id, material_id, transaction_type, quantity, unit_id, from_location_id, to_location_id, reference_type, reference_id, remarks, created_by, is_deleted, deleted_at, created_at, updated_at, batch_id) FROM stdin;
8f076e9e-57c0-4b25-93c9-696072087583	1e26d822-336a-4caf-b726-d5bc873bcd47	10702529-530f-45a9-ac87-0692f34f9472	in	100.000	\N	\N	\N	opening_balance	\N	Opening balance	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 14:47:00.884454+05:30	2026-07-25 14:47:00.884462+05:30	\N
277dde04-284f-4fa5-974e-253f4cd486fe	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	in	100.000	\N	\N	e9312a72-f06e-4e5e-b9d7-2973da769656	manual	\N	adding manually	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 19:05:20.465987+05:30	2026-07-25 19:05:20.465992+05:30	\N
b6eab399-5869-4e63-8175-51419d39eb47	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	FG_RECEIPT	1.000	\N	\N	732e6349-8c10-4a9b-ac52-19d1c83ea805	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	FG receipt for WO 5faa5b8c-025c-4637-84e7-0c6a07d57c7f	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 21:52:14.533423+05:30	2026-07-25 21:52:14.533425+05:30	\N
eaeff5d4-8903-4191-9d5c-14c4c82bfaf6	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	FG_RECEIPT	5.000	\N	\N	732e6349-8c10-4a9b-ac52-19d1c83ea805	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	FG receipt for WO 88b79ec2-96c1-4242-a023-9889ea0d430b	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:57:17.319536+05:30	2026-07-25 23:57:17.319548+05:30	\N
929c6837-468a-4894-b703-bf516fc57e52	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	PURCHASE_RECEIPT	100.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	732e6349-8c10-4a9b-ac52-19d1c83ea805	purchase_receipt	68d8baa0-90bc-4078-92f1-ec5d95ce6847	Goods receipt	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-26 00:31:01.656172+05:30	2026-07-26 00:31:01.65618+05:30	\N
dd0415f6-672f-44a3-b3f7-8568a85b349d	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	RESERVATION	2.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	Reserved for WO 5faa5b8c-025c-4637-84e7-0c6a07d57c7f	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 19:06:08.880311+05:30	2026-07-25 19:06:08.880316+05:30	\N
e3e763c0-0d03-4018-9938-64b3952eb4ab	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	RESERVATION	1.000	\N	\N	\N	sales_order_line	c7c8d198-17b8-4fac-9a7b-40ea353726e2	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 22:10:03.871+05:30	2026-07-25 22:10:03.871+05:30	\N
d302b8c3-9c47-46be-bfac-99a27468ed8b	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	RESERVATION	10.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	Reserved for WO 88b79ec2-96c1-4242-a023-9889ea0d430b	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:45:20.773751+05:30	2026-07-25 23:45:20.773758+05:30	\N
6dd89a3c-572b-4be3-9d59-e1e8f8f0d6f1	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	RESERVATION	5.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	sales_order_line	cdab60e1-50bb-4870-93fd-80da6daf549b	Reserved for sales order line cdab60e1-50bb-4870-93fd-80da6daf549b	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:57:17.319554+05:30	2026-07-25 23:57:17.319556+05:30	\N
08566195-54ea-4593-a089-af2782c5e771	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	MATERIAL_ISSUE	2.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	Issued for WO 5faa5b8c-025c-4637-84e7-0c6a07d57c7f	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 19:42:26.919644+05:30	2026-07-25 19:42:26.919648+05:30	\N
6f348b86-abab-485d-b4fc-8dd5be39cfad	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	MATERIAL_ISSUE	1.000	\N	\N	\N	sales_order_line	c7c8d198-17b8-4fac-9a7b-40ea353726e2	Shipped for sales order line c7c8d198-17b8-4fac-9a7b-40ea353726e2	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 22:12:48.963979+05:30	2026-07-25 22:12:48.963986+05:30	\N
e6a829a5-4071-4cc1-bb8a-5226c93738a0	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	MATERIAL_ISSUE	10.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	Issued for WO 88b79ec2-96c1-4242-a023-9889ea0d430b	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:46:19.321912+05:30	2026-07-25 23:46:19.32192+05:30	\N
600b2921-5e06-4af8-849b-3c6da3be8218	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	MATERIAL_ISSUE	5.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	sales_order_line	cdab60e1-50bb-4870-93fd-80da6daf549b	Shipped for sales order line cdab60e1-50bb-4870-93fd-80da6daf549b	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-26 00:03:37.062766+05:30	2026-07-26 00:03:37.062773+05:30	\N
7cf01816-464d-43b0-886c-ccf3638e6ae0	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	PROD_CONSUMPTION	2.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	Production consumption for WO 5faa5b8c-025c-4637-84e7-0c6a07d57c7f	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 20:08:09.936115+05:30	2026-07-25 20:08:09.93612+05:30	\N
44e026af-d184-4cd3-8423-869c2c102d6e	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	PROD_CONSUMPTION	10.000	533498de-dc4d-4842-840c-43ddc8206c9a	\N	\N	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	Production consumption for WO 88b79ec2-96c1-4242-a023-9889ea0d430b	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:56:27.392718+05:30	2026-07-25 23:56:27.392727+05:30	\N
88ecdb7a-a9da-4c09-b635-a2d1862cc273	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	in	10.000	\N	\N	\N	opening_balance	\N	Opening balance	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 19:58:57.406896+05:30	2026-08-16 19:58:57.406901+05:30	\N
dc38c5ee-b06e-4749-8638-0baac53bdab5	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	RESERVATION	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	Reserved for WO 6b2cc088-c47c-471d-9247-d33974e47a84	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:02:24.898923+05:30	2026-08-16 20:02:24.898931+05:30	\N
980d1b14-317a-4bc8-8a2e-2dd9582a755d	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	MATERIAL_ISSUE	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	Issued for WO 6b2cc088-c47c-471d-9247-d33974e47a84	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:04:09.866713+05:30	2026-08-16 20:04:09.866718+05:30	\N
cfd49299-33b1-4828-b1d7-f4e9bf67ae96	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	CONSUME	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	Production consumption for WO 6b2cc088-c47c-471d-9247-d33974e47a84	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:04:45.00788+05:30	2026-08-16 20:04:45.007889+05:30	\N
d6b85699-8e4c-41bf-a6ac-6fc2ea9d1bc2	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	FG_RECEIPT	1.000	\N	\N	a7054e96-1ae5-4800-b414-d556c437b796	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	FG receipt for WO 6b2cc088-c47c-471d-9247-d33974e47a84	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:49:04.845716+05:30	2026-08-16 20:49:04.84572+05:30	\N
b97e6905-a710-455e-b7f9-65d59b5660e9	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	RESERVATION	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	sales_order_line	33c5204f-d592-4f17-9f19-e8987fe60caf	Reserved for sales order line 33c5204f-d592-4f17-9f19-e8987fe60caf	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:49:04.845722+05:30	2026-08-16 20:49:04.845723+05:30	\N
501889fa-2e6c-4a68-a247-d5fe1f7305fd	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	DISPATCH	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	sales_order_line	33c5204f-d592-4f17-9f19-e8987fe60caf	Shipped for sales order line 33c5204f-d592-4f17-9f19-e8987fe60caf	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:53:42.679403+05:30	2026-08-16 20:53:42.679415+05:30	\N
00663caf-bc53-468a-9108-c80c1da89b1a	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	RESERVATION	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	Reserved for WO 66863c47-2254-44a6-b93e-6f9c7633c58b	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 21:01:48.597495+05:30	2026-08-16 21:01:48.597503+05:30	\N
af09bf2a-709e-4bf0-8227-4b251a5420c1	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	MATERIAL_ISSUE	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	Issued for WO 66863c47-2254-44a6-b93e-6f9c7633c58b	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 21:11:13.338399+05:30	2026-08-16 21:11:13.338406+05:30	\N
42c934fc-98d2-44b4-9fff-0fddbc50d34f	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	CONSUME	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	Production consumption for WO 66863c47-2254-44a6-b93e-6f9c7633c58b	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 22:10:35.613028+05:30	2026-08-16 22:10:35.613037+05:30	\N
6e8e0186-0ac0-4269-b1ea-72ff9a684b2e	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	FG_RECEIPT	1.000	\N	\N	a7054e96-1ae5-4800-b414-d556c437b796	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	FG receipt for WO 66863c47-2254-44a6-b93e-6f9c7633c58b	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 22:11:03.675206+05:30	2026-08-16 22:11:03.675214+05:30	\N
f9c67efa-406a-48ed-9a8f-b96ec3fc32ae	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	RESERVATION	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	sales_order_line	6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	Reserved for sales order line 6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 22:11:03.675218+05:30	2026-08-16 22:11:03.675219+05:30	\N
54bdac9c-a21c-49ec-9feb-7b2b41029a5c	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	DISPATCH	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	\N	sales_order_line	6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	Shipped for sales order line 6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 22:11:36.272868+05:30	2026-08-16 22:11:36.272876+05:30	\N
1dab911b-e137-447f-8860-223cddf98fe0	df413048-964e-45da-af55-91e90d7c54ee	72723bde-d01b-4182-9517-bd64f80d3c5f	PURCHASE_RECEIPT	10.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	a7054e96-1ae5-4800-b414-d556c437b796	purchase_receipt	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	Goods receipt	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 17:58:29.239919+05:30	2026-09-29 17:58:29.239931+05:30	\N
c9bd226f-2130-489e-ba64-2c61bec38f6f	df413048-964e-45da-af55-91e90d7c54ee	72723bde-d01b-4182-9517-bd64f80d3c5f	transfer	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	a7054e96-1ae5-4800-b414-d556c437b796	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	subcontract_order	4412fe8e-b123-4b2f-a766-b2d15db2c89e	Issue to subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:25:32.410191+05:30	2026-09-29 18:25:32.410201+05:30	\N
e1db93d9-be9e-4cd2-b88f-030e1728c528	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	PURCHASE_RECEIPT	10.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	a7054e96-1ae5-4800-b414-d556c437b796	purchase_receipt	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	Goods receipt	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:27:49.759744+05:30	2026-09-29 18:27:49.759752+05:30	\N
40ebfdcf-6659-47b3-8d71-eb426786d29d	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	PURCHASE_RECEIPT	10.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	a7054e96-1ae5-4800-b414-d556c437b796	purchase_receipt	13ee59cc-e503-43d4-83dc-44eaa53b5172	Goods receipt	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:33:04.689635+05:30	2026-09-29 18:33:04.689646+05:30	\N
06c20db4-b358-45ae-980e-1ae7d24a303b	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	transfer	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	a7054e96-1ae5-4800-b414-d556c437b796	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	subcontract_order	4412fe8e-b123-4b2f-a766-b2d15db2c89e	Issue to subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:34:25.258819+05:30	2026-09-29 18:34:25.258828+05:30	\N
864f60f1-3ee9-4300-9d69-f02439afb62d	df413048-964e-45da-af55-91e90d7c54ee	626920a3-a4e1-41ca-af9f-fb9e2631a46f	PURCHASE_RECEIPT	10.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	a7054e96-1ae5-4800-b414-d556c437b796	purchase_receipt	360f4ed6-0526-445c-abeb-250977dfe563	Goods receipt	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:35:14.523224+05:30	2026-09-29 18:35:14.523235+05:30	\N
8975da1b-0259-45ca-bd6b-648c1ca40485	df413048-964e-45da-af55-91e90d7c54ee	626920a3-a4e1-41ca-af9f-fb9e2631a46f	transfer	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	a7054e96-1ae5-4800-b414-d556c437b796	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	subcontract_order	4412fe8e-b123-4b2f-a766-b2d15db2c89e	Issue to subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:35:30.203359+05:30	2026-09-29 18:35:30.203367+05:30	\N
98aba579-30bf-4575-a7c5-07cb923b1232	df413048-964e-45da-af55-91e90d7c54ee	b2876e59-29fe-4c9b-86a6-be45d3a6c479	transfer	1.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	a7054e96-1ae5-4800-b414-d556c437b796	subcontract_order	4412fe8e-b123-4b2f-a766-b2d15db2c89e	Receive finished goods from subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 19:30:36.669665+05:30	2026-09-29 19:30:36.669682+05:30	70f2f536-55ca-4d7b-a039-fa6945235031
5987abc0-6ac9-442f-ad5c-54e6de810253	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	transfer	2.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	a7054e96-1ae5-4800-b414-d556c437b796	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	subcontract_order	4798a3c4-8865-47af-9fc4-539f4742c39d	Issue to subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 13:51:05.359873+05:30	2026-10-01 13:51:05.359886+05:30	\N
3b60cd52-c6ef-449c-850a-d22e149878fc	df413048-964e-45da-af55-91e90d7c54ee	626920a3-a4e1-41ca-af9f-fb9e2631a46f	transfer	2.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	a7054e96-1ae5-4800-b414-d556c437b796	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	subcontract_order	4798a3c4-8865-47af-9fc4-539f4742c39d	Issue to subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 13:51:21.205881+05:30	2026-10-01 13:51:21.205891+05:30	\N
3a4b9ba8-5176-4acb-84ec-bd1a86dc41f7	df413048-964e-45da-af55-91e90d7c54ee	72723bde-d01b-4182-9517-bd64f80d3c5f	transfer	2.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	a7054e96-1ae5-4800-b414-d556c437b796	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	subcontract_order	4798a3c4-8865-47af-9fc4-539f4742c39d	Issue to subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 13:51:36.115093+05:30	2026-10-01 13:51:36.115102+05:30	\N
f3478969-f4eb-4a3b-94be-8b57e884fe55	df413048-964e-45da-af55-91e90d7c54ee	b2876e59-29fe-4c9b-86a6-be45d3a6c479	transfer	2.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	\N	a7054e96-1ae5-4800-b414-d556c437b796	subcontract_order	4798a3c4-8865-47af-9fc4-539f4742c39d	Receive finished goods from subcontractor	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 13:54:15.363289+05:30	2026-10-01 13:54:15.363298+05:30	0ff6d195-7859-49fb-904f-836b878de529
9c9a4496-d7b6-47be-9394-c9554bf00b6c	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	out	2.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	\N	subcontract_order	4798a3c4-8865-47af-9fc4-539f4742c39d	Consumed in subcontract processing (receipt: 2.0 units)	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 13:54:15.470216+05:30	2026-10-01 13:54:15.470228+05:30	\N
608135cf-9b18-4a42-8166-605dbe3c51ae	df413048-964e-45da-af55-91e90d7c54ee	626920a3-a4e1-41ca-af9f-fb9e2631a46f	out	2.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	\N	subcontract_order	4798a3c4-8865-47af-9fc4-539f4742c39d	Consumed in subcontract processing (receipt: 2.0 units)	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 13:54:15.497288+05:30	2026-10-01 13:54:15.497299+05:30	\N
b9a1dad9-5888-4c8c-ab58-4981eace11d2	df413048-964e-45da-af55-91e90d7c54ee	72723bde-d01b-4182-9517-bd64f80d3c5f	out	2.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	\N	subcontract_order	4798a3c4-8865-47af-9fc4-539f4742c39d	Consumed in subcontract processing (receipt: 2.0 units)	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 13:54:15.51126+05:30	2026-10-01 13:54:15.511271+05:30	\N
8725d7ef-5d24-4399-b6e8-b2109a290162	df413048-964e-45da-af55-91e90d7c54ee	b260fa5a-943e-44f6-b754-ce6442671016	in	10.000	\N	\N	\N	onboarding_opening_balance	\N	Opening balance via onboarding import	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 20:50:07.051693+05:30	2026-10-01 20:50:07.051698+05:30	\N
857a1783-9779-4fc4-af42-40945e4af743	df413048-964e-45da-af55-91e90d7c54ee	c6c6937f-121d-4ed9-82c1-53c7e460f3da	in	100.000	\N	\N	\N	onboarding_opening_balance	\N	Opening balance via onboarding import	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-10-01 20:52:03.965915+05:30	2026-10-01 20:52:03.965922+05:30	\N
\.


--
-- Data for Name: invoice_disputes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.invoice_disputes (id, tenant_id, supplier_invoice_id, disputed_amount, reason, status, resolution_notes, raised_by_supplier, resolved_by, resolved_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invoice_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.invoice_lines (id, tenant_id, invoice_id, product_id, product_type, description, quantity, unit_price, discount_amount, tax_rate, tax_amount, total, created_at) FROM stdin;
27023aac-c10a-4e39-8b1c-3436bc6c0a7b	1e26d822-336a-4caf-b726-d5bc873bcd47	1cc3df73-6266-4e93-b6e3-60755454f576	fb929cf7-6354-433e-b66f-d66fad60a0d5	variant	Product fb929cf7-6354-433e-b66f-d66fad60a0d5	1	500.00	0.00	0.00	0.00	500.00	2026-07-25 23:09:03.171504+05:30
f0769b42-ed4d-4c72-b0e7-9325aafa4f6c	1e26d822-336a-4caf-b726-d5bc873bcd47	03871f18-778b-4c1b-8ba4-0d2cf6fef04a	fb929cf7-6354-433e-b66f-d66fad60a0d5	variant	Product fb929cf7-6354-433e-b66f-d66fad60a0d5	5	500.00	0.00	0.00	0.00	2500.00	2026-07-26 00:03:40.92386+05:30
a2803abb-29c1-456b-ba2a-8672f85091ce	df413048-964e-45da-af55-91e90d7c54ee	d94d0a9c-8975-4615-857f-0bd2137e61b3	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	variant	Product d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	1	10000.00	0.00	0.00	0.00	10000.00	2026-08-16 20:54:00.645858+05:30
7e42c345-2d19-4446-a517-6e14fc85a119	df413048-964e-45da-af55-91e90d7c54ee	72e65e59-bd98-46c0-9c63-d103ea1e0989	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	variant	Product d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	1	10000.00	0.00	0.00	0.00	10000.00	2026-08-16 22:11:38.169158+05:30
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.invoices (id, tenant_id, invoice_number, sales_order_id, client_id, client_name, client_address, client_gst_number, status, invoice_date, due_date, subtotal, discount_amount, tax_amount, grand_total, paid_amount, notes, terms, created_by, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
1cc3df73-6266-4e93-b6e3-60755454f576	1e26d822-336a-4caf-b726-d5bc873bcd47	INV-000001	b0e1d83e-fd9b-4b77-b53c-04568725f32b	8566fc0d-5da9-4655-9342-1c1cf9b4f261	tanveer	tes		PAID	2026-07-25	2026-07-26	500.00	0.00	0.00	500.00	500.00	Auto-generated invoice on delivery	Net 1	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:09:03.164038+05:30	2026-07-25 23:20:04.081224+05:30
03871f18-778b-4c1b-8ba4-0d2cf6fef04a	1e26d822-336a-4caf-b726-d5bc873bcd47	INV-000002	d13e28dd-d1db-4710-a628-1cf7cfb3d596	8566fc0d-5da9-4655-9342-1c1cf9b4f261	tanveer	tes		PAID	2026-07-26	2026-07-27	2500.00	0.00	0.00	2500.00	2500.00	Auto-generated invoice on delivery	Net 1	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-26 00:03:40.897611+05:30	2026-07-26 00:04:38.665362+05:30
d94d0a9c-8975-4615-857f-0bd2137e61b3	df413048-964e-45da-af55-91e90d7c54ee	INV-000001	cdea16ef-befb-4d97-a598-25fa710f6ce8	63bd0ed6-7e32-4c12-a6d6-ea8eb901006b	test	test	\N	PAID	2026-08-16	2026-09-15	10000.00	0.00	0.00	10000.00	10000.00	Auto-generated invoice on delivery	Net 30	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:54:00.593408+05:30	2026-08-16 20:56:45.786594+05:30
72e65e59-bd98-46c0-9c63-d103ea1e0989	df413048-964e-45da-af55-91e90d7c54ee	INV-000002	bbe75209-17d6-4626-ad3e-df0bbdce24f9	63bd0ed6-7e32-4c12-a6d6-ea8eb901006b	test	test	\N	PAID	2026-08-16	2026-09-15	10000.00	0.00	0.00	10000.00	10000.00	Auto-generated invoice on delivery	Net 30	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 22:11:38.14893+05:30	2026-08-16 22:22:12.520469+05:30
\.


--
-- Data for Name: item_code_sequences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.item_code_sequences (id, tenant_id, item_type, category_id, next_number, created_at, updated_at) FROM stdin;
615d7d74-cc33-4afd-9a2e-24f0b37ff08a	1e26d822-336a-4caf-b726-d5bc873bcd47	RM	93feb87c-72d3-4f55-9076-e3806702fa59	3	2026-07-25 14:47:00.822964+05:30	2026-07-25 15:12:37.844851+05:30
33f1ae19-45c3-4a3c-90cd-9646959cc808	1e26d822-336a-4caf-b726-d5bc873bcd47	FG	93feb87c-72d3-4f55-9076-e3806702fa59	4	2026-07-25 14:50:59.730878+05:30	2026-07-25 15:15:16.882306+05:30
5c33f8f6-292f-46ef-a493-6d132b7a5b7c	7fd84f4a-c061-4774-a95d-415c4e67b6b6	FG	d1f92133-f688-4e00-9393-f6ed12e8699a	2	2026-07-30 17:18:14.760404+05:30	2026-07-30 17:18:14.807504+05:30
b97f8fc0-bfe3-4468-8068-6a00bf9988ca	df413048-964e-45da-af55-91e90d7c54ee	SF	24f51813-20b3-438b-a110-84f825816abd	2	2026-09-28 15:54:12.490467+05:30	2026-09-28 15:54:12.544914+05:30
22f284d6-5029-4e19-856d-f64b96e58c42	df413048-964e-45da-af55-91e90d7c54ee	FG	24f51813-20b3-438b-a110-84f825816abd	12	2026-08-16 14:12:11.092626+05:30	2026-09-28 21:33:15.981305+05:30
d0ea931d-b19f-4ed7-9bc7-c6a8992b63f5	df413048-964e-45da-af55-91e90d7c54ee	RM	24f51813-20b3-438b-a110-84f825816abd	5	2026-08-16 19:58:57.360391+05:30	2026-09-29 14:43:41.232654+05:30
\.


--
-- Data for Name: item_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.item_templates (id, tenant_id, code, name, description, category_id, base_unit_id, attributes, is_active, is_deleted, deleted_at, created_at, updated_at, status, code_locked) FROM stdin;
4ae6ebe2-d988-4c16-a860-3e84dadf6048	1e26d822-336a-4caf-b726-d5bc873bcd47	FG-MT-0001	rotameter		93feb87c-72d3-4f55-9076-e3806702fa59	533498de-dc4d-4842-840c-43ddc8206c9a	[{"key": "2", "label": "250", "values": ["S"]}]	f	f	\N	2026-07-25 14:50:59.746945+05:30	2026-07-25 14:50:59.746953+05:30	DRAFT	t
e226b35d-07ba-4210-aa57-5d8b480c367c	1e26d822-336a-4caf-b726-d5bc873bcd47	FG-MT-0003	Basic Desk		93feb87c-72d3-4f55-9076-e3806702fa59	533498de-dc4d-4842-840c-43ddc8206c9a	[{"key": "finish", "label": "Finish", "values": ["Oak", "Walnut"]}]	t	f	\N	2026-07-25 15:15:16.879251+05:30	2026-07-25 15:21:29.872133+05:30	ACTIVE	t
803f3166-0c7c-44b8-ad2a-b3e5d6ea51c4	7fd84f4a-c061-4774-a95d-415c4e67b6b6	FG-MT-0001	Thermometer	Thermometer made of colored alcohol , glass and steel 	d1f92133-f688-4e00-9393-f6ed12e8699a	d91ce611-6b54-4db6-82d5-9e03e0bc56e3	[{"key": "c", "label": "classic", "values": ["s"]}]	t	f	\N	2026-07-30 17:18:14.792412+05:30	2026-07-30 17:35:21.26843+05:30	ACTIVE	t
0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0002	test45		24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	[{"key": "red", "label": "red", "values": ["xl"]}]	t	f	\N	2026-08-16 16:24:12.260614+05:30	2026-08-16 22:51:32.680664+05:30	ACTIVE	t
be57c4d4-2106-4a78-856b-a385cadd90a4	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0001	test1		24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	[{"key": "s", "label": "small", "values": ["idontknowwhatto"]}]	t	f	\N	2026-08-16 14:12:11.106941+05:30	2026-08-16 22:52:52.950468+05:30	ACTIVE	t
8f8e2199-ffd0-412d-9f67-7636bca74a82	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0004	test3		24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	[]	f	f	\N	2026-08-16 22:54:27.675679+05:30	2026-08-16 22:54:27.675683+05:30	DRAFT	t
145fed75-cb52-4e0d-9407-9e9de3493e13	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0008	test-sub-materail-tempalte	tes	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	[{"key": "blue", "label": "blue", "values": ["test"]}]	f	f	\N	2026-09-28 21:28:19.126541+05:30	2026-09-28 21:28:19.126548+05:30	DRAFT	t
80d74378-f5a5-4a83-933c-35ee9a82bd51	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0010	test2-semi-tempate		24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	[{"key": "yellow", "label": "yellow", "values": ["A", "B", "C"]}]	f	f	\N	2026-09-28 21:32:43.797305+05:30	2026-09-28 21:32:43.797311+05:30	DRAFT	t
9468e99f-757a-4a99-920e-758d967c9b2a	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0006	semi-prodcut		24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	[]	t	f	\N	2026-09-28 15:56:04.739794+05:30	2026-09-29 14:42:05.170737+05:30	ACTIVE	t
\.


--
-- Data for Name: item_variants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.item_variants (id, tenant_id, template_id, code, name, variant_key, attribute_values, base_unit_id, standard_cost, selling_price, is_active, is_deleted, deleted_at, created_at, updated_at, material_id, code_locked) FROM stdin;
fb929cf7-6354-433e-b66f-d66fad60a0d5	1e26d822-336a-4caf-b726-d5bc873bcd47	e226b35d-07ba-4210-aa57-5d8b480c367c	FG-MT-0003-OAK	Basic Desk - Oak	FINISH=OAK	{"FINISH": "Oak"}	533498de-dc4d-4842-840c-43ddc8206c9a	50.0000	500.0000	t	f	\N	2026-07-25 15:18:58.638042+05:30	2026-07-25 15:18:58.638049+05:30	0104ddea-8623-463e-aa8c-000a8ce0b8f9	t
d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	df413048-964e-45da-af55-91e90d7c54ee	0bdd04c8-e74f-4285-bbf9-b1a0c77e3c53	FG-MT-0002-XL	test45 - xl	RED=XL	{"RED": "xl"}	18f11e18-dd91-45f5-8ac1-2340161e2a4e	500.0000	10000.0000	t	f	\N	2026-08-16 16:25:04.664435+05:30	2026-08-16 16:25:04.717364+05:30	1c172b0b-ce97-415b-89aa-96c489f24560	t
ecc099e8-ce13-4f0c-a3ee-7ee972dfd2f7	df413048-964e-45da-af55-91e90d7c54ee	145fed75-cb52-4e0d-9407-9e9de3493e13	FG-MT-0008-TEST	test-sub-materail-tempalte - test	BLUE=TEST	{"BLUE": "test"}	18f11e18-dd91-45f5-8ac1-2340161e2a4e	90.0000	1000.0000	t	f	\N	2026-09-28 21:29:02.073457+05:30	2026-09-28 21:32:00.538032+05:30	b2876e59-29fe-4c9b-86a6-be45d3a6c479	t
90ef81ec-1e64-430e-8a3f-640c7bff5bdc	df413048-964e-45da-af55-91e90d7c54ee	80d74378-f5a5-4a83-933c-35ee9a82bd51	FG-MT-0010-A	test2-semi-tempate - A	YELLOW=A	{"YELLOW": "A"}	18f11e18-dd91-45f5-8ac1-2340161e2a4e	5.0000	10.0000	t	f	\N	2026-09-28 21:33:15.946906+05:30	2026-09-28 21:33:15.992359+05:30	2618eb22-948a-4ad2-9ef7-de0b652cbc6b	t
92a32baf-41d5-4524-abf3-10ea30e42b3e	df413048-964e-45da-af55-91e90d7c54ee	80d74378-f5a5-4a83-933c-35ee9a82bd51	FG-MT-0010-B	test2-semi-tempate - B	YELLOW=B	{"YELLOW": "B"}	18f11e18-dd91-45f5-8ac1-2340161e2a4e	0.0000	\N	t	f	\N	2026-09-28 21:49:55.553689+05:30	2026-09-28 21:49:55.553697+05:30	b2876e59-29fe-4c9b-86a6-be45d3a6c479	t
6168bef7-18d4-4030-9b52-343c5f56700d	df413048-964e-45da-af55-91e90d7c54ee	9468e99f-757a-4a99-920e-758d967c9b2a	FG-MT-0006-	semi-prodcut - 		{}	18f11e18-dd91-45f5-8ac1-2340161e2a4e	500.0000	\N	t	f	\N	2026-09-28 15:57:36.83611+05:30	2026-09-29 14:42:00.226041+05:30	b2876e59-29fe-4c9b-86a6-be45d3a6c479	t
\.


--
-- Data for Name: job_cards; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_cards (id, work_order_id, operation_id, sequence, assigned_to, status, started_at, completed_at, remarks, pause_reason, operator_notes, paused_at, total_downtime_seconds, produced_quantity, scrap_quantity, rework_quantity, rejected_quantity) FROM stdin;
adf0bd0c-f823-4958-bcc3-0755f17e3e46	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	ada5d5a6-a6b0-41a0-ae86-d51c5de5df53	10	\N	DONE	2026-07-25 19:08:14.462399+05:30	2026-07-25 19:08:31.565719+05:30	completed	\N	\N	\N	0.000	0.000	0.000	0.000	0.000
2f1cd9ce-dc9a-4c11-98b8-f665ed221c25	88b79ec2-96c1-4242-a023-9889ea0d430b	ada5d5a6-a6b0-41a0-ae86-d51c5de5df53	10	\N	DONE	2026-07-25 23:51:16.595894+05:30	2026-07-25 23:51:32.165666+05:30	done	\N	\N	\N	0.000	0.000	0.000	0.000	0.000
f4b9a7c2-a2b0-4da7-a9cd-a3fd75c2df02	6b2cc088-c47c-471d-9247-d33974e47a84	25d80b77-9769-453c-9c7f-65abca112e78	10	\N	IN_PROGRESS	2026-08-16 20:05:07.28965+05:30	\N	\N	\N	\N	\N	0.000	0.000	0.000	0.000	0.000
46bed4af-83f7-4a2d-b4fe-68120031a006	66863c47-2254-44a6-b93e-6f9c7633c58b	25d80b77-9769-453c-9c7f-65abca112e78	10	\N	DONE	2026-08-16 21:11:32.341979+05:30	2026-08-16 21:11:59.004244+05:30	t	\N	\N	\N	0.000	1.000	0.000	0.000	0.000
\.


--
-- Data for Name: journal_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.journal_entries (id, tenant_id, entry_number, entry_date, reference_type, reference_id, memo, status, reverses_entry_id, meta, created_by, created_at) FROM stdin;
7aa78ca2-351f-4276-8a5f-ae413bca59f6	1e26d822-336a-4caf-b726-d5bc873bcd47	JE-000001	2026-07-25	invoice	1cc3df73-6266-4e93-b6e3-60755454f576	Invoice INV-000001 created for SO SO-20260725-001	POSTED	\N	{"invoice_number": "INV-000001"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:09:03.182138+05:30
482c17b5-602b-4b74-8eac-a56f1d4a415b	1e26d822-336a-4caf-b726-d5bc873bcd47	JE-000002	2026-07-25	payment	b142a464-d55d-48e0-b9b6-d321e0763b55	Payment PAY-000001 received for invoice INV-000001	POSTED	\N	{"invoice_number": "INV-000001", "payment_number": "PAY-000001"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:20:04.201584+05:30
bb9b4e07-ce43-4ea3-a697-93cbd514f0e6	1e26d822-336a-4caf-b726-d5bc873bcd47	JE-000003	2026-07-26	invoice	03871f18-778b-4c1b-8ba4-0d2cf6fef04a	Invoice INV-000002 created for SO SO-20260725-002	POSTED	\N	{"invoice_number": "INV-000002"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:03:40.937143+05:30
557aedfb-af87-4f9b-9ee3-f3b47d5b469e	1e26d822-336a-4caf-b726-d5bc873bcd47	JE-000004	2026-07-25	payment	8bcd307e-34d2-47bb-a1cb-0e67fdb5ae35	Payment PAY-000002 received for invoice INV-000002	POSTED	\N	{"invoice_number": "INV-000002", "payment_number": "PAY-000002"}	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:04:38.749771+05:30
e340c139-8fd8-4180-b5a6-a37a53b8b6f3	df413048-964e-45da-af55-91e90d7c54ee	JE-000001	2026-08-16	invoice	d94d0a9c-8975-4615-857f-0bd2137e61b3	Invoice INV-000001 created for SO SO-20260816-001	POSTED	\N	{"invoice_number": "INV-000001"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:54:00.67281+05:30
a0d33eb5-177c-4c64-a832-6067bb9459dd	df413048-964e-45da-af55-91e90d7c54ee	JE-000002	2026-08-16	payment	82284836-2e58-403f-ac23-a6866e64db79	Payment PAY-000001 received for invoice INV-000001	POSTED	\N	{"invoice_number": "INV-000001", "payment_number": "PAY-000001"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:56:45.90092+05:30
67a1c129-39e2-4ce2-a523-8c2ab493210d	df413048-964e-45da-af55-91e90d7c54ee	JE-000003	2026-08-16	invoice	72e65e59-bd98-46c0-9c63-d103ea1e0989	Invoice INV-000002 created for SO SO-20260816-002	POSTED	\N	{"invoice_number": "INV-000002"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:11:38.186801+05:30
c2a1607f-3e59-4b44-ae5c-a721d3f37668	df413048-964e-45da-af55-91e90d7c54ee	JE-000004	2026-08-16	payment	ae4af7ba-8919-4189-b98d-5ff7bbca7243	Payment PAY-000002 received for invoice INV-000002	POSTED	\N	{"invoice_number": "INV-000002", "payment_number": "PAY-000002"}	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:22:12.639631+05:30
\.


--
-- Data for Name: journal_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.journal_lines (id, journal_entry_id, account_id, description, debit, credit, created_at) FROM stdin;
72466e15-9681-4885-92fe-45580b29ec05	7aa78ca2-351f-4276-8a5f-ae413bca59f6	7f59c97d-4952-44be-a11b-bec47b3116eb	Accounts receivable for INV-000001	500.00	0.00	2026-07-25 23:09:03.196465+05:30
c97cfc03-11f8-4049-b1f8-dcedc7ea3f7a	7aa78ca2-351f-4276-8a5f-ae413bca59f6	db61979f-30b7-4547-b2ee-4f8fe3272733	Revenue for INV-000001	0.00	500.00	2026-07-25 23:09:03.201084+05:30
1d1569fe-aa78-4a95-a298-d37ee712d115	482c17b5-602b-4b74-8eac-a56f1d4a415b	949a5f7b-0353-404f-bd63-dc49ef36171a	Cash received for INV-000001	500.00	0.00	2026-07-25 23:20:04.238217+05:30
8af2ef91-a1b9-420d-bfa7-878252308dfb	482c17b5-602b-4b74-8eac-a56f1d4a415b	7f59c97d-4952-44be-a11b-bec47b3116eb	Receivable cleared for INV-000001	0.00	500.00	2026-07-25 23:20:04.252181+05:30
df549832-a7a0-4372-9c16-75493ab1a77e	bb9b4e07-ce43-4ea3-a697-93cbd514f0e6	7f59c97d-4952-44be-a11b-bec47b3116eb	Accounts receivable for INV-000002	2500.00	0.00	2026-07-26 00:03:40.971201+05:30
fcf8e039-f745-4173-9086-0cde25713959	bb9b4e07-ce43-4ea3-a697-93cbd514f0e6	db61979f-30b7-4547-b2ee-4f8fe3272733	Revenue for INV-000002	0.00	2500.00	2026-07-26 00:03:40.982703+05:30
53c85af4-65d7-48c5-8d20-8a05743e86d6	557aedfb-af87-4f9b-9ee3-f3b47d5b469e	949a5f7b-0353-404f-bd63-dc49ef36171a	Cash received for INV-000002	2500.00	0.00	2026-07-26 00:04:38.769436+05:30
1e3f49d9-b27b-43b3-bae9-da6ac783bae6	557aedfb-af87-4f9b-9ee3-f3b47d5b469e	7f59c97d-4952-44be-a11b-bec47b3116eb	Receivable cleared for INV-000002	0.00	2500.00	2026-07-26 00:04:38.781291+05:30
db27bbe2-7bb8-4a76-a874-5bc619120d39	e340c139-8fd8-4180-b5a6-a37a53b8b6f3	ab21f7d0-2b01-4200-a4be-7ccc2eebdb92	Accounts receivable for INV-000001	10000.00	0.00	2026-08-16 20:54:00.726114+05:30
1b3379a1-12a8-49dc-a003-980ac614b997	e340c139-8fd8-4180-b5a6-a37a53b8b6f3	6d5dbc4b-22ea-4902-ba84-1c77c840e0bd	Revenue for INV-000001	0.00	10000.00	2026-08-16 20:54:00.741674+05:30
539d33c0-daa5-426b-823b-49c1ffda278a	a0d33eb5-177c-4c64-a832-6067bb9459dd	21d2f626-566b-478d-a7a4-86fcd023d4f7	Cash received for INV-000001	10000.00	0.00	2026-08-16 20:56:45.921896+05:30
15ea01a2-dd0c-4da7-86c3-a7bf92555772	a0d33eb5-177c-4c64-a832-6067bb9459dd	ab21f7d0-2b01-4200-a4be-7ccc2eebdb92	Receivable cleared for INV-000001	0.00	10000.00	2026-08-16 20:56:45.930584+05:30
02c6cef8-5dc5-48c7-a230-b53e36d34276	67a1c129-39e2-4ce2-a523-8c2ab493210d	ab21f7d0-2b01-4200-a4be-7ccc2eebdb92	Accounts receivable for INV-000002	10000.00	0.00	2026-08-16 22:11:38.224358+05:30
6bb5bafd-0ab1-460e-b83a-26c959ef367e	67a1c129-39e2-4ce2-a523-8c2ab493210d	6d5dbc4b-22ea-4902-ba84-1c77c840e0bd	Revenue for INV-000002	0.00	10000.00	2026-08-16 22:11:38.234869+05:30
4fb9974b-0199-4e44-9dec-f9f52e64e1f3	c2a1607f-3e59-4b44-ae5c-a721d3f37668	21d2f626-566b-478d-a7a4-86fcd023d4f7	Cash received for INV-000002	10000.00	0.00	2026-08-16 22:22:12.678372+05:30
53ca73fb-5f36-4805-81f1-deb9c86ae363	c2a1607f-3e59-4b44-ae5c-a721d3f37668	ab21f7d0-2b01-4200-a4be-7ccc2eebdb92	Receivable cleared for INV-000002	0.00	10000.00	2026-08-16 22:22:12.690691+05:30
\.


--
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.locations (id, tenant_id, name, type, parent_location_id, is_active, created_at, updated_at, is_deleted, deleted_at, code) FROM stdin;
885f0264-c974-45dc-97a1-77575991bde7	52323f77-709b-4cb8-818e-c1ad16262541	raw material	rack	\N	t	2026-07-24 22:27:54.945728+05:30	2026-07-24 22:27:54.945736+05:30	f	\N	\N
09a60aba-ada3-4dba-a84a-9d9973d5150d	52323f77-709b-4cb8-818e-c1ad16262541	finish gd	warehouse	\N	t	2026-07-24 22:28:32.334133+05:30	2026-07-24 22:28:32.334144+05:30	f	\N	rack-finish
e9312a72-f06e-4e5e-b9d7-2973da769656	1e26d822-336a-4caf-b726-d5bc873bcd47	rack	rack	\N	t	2026-07-24 22:51:54.950911+05:30	2026-07-24 22:52:02.890436+05:30	f	\N	rc
732e6349-8c10-4a9b-ac52-19d1c83ea805	1e26d822-336a-4caf-b726-d5bc873bcd47	raw rack	warehouse	\N	t	2026-07-24 22:54:41.104628+05:30	2026-07-24 22:54:41.104635+05:30	f	\N	rk
f6eb0257-c15c-4f33-a425-4639c53cf16e	7fd84f4a-c061-4774-a95d-415c4e67b6b6	Kurla Mumbai	warehouse	\N	t	2026-07-30 16:57:04.842199+05:30	2026-07-30 16:57:04.842209+05:30	f	\N	ST-Kurla
8433d5f7-c2a7-450a-84d3-302ad01ddc03	7fd84f4a-c061-4774-a95d-415c4e67b6b6	Mumbra Thane 	warehouse	\N	t	2026-07-30 16:57:29.232098+05:30	2026-07-30 16:57:29.232105+05:30	f	\N	TH-Mumbra
a7054e96-1ae5-4800-b414-d556c437b796	df413048-964e-45da-af55-91e90d7c54ee	raw	warehouse	\N	t	2026-08-16 14:11:09.158099+05:30	2026-08-16 14:11:09.158107+05:30	f	\N	\N
b28a8a9b-08ab-470f-b6b2-6e43b1aad297	df413048-964e-45da-af55-91e90d7c54ee	Subcontractor: SUP-000001	subcontractor	\N	t	2026-09-29 18:25:32.347843+05:30	2026-09-29 18:25:32.347852+05:30	f	\N	SUB-96ad7e79-2424-4d35-8960-c471b942ff16
\.


--
-- Data for Name: material_categories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_categories (id, tenant_id, name, description, is_active, created_at, updated_at, is_deleted, deleted_at, code_prefix) FROM stdin;
3d7d5f13-d8a5-478e-a666-cfa81d3af614	52323f77-709b-4cb8-818e-c1ad16262541	Metal	\N	t	2026-07-24 22:26:56.793969+05:30	2026-07-24 22:26:56.793978+05:30	f	\N	ML
93feb87c-72d3-4f55-9076-e3806702fa59	1e26d822-336a-4caf-b726-d5bc873bcd47	Metal	\N	t	2026-07-24 22:51:20.554796+05:30	2026-07-24 22:51:20.554802+05:30	f	\N	MT
dbe8ed9e-4a76-46d6-a987-42cc1afc9ddc	1e26d822-336a-4caf-b726-d5bc873bcd47	UNCATEGORIZED	\N	t	2026-07-28 19:55:14.301016+05:30	2026-07-28 19:55:14.301022+05:30	f	\N	UNC
d1f92133-f688-4e00-9393-f6ed12e8699a	7fd84f4a-c061-4774-a95d-415c4e67b6b6	Metal	Any metal steel or copper	t	2026-07-30 16:55:46.004806+05:30	2026-07-30 16:55:46.004815+05:30	f	\N	MT
dfc18108-99e9-4897-9921-6518313528b5	7fd84f4a-c061-4774-a95d-415c4e67b6b6	Glass	Glass 	t	2026-07-30 16:56:23.442571+05:30	2026-07-30 16:56:23.442577+05:30	f	\N	GLS
24f51813-20b3-438b-a110-84f825816abd	df413048-964e-45da-af55-91e90d7c54ee	Metal	\N	t	2026-08-16 14:10:30.799546+05:30	2026-08-16 14:10:30.799553+05:30	f	\N	MT
\.


--
-- Data for Name: material_consumption_records; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_consumption_records (id, tenant_id, work_order_id, material_id, production_record_id, operation_id, batch_id, planned_quantity, actual_quantity, variance_quantity, scrap_quantity, unit_id, recorded_by, recorded_at, remarks) FROM stdin;
8ad71ad0-5d7e-464c-84a4-c5e97e89f09c	1e26d822-336a-4caf-b726-d5bc873bcd47	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	e2c1deee-51be-4698-8c4c-20aa0d7b027d	5e94312e-eacd-4b97-b6d7-29c6dffa69a3	\N	\N	2.000	2.000	0.000	0.000	533498de-dc4d-4842-840c-43ddc8206c9a	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 20:08:09.944605+05:30	\N
4c73186a-2270-4409-957b-b3515bd54d22	1e26d822-336a-4caf-b726-d5bc873bcd47	88b79ec2-96c1-4242-a023-9889ea0d430b	e2c1deee-51be-4698-8c4c-20aa0d7b027d	d5a1dc6e-51f4-470e-baea-619f0ac5fcdb	\N	\N	10.000	10.000	0.000	0.000	533498de-dc4d-4842-840c-43ddc8206c9a	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:56:27.409587+05:30	\N
12135fa0-ad44-4d55-918d-33b1a641f7fe	df413048-964e-45da-af55-91e90d7c54ee	6b2cc088-c47c-471d-9247-d33974e47a84	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	62a054bf-3f74-408b-922f-448f557f4ba6	\N	\N	1.000	1.000	0.000	0.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:04:45.014876+05:30	\N
974a364d-bd03-43d4-9b70-086724956a36	df413048-964e-45da-af55-91e90d7c54ee	66863c47-2254-44a6-b93e-6f9c7633c58b	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	02945f64-7cff-41b5-9500-d4160d624e2e	25d80b77-9769-453c-9c7f-65abca112e78	\N	1.000	1.000	0.000	0.000	18f11e18-dd91-45f5-8ac1-2340161e2a4e	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:10:35.626526+05:30	\N
\.


--
-- Data for Name: material_import_mappings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_import_mappings (id, tenant_id, name, mapping_json, created_at) FROM stdin;
\.


--
-- Data for Name: material_onboarding_profiles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_onboarding_profiles (id, tenant_id, name, defaults_json, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: material_onboarding_rows; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_onboarding_rows (id, session_id, tenant_id, row_number, raw_json, normalized_json, validation_json, protected_changes_json, classification, status, result_material_id, created_at) FROM stdin;
\.


--
-- Data for Name: material_onboarding_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_onboarding_sessions (id, tenant_id, uploaded_by, filename, status, dry_run, protected_changes_confirmed, original_headers_json, mapping_json, summary_json, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: material_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_requests (id, tenant_id, item_id, item_type, required_quantity, fulfilled_quantity, required_by, status, source_ref_type, source_ref_id, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
7d690cc4-eaa8-4f5b-bd2d-d65d3e41838d	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	material	2.000	0.000	2026-07-31	open	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	f	\N	2026-07-25 18:04:19.807281+05:30	2026-07-25 18:04:19.807292+05:30
\.


--
-- Data for Name: material_shortages; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.material_shortages (id, tenant_id, work_order_id, material_id, required_quantity, available_quantity, shortage_quantity, status, created_by, created_at, updated_at) FROM stdin;
5fffa968-b9ed-46fd-9237-2f866786ea1e	1e26d822-336a-4caf-b726-d5bc873bcd47	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	e2c1deee-51be-4698-8c4c-20aa0d7b027d	2.000	0.000	2.000	open	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 18:04:19.815192+05:30	2026-07-25 19:03:18.202805+05:30
\.


--
-- Data for Name: materials; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.materials (id, tenant_id, code, name, description, category_id, base_unit_id, material_type, is_active, is_deleted, deleted_at, created_at, updated_at, current_stock, reserved_stock, reorder_level, location_id, is_batch_tracked, is_serialized, current_cost, inspection_required, inspection_template_id, safety_stock, lead_time_days, created_by, updated_by, code_locked, item_code, length_uom, length_per_unit, weight_per_unit, dimension_spec, preferred_supplier_id, hazardous_flag, qc_required_flag, barcode, traceability_enabled, batch_rule, expiry_tracking, shelf_life_days, quarantine_required, cuttable_inventory, remaining_quantity_tracking, reusable_remainder, decimal_precision, supplier_item_code, purchase_uom, min_stock, max_stock, reorder_quantity, moq) FROM stdin;
10702529-530f-45a9-ac87-0692f34f9472	1e26d822-336a-4caf-b726-d5bc873bcd47	RM-MT-0001	brass body	\N	93feb87c-72d3-4f55-9076-e3806702fa59	533498de-dc4d-4842-840c-43ddc8206c9a	raw	t	f	\N	2026-07-25 14:47:00.84495+05:30	2026-07-25 14:47:00.876044+05:30	100.0000	0.0000	10.0000	732e6349-8c10-4a9b-ac52-19d1c83ea805	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
31be554c-ad23-49a8-8427-d0dea4f676ac	1e26d822-336a-4caf-b726-d5bc873bcd47	RM-GRB-000001	Gear Rotameter Brass Body	\N	dbe8ed9e-4a76-46d6-a987-42cc1afc9ddc	5a4cd2fb-e55f-4784-a87b-2a3b2c804437	raw	t	f	\N	2026-07-28 19:55:14.513293+05:30	2026-07-28 19:55:14.513318+05:30	0.0000	0.0000	10.0000	\N	t	t	0.0000	f	\N	5.0000	7	69ebd965-54bc-4d0d-8231-db1f55e0cde4	69ebd965-54bc-4d0d-8231-db1f55e0cde4	t	\N	\N	\N	\N	\N	\N	f	t	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
79418991-53b3-4d43-b9da-cf42ed893394	1e26d822-336a-4caf-b726-d5bc873bcd47	RM-GRS-000002	Gear Rotameter SS Float	\N	dbe8ed9e-4a76-46d6-a987-42cc1afc9ddc	5a4cd2fb-e55f-4784-a87b-2a3b2c804437	raw	t	f	\N	2026-07-28 19:55:14.513335+05:30	2026-07-28 19:55:14.513338+05:30	0.0000	0.0000	15.0000	\N	t	t	0.0000	f	\N	5.0000	10	69ebd965-54bc-4d0d-8231-db1f55e0cde4	69ebd965-54bc-4d0d-8231-db1f55e0cde4	t	\N	\N	\N	\N	\N	\N	f	t	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
a8b13e4d-51c9-4786-8cc4-a3197b305a27	1e26d822-336a-4caf-b726-d5bc873bcd47	RM-GRG-000003	Gear Rotameter Gear Set	\N	dbe8ed9e-4a76-46d6-a987-42cc1afc9ddc	5a4cd2fb-e55f-4784-a87b-2a3b2c804437	raw	t	f	\N	2026-07-28 19:55:14.513348+05:30	2026-07-28 19:55:14.51335+05:30	0.0000	0.0000	8.0000	\N	f	t	0.0000	f	\N	2.0000	12	69ebd965-54bc-4d0d-8231-db1f55e0cde4	69ebd965-54bc-4d0d-8231-db1f55e0cde4	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
5eba3174-fd9c-45b4-bf1d-9c82a1ee6822	1e26d822-336a-4caf-b726-d5bc873bcd47	RM-GRB-000004	Gear Rotameter Borosilicate Glass Tube	\N	dbe8ed9e-4a76-46d6-a987-42cc1afc9ddc	5a4cd2fb-e55f-4784-a87b-2a3b2c804437	raw	t	f	\N	2026-07-28 19:55:14.513357+05:30	2026-07-28 19:55:14.513359+05:30	0.0000	0.0000	6.0000	\N	t	t	0.0000	f	\N	3.0000	14	69ebd965-54bc-4d0d-8231-db1f55e0cde4	69ebd965-54bc-4d0d-8231-db1f55e0cde4	t	\N	\N	\N	\N	\N	\N	f	t	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
dd1b4662-08e8-4f92-8d58-35f3015f9ea5	1e26d822-336a-4caf-b726-d5bc873bcd47	RM-GRN-000005	Gear Rotameter NBR Gasket		93feb87c-72d3-4f55-9076-e3806702fa59	5a4cd2fb-e55f-4784-a87b-2a3b2c804437	raw	t	f	\N	2026-07-28 19:55:14.513366+05:30	2026-07-28 20:03:41.489195+05:30	0.0000	0.0000	50.0000	732e6349-8c10-4a9b-ac52-19d1c83ea805	t	t	0.0000	f	\N	20.0000	5	69ebd965-54bc-4d0d-8231-db1f55e0cde4	69ebd965-54bc-4d0d-8231-db1f55e0cde4	t	\N	\N	\N	\N	\N	\N	f	t	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
d10f8452-dc72-462f-8d5e-7accc6c38e38	7fd84f4a-c061-4774-a95d-415c4e67b6b6	FG-THE-000001	thermometer	test	d1f92133-f688-4e00-9393-f6ed12e8699a	d91ce611-6b54-4db6-82d5-9e03e0bc56e3	finished	t	f	\N	2026-07-30 17:38:53.39409+05:30	2026-07-30 17:38:53.394096+05:30	0.0000	0.0000	10.0000	8433d5f7-c2a7-450a-84d3-302ad01ddc03	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
b2876e59-29fe-4c9b-86a6-be45d3a6c479	df413048-964e-45da-af55-91e90d7c54ee	SF-MT-0001	main-sub-part	\N	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	semi_finished	t	f	\N	2026-09-28 15:54:12.526787+05:30	2026-10-01 13:54:15.377548+05:30	3.0000	0.0000	10.0000	a7054e96-1ae5-4800-b414-d556c437b796	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	df413048-964e-45da-af55-91e90d7c54ee	RM-MT-0001	test	\N	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	raw	t	f	\N	2026-08-16 19:58:57.377282+05:30	2026-08-16 22:10:35.580087+05:30	8.0000	0.0000	10.0000	a7054e96-1ae5-4800-b414-d556c437b796	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
1c172b0b-ce97-415b-89aa-96c489f24560	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0003	test45 - xl	Auto-provisioned Finished Good for variant: test45 - xl	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	finished	t	f	\N	2026-08-16 16:25:04.696507+05:30	2026-08-16 22:11:36.276676+05:30	0.0000	0.0000	\N	\N	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
2d46674c-c3bb-485f-890c-10bfb98027d5	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0005	test	\N	24f51813-20b3-438b-a110-84f825816abd	\N	finished	t	f	\N	2026-09-27 19:57:24.966883+05:30	2026-09-27 19:57:24.966892+05:30	0.0000	0.0000	10.0000	a7054e96-1ae5-4800-b414-d556c437b796	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
0104ddea-8623-463e-aa8c-000a8ce0b8f9	1e26d822-336a-4caf-b726-d5bc873bcd47	FG-MT-0002	Basic Desk - Oak Finish	Fully assembled basic desk with oak finish	93feb87c-72d3-4f55-9076-e3806702fa59	\N	finished	t	f	\N	2026-07-25 15:13:56.380194+05:30	2026-07-26 00:03:37.065477+05:30	0.0000	0.0000	10.0000	e9312a72-f06e-4e5e-b9d7-2973da769656	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
e2c1deee-51be-4698-8c4c-20aa0d7b027d	1e26d822-336a-4caf-b726-d5bc873bcd47	RM-MT-0002	Oak Wood Board	Standard oak boards used for assembling basic desks	93feb87c-72d3-4f55-9076-e3806702fa59	533498de-dc4d-4842-840c-43ddc8206c9a	raw	t	f	\N	2026-07-25 15:12:37.842004+05:30	2026-07-26 00:31:01.665063+05:30	188.0000	0.0000	10.0000	e9312a72-f06e-4e5e-b9d7-2973da769656	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
f1be51f0-66c9-4961-8aab-50b98f7cd11d	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0007	semi-prodcut -	Auto-provisioned Finished Good for variant: semi-prodcut - 	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	finished	t	f	\N	2026-09-28 15:57:36.871754+05:30	2026-09-28 15:57:36.871761+05:30	0.0000	0.0000	\N	\N	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
84edf1a2-83ce-432b-9d0c-534c20824f1d	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0009	test-sub-materail-tempalte - test	Auto-provisioned Finished Good for variant: test-sub-materail-tempalte - test	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	finished	t	f	\N	2026-09-28 21:29:02.111269+05:30	2026-09-28 21:29:02.111274+05:30	0.0000	0.0000	\N	\N	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
2618eb22-948a-4ad2-9ef7-de0b652cbc6b	df413048-964e-45da-af55-91e90d7c54ee	FG-MT-0011	test2-semi-tempate - A	Auto-provisioned Finished Good for variant: test2-semi-tempate - A	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	finished	t	f	\N	2026-09-28 21:33:15.971265+05:30	2026-09-28 21:33:15.971273+05:30	0.0000	0.0000	\N	\N	f	f	0.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
55c87cf5-af2f-4204-a575-2a1e8523e075	df413048-964e-45da-af55-91e90d7c54ee	RM-MT-0002	raw001	\N	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	raw	t	f	\N	2026-09-29 14:43:11.101681+05:30	2026-10-01 13:54:15.475503+05:30	18.0000	0.0000	10.0000	a7054e96-1ae5-4800-b414-d556c437b796	f	f	100.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
626920a3-a4e1-41ca-af9f-fb9e2631a46f	df413048-964e-45da-af55-91e90d7c54ee	RM-MT-0003	raw002	\N	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	raw	t	f	\N	2026-09-29 14:43:26.070129+05:30	2026-10-01 13:54:15.499356+05:30	8.0000	0.0000	10.0000	a7054e96-1ae5-4800-b414-d556c437b796	f	f	10.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
72723bde-d01b-4182-9517-bd64f80d3c5f	df413048-964e-45da-af55-91e90d7c54ee	RM-MT-0004	raw-003	\N	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	raw	t	f	\N	2026-09-29 14:43:41.228231+05:30	2026-10-01 13:54:15.513992+05:30	8.0000	0.0000	10.0000	a7054e96-1ae5-4800-b414-d556c437b796	f	f	10.0000	f	\N	\N	\N	\N	\N	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
b260fa5a-943e-44f6-b754-ce6442671016	df413048-964e-45da-af55-91e90d7c54ee	RM-TES-000001	tes1	\N	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	raw	t	f	\N	2026-10-01 20:50:07.029012+05:30	2026-10-01 20:50:07.029021+05:30	10.0000	0.0000	20.0000	\N	f	f	0.0000	f	\N	101.0000	7	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
c6c6937f-121d-4ed9-82c1-53c7e460f3da	df413048-964e-45da-af55-91e90d7c54ee	RM-BRA-000002	brass2x	\N	24f51813-20b3-438b-a110-84f825816abd	18f11e18-dd91-45f5-8ac1-2340161e2a4e	raw	t	f	\N	2026-10-01 20:52:03.960348+05:30	2026-10-01 20:52:03.960356+05:30	100.0000	0.0000	20.0000	\N	f	f	0.0000	f	\N	101.0000	7	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	t	\N	\N	\N	\N	\N	\N	f	f	\N	f	\N	f	\N	f	f	f	f	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: mrp_suggestions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.mrp_suggestions (id, tenant_id, material_id, material_code, material_name, gross_requirement, current_stock, open_po_qty, reserved_stock, net_requirement, suggested_qty, lead_time_days, order_by_date, need_by_date, supplier_id, supplier_name, status, po_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: non_conformance_reports; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.non_conformance_reports (id, tenant_id, inspection_id, ncr_type, reason, action_taken, created_at) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notifications (id, tenant_id, user_id, title, message, reference_type, reference_id, is_read, notification_type, created_at, read_at, deep_link, target_role) FROM stdin;
7e8cf048-abcb-44b2-ade8-4884848cd0a1	1e26d822-336a-4caf-b726-d5bc873bcd47	69ebd965-54bc-4d0d-8231-db1f55e0cde4	Order SO-20260725-001 needs approval	tanveer (CUST-000001) requested Basic Desk - Oak x1. Open sales order SO-20260725-001 to review and approve.	sales_order	b0e1d83e-fd9b-4b77-b53c-04568725f32b	t	SALES_ORDER_PENDING_APPROVAL	2026-07-25 17:36:17.331768+05:30	\N	\N	\N
dea9360c-e5c6-43ba-9268-1a04b4bf7af7	1e26d822-336a-4caf-b726-d5bc873bcd47	50a4b4fa-eb2a-4e40-a864-34989d88b429	Order SO-20260725-001 confirmed	Your order has entered execution and is now Production.	sales_order	b0e1d83e-fd9b-4b77-b53c-04568725f32b	f	ORDER_CONFIRMED	2026-07-25 18:04:19.97062+05:30	\N	\N	\N
cf93b1d0-67ef-4066-ac5a-9c7b232704b9	1e26d822-336a-4caf-b726-d5bc873bcd47	69ebd965-54bc-4d0d-8231-db1f55e0cde4	Production action required for SO-20260725-001	Sales order SO-20260725-001 was approved and needs production work order execution.	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	t	WORK_ORDER_ACTION_REQUIRED	2026-07-25 18:04:19.991003+05:30	\N	\N	\N
8ddb5203-f26e-4942-8f77-97af2a6ef585	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	FG Received - WO WO-20260725-0001	Finished goods received for Work Order WO-20260725-0001. Quantity: 1.0.	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	f	fg_received	2026-07-25 21:52:14.550536+05:30	\N	/manufacturing/work-orders/5faa5b8c-025c-4637-84e7-0c6a07d57c7f	dispatch
df8321b3-f4ab-4507-90ff-e3ee3490513f	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Order SO-20260725-001 Ready for Dispatch	All materials allocated for order SO-20260725-001. Ready for dispatch.	sales_order	b0e1d83e-fd9b-4b77-b53c-04568725f32b	f	ready_for_dispatch_action	2026-07-25 21:52:14.560685+05:30	\N	/sales/orders/b0e1d83e-fd9b-4b77-b53c-04568725f32b	dispatch
c5d24e44-8ab3-4a0d-ac66-f4766af9502b	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Dispatch Completed - Order SO-20260725-001	Order SO-20260725-001 has been delivered. Auto-invoicing in progress.	sales_order	b0e1d83e-fd9b-4b77-b53c-04568725f32b	f	dispatch_completed	2026-07-25 23:09:03.128729+05:30	\N	/sales/orders/b0e1d83e-fd9b-4b77-b53c-04568725f32b	finance
bff3ee13-398e-4b11-80ff-60eaae6fbcd6	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Payment Complete for Order SO-20260725-001	Full payment received for order SO-20260725-001. Order is now COMPLETED.	sales_order	b0e1d83e-fd9b-4b77-b53c-04568725f32b	f	payment_received	2026-07-25 23:20:04.168901+05:30	\N	/sales/orders/b0e1d83e-fd9b-4b77-b53c-04568725f32b	sales
9332ee86-e478-497d-8e97-bf0c9bf1b72b	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Work Order WO-20260725-0002 Released	Work Order WO-20260725-0002 has been released. Materials can be prepared.	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	f	wo_released	2026-07-25 23:45:20.796084+05:30	\N	/manufacturing/work-orders/88b79ec2-96c1-4242-a023-9889ea0d430b	storekeeper
c03b7795-c2be-49e3-9162-abb47405ddaa	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Action Required: Issue Materials - WO WO-20260725-0002	Materials reserved for Work Order WO-20260725-0002. Please issue materials to begin production.	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	f	issue_materials_action	2026-07-25 23:45:20.801281+05:30	\N	/manufacturing/work-orders/88b79ec2-96c1-4242-a023-9889ea0d430b	storekeeper
d7e05775-ab2a-481f-9277-8c75b7c5139c	1e26d822-336a-4caf-b726-d5bc873bcd47	50a4b4fa-eb2a-4e40-a864-34989d88b429	Order SO-20260725-002 approved	Your order has been approved and is now Production.	sales_order	d13e28dd-d1db-4710-a628-1cf7cfb3d596	f	ORDER_APPROVED	2026-07-25 23:45:20.854677+05:30	\N	\N	\N
9fcf15d5-1548-4beb-af4c-0dff1ec7ffc0	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Materials Issued - WO WO-20260725-0002	All BOM materials have been issued for Work Order WO-20260725-0002. Production can begin.	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	f	material_issued	2026-07-25 23:46:19.310464+05:30	\N	/manufacturing/work-orders/88b79ec2-96c1-4242-a023-9889ea0d430b	operator
919ed593-fd3a-48c8-b49b-1c77172bc497	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Action Required: Start Production - WO WO-20260725-0002	All materials issued for Work Order WO-20260725-0002. Production can now begin.	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	f	start_production_action	2026-07-25 23:46:19.341136+05:30	\N	/manufacturing/work-orders/88b79ec2-96c1-4242-a023-9889ea0d430b	operator
1cc1edb6-4245-49fb-b063-c05fb162bc61	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	FG Received - WO WO-20260725-0002	Finished goods received for Work Order WO-20260725-0002. Quantity: 5.0.	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	f	fg_received	2026-07-25 23:57:17.385516+05:30	\N	/manufacturing/work-orders/88b79ec2-96c1-4242-a023-9889ea0d430b	dispatch
055bbd35-f83b-4faf-8032-cfc054669a44	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Order SO-20260725-002 Ready for Dispatch	All materials allocated for order SO-20260725-002. Ready for dispatch.	sales_order	d13e28dd-d1db-4710-a628-1cf7cfb3d596	f	ready_for_dispatch_action	2026-07-25 23:57:17.404346+05:30	\N	/sales/orders/d13e28dd-d1db-4710-a628-1cf7cfb3d596	dispatch
02858e33-84d0-4afa-b548-3c34a0dbc4e2	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Dispatch Completed - Order SO-20260725-002	Order SO-20260725-002 has been delivered. Auto-invoicing in progress.	sales_order	d13e28dd-d1db-4710-a628-1cf7cfb3d596	f	dispatch_completed	2026-07-26 00:03:40.837636+05:30	\N	/sales/orders/d13e28dd-d1db-4710-a628-1cf7cfb3d596	finance
4f2def99-9bb5-4dc0-9118-c0398019aacc	1e26d822-336a-4caf-b726-d5bc873bcd47	\N	Payment Complete for Order SO-20260725-002	Full payment received for order SO-20260725-002. Order is now COMPLETED.	sales_order	d13e28dd-d1db-4710-a628-1cf7cfb3d596	f	payment_received	2026-07-26 00:04:38.738238+05:30	\N	/sales/orders/d13e28dd-d1db-4710-a628-1cf7cfb3d596	sales
f0261b13-d392-425e-a3cb-155b7e992184	1e26d822-336a-4caf-b726-d5bc873bcd47	69ebd965-54bc-4d0d-8231-db1f55e0cde4	Production action required for SO-20260725-002	Sales order SO-20260725-002 was approved and needs production work order execution.	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	t	WORK_ORDER_ACTION_REQUIRED	2026-07-25 23:45:20.880094+05:30	\N	\N	\N
85b9772a-b2ff-4fc9-ade0-6dd5cf686b49	1e26d822-336a-4caf-b726-d5bc873bcd47	69ebd965-54bc-4d0d-8231-db1f55e0cde4	Order SO-20260725-002 needs approval	tanveer (CUST-000001) requested Basic Desk - Oak x5. Open sales order SO-20260725-002 to review and approve.	sales_order	d13e28dd-d1db-4710-a628-1cf7cfb3d596	t	SALES_ORDER_PENDING_APPROVAL	2026-07-25 23:45:01.750583+05:30	\N	\N	\N
b2bbbcb2-c9de-42d0-8096-60e73320eadc	df413048-964e-45da-af55-91e90d7c54ee	\N	Work Order WO-20260816-0001 Released	Work Order WO-20260816-0001 has been released. Materials can be prepared.	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	f	wo_released	2026-08-16 20:02:24.916071+05:30	\N	/manufacturing/work-orders/6b2cc088-c47c-471d-9247-d33974e47a84	storekeeper
b64f3c00-ded4-4496-a116-c1151a2f1957	df413048-964e-45da-af55-91e90d7c54ee	\N	Action Required: Issue Materials - WO WO-20260816-0001	Materials reserved for Work Order WO-20260816-0001. Please issue materials to begin production.	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	f	issue_materials_action	2026-08-16 20:02:24.921072+05:30	\N	/manufacturing/work-orders/6b2cc088-c47c-471d-9247-d33974e47a84	storekeeper
704d845a-4ec4-4cf3-82c6-cb6f7a8a8218	df413048-964e-45da-af55-91e90d7c54ee	\N	Materials Issued - WO WO-20260816-0001	All BOM materials have been issued for Work Order WO-20260816-0001. Production can begin.	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	f	material_issued	2026-08-16 20:04:09.855246+05:30	\N	/manufacturing/work-orders/6b2cc088-c47c-471d-9247-d33974e47a84	operator
13f80bd1-40a0-4ae6-9374-cf8ea45bc1f6	df413048-964e-45da-af55-91e90d7c54ee	\N	Action Required: Start Production - WO WO-20260816-0001	All materials issued for Work Order WO-20260816-0001. Production can now begin.	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	f	start_production_action	2026-08-16 20:04:09.879615+05:30	\N	/manufacturing/work-orders/6b2cc088-c47c-471d-9247-d33974e47a84	operator
04d82bf3-b315-4e38-b10e-f6a60e300137	df413048-964e-45da-af55-91e90d7c54ee	\N	FG Received - WO WO-20260816-0001	Finished goods received for Work Order WO-20260816-0001. Quantity: 1.0.	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	f	fg_received	2026-08-16 20:49:04.888288+05:30	\N	/manufacturing/work-orders/6b2cc088-c47c-471d-9247-d33974e47a84	dispatch
9a878644-5e7e-4c23-a408-cd0bd71e999e	df413048-964e-45da-af55-91e90d7c54ee	\N	Order SO-20260816-001 Ready for Dispatch	All materials allocated for order SO-20260816-001. Ready for dispatch.	sales_order	cdea16ef-befb-4d97-a598-25fa710f6ce8	f	ready_for_dispatch_action	2026-08-16 20:49:04.910346+05:30	\N	/sales/orders/cdea16ef-befb-4d97-a598-25fa710f6ce8	dispatch
7561442f-13ef-4747-80a3-43a87fb99d3a	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	Order SO-20260816-001 needs approval	test (None) requested test45 - xl x1. Open sales order SO-20260816-001 to review and approve.	sales_order	cdea16ef-befb-4d97-a598-25fa710f6ce8	t	SALES_ORDER_PENDING_APPROVAL	2026-08-16 20:02:09.94447+05:30	\N	\N	\N
4ce97aa1-6095-4a33-be10-21d579ec97db	df413048-964e-45da-af55-91e90d7c54ee	\N	Dispatch Completed - Order SO-20260816-001	Order SO-20260816-001 has been delivered. Auto-invoicing in progress.	sales_order	cdea16ef-befb-4d97-a598-25fa710f6ce8	f	dispatch_completed	2026-08-16 20:54:00.475958+05:30	\N	/sales/orders/cdea16ef-befb-4d97-a598-25fa710f6ce8	finance
ca1cede8-8419-40d6-9747-ff6d9fef2383	df413048-964e-45da-af55-91e90d7c54ee	\N	Payment Complete for Order SO-20260816-001	Full payment received for order SO-20260816-001. Order is now COMPLETED.	sales_order	cdea16ef-befb-4d97-a598-25fa710f6ce8	f	payment_received	2026-08-16 20:56:45.884812+05:30	\N	/sales/orders/cdea16ef-befb-4d97-a598-25fa710f6ce8	sales
f6f08fea-1f2b-490c-a391-679c12060e01	df413048-964e-45da-af55-91e90d7c54ee	\N	Work Order WO-20260816-0002 Released	Work Order WO-20260816-0002 has been released. Materials can be prepared.	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	f	wo_released	2026-08-16 21:01:48.614624+05:30	\N	/manufacturing/work-orders/66863c47-2254-44a6-b93e-6f9c7633c58b	storekeeper
25a33f57-165c-4e84-bbc7-b458e7fcb72f	df413048-964e-45da-af55-91e90d7c54ee	\N	Action Required: Issue Materials - WO WO-20260816-0002	Materials reserved for Work Order WO-20260816-0002. Please issue materials to begin production.	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	f	issue_materials_action	2026-08-16 21:01:48.617679+05:30	\N	/manufacturing/work-orders/66863c47-2254-44a6-b93e-6f9c7633c58b	storekeeper
1030605f-ed73-477d-ae82-2aa2ce54bf25	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	Production action required for SO-20260816-002	Sales order SO-20260816-002 was approved and needs production work order execution.	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	t	WORK_ORDER_ACTION_REQUIRED	2026-08-16 21:01:48.676823+05:30	\N	\N	\N
872f0694-af77-4e84-80c3-6b265c8dcbac	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	Order SO-20260816-002 needs approval	test (None) requested test45 - xl x1. Open sales order SO-20260816-002 to review and approve.	sales_order	bbe75209-17d6-4626-ad3e-df0bbdce24f9	t	SALES_ORDER_PENDING_APPROVAL	2026-08-16 21:01:31.890053+05:30	\N	\N	\N
5c841db1-c2f5-4472-b418-505761b17b52	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	Production action required for SO-20260816-001	Sales order SO-20260816-001 was approved and needs production work order execution.	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	t	WORK_ORDER_ACTION_REQUIRED	2026-08-16 20:02:24.984192+05:30	\N	\N	\N
9b39f1b4-31ba-40ce-8504-44896e90f47d	df413048-964e-45da-af55-91e90d7c54ee	\N	Materials Issued - WO WO-20260816-0002	All BOM materials have been issued for Work Order WO-20260816-0002. Production can begin.	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	f	material_issued	2026-08-16 21:11:13.329878+05:30	\N	/manufacturing/work-orders/66863c47-2254-44a6-b93e-6f9c7633c58b	operator
b7dc945c-580d-47a8-a5f7-308dc00579f4	df413048-964e-45da-af55-91e90d7c54ee	\N	Action Required: Start Production - WO WO-20260816-0002	All materials issued for Work Order WO-20260816-0002. Production can now begin.	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	f	start_production_action	2026-08-16 21:11:13.350563+05:30	\N	/manufacturing/work-orders/66863c47-2254-44a6-b93e-6f9c7633c58b	operator
c75a4f3f-c852-40ce-8b00-49e9c390b7de	df413048-964e-45da-af55-91e90d7c54ee	\N	FG Received - WO WO-20260816-0002	Finished goods received for Work Order WO-20260816-0002. Quantity: 1.0.	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	f	fg_received	2026-08-16 22:11:03.729631+05:30	\N	/manufacturing/work-orders/66863c47-2254-44a6-b93e-6f9c7633c58b	dispatch
da87c780-eb46-4d29-856d-33dc7023e4c3	df413048-964e-45da-af55-91e90d7c54ee	\N	Order SO-20260816-002 Ready for Dispatch	All materials allocated for order SO-20260816-002. Ready for dispatch.	sales_order	bbe75209-17d6-4626-ad3e-df0bbdce24f9	f	ready_for_dispatch_action	2026-08-16 22:11:03.755655+05:30	\N	/sales/orders/bbe75209-17d6-4626-ad3e-df0bbdce24f9	dispatch
b4a4d60e-2b1d-4e8b-a57f-df03c5ec2724	df413048-964e-45da-af55-91e90d7c54ee	\N	Dispatch Completed - Order SO-20260816-002	Order SO-20260816-002 has been delivered. Auto-invoicing in progress.	sales_order	bbe75209-17d6-4626-ad3e-df0bbdce24f9	f	dispatch_completed	2026-08-16 22:11:38.065199+05:30	\N	/sales/orders/bbe75209-17d6-4626-ad3e-df0bbdce24f9	finance
a737b530-4bfe-41bc-8414-bba40c8dc552	df413048-964e-45da-af55-91e90d7c54ee	\N	Payment Complete for Order SO-20260816-002	Full payment received for order SO-20260816-002. Order is now COMPLETED.	sales_order	bbe75209-17d6-4626-ad3e-df0bbdce24f9	f	payment_received	2026-08-16 22:22:12.60588+05:30	\N	/sales/orders/bbe75209-17d6-4626-ad3e-df0bbdce24f9	sales
\.


--
-- Data for Name: number_series_audit_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.number_series_audit_log (id, tenant_id, entity_type, event_type, entity_id, generated_code, old_value, new_value, user_id, "timestamp", metadata_json) FROM stdin;
ebff28ae-851b-4a06-a461-304b36f8cc7a	1e26d822-336a-4caf-b726-d5bc873bcd47	customer	generated	\N	CUST-000001	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 17:19:12.122826+05:30	{"sub_type": "", "entity_name": "tanveer"}
30164f1a-7978-4f31-ba02-6f94aba8c0c7	1e26d822-336a-4caf-b726-d5bc873bcd47	supplier	generated	\N	SUP-000001	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:26:34.481218+05:30	{"sub_type": "", "entity_name": "supplier1"}
8df466bd-89dc-418b-add9-529f99a51cbd	1e26d822-336a-4caf-b726-d5bc873bcd47	material	generated	\N	RM-GRB-000001	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-28 19:55:14.409495+05:30	{"sub_type": "raw", "entity_name": "Gear Rotameter Brass Body"}
fb132f8d-9d35-488f-be19-9a3eabcbe952	1e26d822-336a-4caf-b726-d5bc873bcd47	material	generated	\N	RM-GRS-000002	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-28 19:55:14.431536+05:30	{"sub_type": "raw", "entity_name": "Gear Rotameter SS Float"}
2a1c9235-3048-4162-b4c6-43baa2d521ab	1e26d822-336a-4caf-b726-d5bc873bcd47	material	generated	\N	RM-GRG-000003	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-28 19:55:14.446703+05:30	{"sub_type": "raw", "entity_name": "Gear Rotameter Gear Set"}
b2af3076-831e-48db-ac64-23350ae99fa0	1e26d822-336a-4caf-b726-d5bc873bcd47	material	generated	\N	RM-GRB-000004	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-28 19:55:14.469021+05:30	{"sub_type": "raw", "entity_name": "Gear Rotameter Borosilicate Glass Tube"}
b0a6918c-7727-4638-bc48-cf456d397efb	1e26d822-336a-4caf-b726-d5bc873bcd47	material	generated	\N	RM-GRN-000005	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-28 19:55:14.487817+05:30	{"sub_type": "raw", "entity_name": "Gear Rotameter NBR Gasket"}
c329861a-9f41-48fc-a832-bb68fe3e7534	7fd84f4a-c061-4774-a95d-415c4e67b6b6	customer	generated	\N	CUST-000001	\N	\N	71677bc0-be81-4b5b-94e0-3ac4de233185	2026-07-30 17:14:59.510452+05:30	{"sub_type": "", "entity_name": "Ashar Enterprise"}
ee8090d8-b566-44bf-ae92-21481b2717f4	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	generated	\N	FG-THE-000001	\N	\N	71677bc0-be81-4b5b-94e0-3ac4de233185	2026-07-30 17:38:53.38004+05:30	{"sub_type": "finished", "entity_name": "thermometer"}
7ffeb655-7518-4f2b-bba9-5f5ddf7196f9	df413048-964e-45da-af55-91e90d7c54ee	supplier	generated	\N	SUP-000001	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 13:54:56.691454+05:30	{"sub_type": "", "entity_name": "test1"}
6d2fb99d-be81-4904-b44a-f02dbaa16ebe	df413048-964e-45da-af55-91e90d7c54ee	material	generated	\N	RM-TES-000001	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-10-01 20:50:07.021832+05:30	{"sub_type": "raw", "entity_name": "tes1"}
b91fbe50-2732-49cc-86c0-ce1c18d1903b	df413048-964e-45da-af55-91e90d7c54ee	material	generated	\N	RM-BRA-000002	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-10-01 20:52:03.958602+05:30	{"sub_type": "raw", "entity_name": "brass2x"}
\.


--
-- Data for Name: number_series_config; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.number_series_config (id, tenant_id, entity_type, auto_generate, manual_override, prefix, include_abbreviation, abbreviation_length, sequence_length, separator, lock_after_save, created_at, updated_at) FROM stdin;
62c347ef-986a-46e4-9181-c6d23c4c3634	1e26d822-336a-4caf-b726-d5bc873bcd47	customer	t	admin_only	CUST	f	3	6	-	t	2026-07-25 17:18:45.369725+05:30	2026-07-25 17:18:45.369725+05:30
5eed682c-ad25-4fa2-b21a-b533b639d22b	1e26d822-336a-4caf-b726-d5bc873bcd47	material	t	never		t	3	6	-	t	2026-07-25 18:50:47.945551+05:30	2026-07-25 18:50:47.945551+05:30
9cc6c96d-dd68-4f23-985d-6ad1db941c0f	1e26d822-336a-4caf-b726-d5bc873bcd47	product	t	never	PRO	f	3	6	-	t	2026-07-25 18:50:47.978083+05:30	2026-07-25 18:50:47.978083+05:30
73829c7f-848b-480b-a19c-289ac68f679c	1e26d822-336a-4caf-b726-d5bc873bcd47	purchase_order	t	never	PO	f	3	6	-	t	2026-07-25 18:50:47.982089+05:30	2026-07-25 18:50:47.982089+05:30
61c6da3d-8ecb-444e-89c1-bbd0f5cde7f1	1e26d822-336a-4caf-b726-d5bc873bcd47	sales_order	t	never	SO	f	3	6	-	t	2026-07-25 18:50:47.986603+05:30	2026-07-25 18:50:47.986603+05:30
9f5bdfb3-d271-47d3-891a-b41d8effa504	1e26d822-336a-4caf-b726-d5bc873bcd47	invoice	t	never	INV	f	3	6	-	t	2026-07-25 18:50:47.990514+05:30	2026-07-25 18:50:47.990514+05:30
bd065b50-7756-42f9-9e0d-57dac4ff381e	1e26d822-336a-4caf-b726-d5bc873bcd47	grn	t	never	GRN	f	3	6	-	t	2026-07-25 18:50:47.992901+05:30	2026-07-25 18:50:47.992901+05:30
70c8b875-a57d-458b-b865-464e31c62c57	1e26d822-336a-4caf-b726-d5bc873bcd47	work_order	t	never	WO	f	3	6	-	t	2026-07-25 18:50:47.9968+05:30	2026-07-25 18:50:47.9968+05:30
62b01c7d-0fd5-461e-b4e6-7bd99c47938f	1e26d822-336a-4caf-b726-d5bc873bcd47	batch	t	never	BAT	f	3	6	-	t	2026-07-25 18:50:47.999572+05:30	2026-07-25 18:50:47.999572+05:30
c9b183d3-54ed-4bcd-96c7-6152d3609f60	1e26d822-336a-4caf-b726-d5bc873bcd47	supplier	t	admin_only	SUP	f	3	6	-	t	2026-07-25 18:50:48.004118+05:30	2026-07-25 18:50:48.004118+05:30
6c660a53-f50c-43a8-b11a-e99665809e93	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	t	never		t	3	6	-	t	2026-07-30 16:43:42.59596+05:30	2026-07-30 16:43:42.59596+05:30
e7134533-1731-46fc-90ba-4c103eabb199	7fd84f4a-c061-4774-a95d-415c4e67b6b6	product	t	never	PRO	f	3	6	-	t	2026-07-30 16:43:42.680453+05:30	2026-07-30 16:43:42.680453+05:30
cdc447a1-908a-4604-b87c-34d58882d8a9	7fd84f4a-c061-4774-a95d-415c4e67b6b6	purchase_order	t	never	PO	f	3	6	-	t	2026-07-30 16:43:42.700481+05:30	2026-07-30 16:43:42.700481+05:30
c95e79c5-f85f-448d-a126-4c63b55bb3c2	7fd84f4a-c061-4774-a95d-415c4e67b6b6	sales_order	t	never	SO	f	3	6	-	t	2026-07-30 16:43:42.711762+05:30	2026-07-30 16:43:42.711762+05:30
1fbc1298-605a-4e63-9bb1-9021c76d8c4e	7fd84f4a-c061-4774-a95d-415c4e67b6b6	invoice	t	never	INV	f	3	6	-	t	2026-07-30 16:43:42.718323+05:30	2026-07-30 16:43:42.718323+05:30
03207362-ac5a-425c-b42d-1481d44e91de	7fd84f4a-c061-4774-a95d-415c4e67b6b6	grn	t	never	GRN	f	3	6	-	t	2026-07-30 16:43:42.728305+05:30	2026-07-30 16:43:42.728305+05:30
14f54090-f0af-4685-9ce4-f1bbe18fba15	7fd84f4a-c061-4774-a95d-415c4e67b6b6	work_order	t	never	WO	f	3	6	-	t	2026-07-30 16:43:42.742813+05:30	2026-07-30 16:43:42.742813+05:30
428ec4e4-da92-4312-8c43-0ffb81ac00f2	7fd84f4a-c061-4774-a95d-415c4e67b6b6	batch	t	never	BAT	f	3	6	-	t	2026-07-30 16:43:42.758825+05:30	2026-07-30 16:43:42.758825+05:30
f3067fbc-01f1-4c00-aabb-7db5dff930e8	7fd84f4a-c061-4774-a95d-415c4e67b6b6	customer	t	admin_only	CUST	f	3	6	-	t	2026-07-30 16:43:42.771584+05:30	2026-07-30 16:43:42.771584+05:30
a953f8fa-7c0f-467f-ae9a-e67c77364c35	7fd84f4a-c061-4774-a95d-415c4e67b6b6	supplier	t	admin_only	SUP	f	3	6	-	t	2026-07-30 16:43:42.778902+05:30	2026-07-30 16:43:42.778902+05:30
3a80ebfe-3e6c-42a3-b712-1f3f635b7d23	df413048-964e-45da-af55-91e90d7c54ee	supplier	t	admin_only	SUP	f	3	6	-	t	2026-08-16 13:54:56.648801+05:30	2026-08-16 13:54:56.648801+05:30
95a43d8b-ea38-4f62-8385-4ec3d6b35b01	df413048-964e-45da-af55-91e90d7c54ee	material	t	never		t	3	6	-	t	2026-09-29 18:45:15.821817+05:30	2026-09-29 18:45:15.821817+05:30
ca14a4ed-dc32-4f07-a829-82dd49ce0e5b	df413048-964e-45da-af55-91e90d7c54ee	product	t	never	PRO	f	3	6	-	t	2026-09-29 18:45:15.865539+05:30	2026-09-29 18:45:15.865539+05:30
fc318281-f1a9-4696-a745-bea381a73f85	df413048-964e-45da-af55-91e90d7c54ee	purchase_order	t	never	PO	f	3	6	-	t	2026-09-29 18:45:15.870798+05:30	2026-09-29 18:45:15.870798+05:30
e69784bb-1b67-424f-8ec1-26686ea0cedc	df413048-964e-45da-af55-91e90d7c54ee	sales_order	t	never	SO	f	3	6	-	t	2026-09-29 18:45:15.876001+05:30	2026-09-29 18:45:15.876001+05:30
68b605f4-649f-419a-bb25-3a1be3f99c01	df413048-964e-45da-af55-91e90d7c54ee	invoice	t	never	INV	f	3	6	-	t	2026-09-29 18:45:15.879917+05:30	2026-09-29 18:45:15.879917+05:30
e61921ea-9ce8-4581-8366-67142b00c4fb	df413048-964e-45da-af55-91e90d7c54ee	grn	t	never	GRN	f	3	6	-	t	2026-09-29 18:45:15.885375+05:30	2026-09-29 18:45:15.885375+05:30
d655e2a0-be99-47a9-90bd-686010576944	df413048-964e-45da-af55-91e90d7c54ee	work_order	t	never	WO	f	3	6	-	t	2026-09-29 18:45:15.890502+05:30	2026-09-29 18:45:15.890502+05:30
46e2660f-9757-4fa7-a8cf-ff98c0800b45	df413048-964e-45da-af55-91e90d7c54ee	batch	t	never	BAT	f	3	6	-	t	2026-09-29 18:45:15.894307+05:30	2026-09-29 18:45:15.894307+05:30
a4c85339-a344-4e3e-acf8-bdcc9ca12934	df413048-964e-45da-af55-91e90d7c54ee	customer	t	admin_only	CUST	f	3	6	-	t	2026-09-29 18:45:15.899464+05:30	2026-09-29 18:45:15.899464+05:30
\.


--
-- Data for Name: number_series_prefixes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.number_series_prefixes (id, tenant_id, entity_type, sub_type, prefix, is_active, created_at, updated_at) FROM stdin;
082d7a65-8de1-4b11-985a-43dd0c92b401	1e26d822-336a-4caf-b726-d5bc873bcd47	material	raw	RM	t	2026-07-25 18:50:47.961028+05:30	2026-07-25 18:50:47.961028+05:30
6ba69738-5085-46cd-9fcf-ac0707fbf828	1e26d822-336a-4caf-b726-d5bc873bcd47	material	finished	FG	t	2026-07-25 18:50:47.961028+05:30	2026-07-25 18:50:47.961028+05:30
c45c1013-447f-4ef1-9d2b-a69a68774c8f	1e26d822-336a-4caf-b726-d5bc873bcd47	material	semi_finished	SF	t	2026-07-25 18:50:47.961028+05:30	2026-07-25 18:50:47.961028+05:30
b418a638-a106-49f3-bd70-4e313464b6d3	1e26d822-336a-4caf-b726-d5bc873bcd47	material	consumable	CON	t	2026-07-25 18:50:47.961028+05:30	2026-07-25 18:50:47.961028+05:30
a42eee02-c2d1-4009-81a7-ca3e96ba4750	1e26d822-336a-4caf-b726-d5bc873bcd47	material	packaging	PKG	t	2026-07-25 18:50:47.961028+05:30	2026-07-25 18:50:47.961028+05:30
35c2ae6b-ec02-434f-ae7b-0c82f3070996	1e26d822-336a-4caf-b726-d5bc873bcd47	material	spare	SPR	t	2026-07-25 18:50:47.961028+05:30	2026-07-25 18:50:47.961028+05:30
4bb93cc3-0c27-4529-9a8d-6aa2f1f27763	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	raw	RM	t	2026-07-30 16:43:42.622386+05:30	2026-07-30 16:43:42.622386+05:30
c21bcdc2-594f-4d98-91f2-3b6333d90cdb	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	finished	FG	t	2026-07-30 16:43:42.622386+05:30	2026-07-30 16:43:42.622386+05:30
92952c9e-3da7-45d7-9d2d-645a5040a6fa	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	semi_finished	SF	t	2026-07-30 16:43:42.622386+05:30	2026-07-30 16:43:42.622386+05:30
782f0c20-4027-40fa-bdd5-19a42b5d6281	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	consumable	CON	t	2026-07-30 16:43:42.622386+05:30	2026-07-30 16:43:42.622386+05:30
af314a5a-bbfa-4d34-b27b-389446770d0a	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	packaging	PKG	t	2026-07-30 16:43:42.622386+05:30	2026-07-30 16:43:42.622386+05:30
327984ef-9de0-4237-99e5-3111b070b290	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	spare	SPR	t	2026-07-30 16:43:42.622386+05:30	2026-07-30 16:43:42.622386+05:30
8f107c84-47d6-4a82-b5a7-ff938e4a8c4c	df413048-964e-45da-af55-91e90d7c54ee	material	raw	RM	t	2026-09-29 18:45:15.830724+05:30	2026-09-29 18:45:15.830724+05:30
3c7d6ad6-62ff-4101-8b9a-1262a6f4cf34	df413048-964e-45da-af55-91e90d7c54ee	material	finished	FG	t	2026-09-29 18:45:15.830724+05:30	2026-09-29 18:45:15.830724+05:30
2b829da6-80ab-4a05-b843-7f70c01407fc	df413048-964e-45da-af55-91e90d7c54ee	material	semi_finished	SF	t	2026-09-29 18:45:15.830724+05:30	2026-09-29 18:45:15.830724+05:30
41a84917-9df8-4403-b60f-7c4f8924ff77	df413048-964e-45da-af55-91e90d7c54ee	material	consumable	CON	t	2026-09-29 18:45:15.830724+05:30	2026-09-29 18:45:15.830724+05:30
91036738-6496-4dab-bd89-8bd505130e1a	df413048-964e-45da-af55-91e90d7c54ee	material	packaging	PKG	t	2026-09-29 18:45:15.830724+05:30	2026-09-29 18:45:15.830724+05:30
381cd57e-fa28-4c2a-97cf-94061c3c4970	df413048-964e-45da-af55-91e90d7c54ee	material	spare	SPR	t	2026-09-29 18:45:15.830724+05:30	2026-09-29 18:45:15.830724+05:30
\.


--
-- Data for Name: number_series_sequences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.number_series_sequences (id, tenant_id, entity_type, prefix, next_number, created_at, updated_at) FROM stdin;
d8aa4201-27ae-4f53-b171-3a026ea81d40	1e26d822-336a-4caf-b726-d5bc873bcd47	customer	CUST	2	2026-07-25 17:19:12.111055+05:30	2026-07-25 17:19:12.147993+05:30
5d89962e-8112-43e5-a961-70f7aee8924d	1e26d822-336a-4caf-b726-d5bc873bcd47	supplier	SUP	2	2026-07-26 00:26:34.463451+05:30	2026-07-26 00:26:34.503325+05:30
5e18089d-368f-4c59-8a2b-fdc9c3cffbb5	1e26d822-336a-4caf-b726-d5bc873bcd47	material	RM	6	2026-07-28 19:55:14.384786+05:30	2026-07-28 19:55:14.562518+05:30
929eac63-27a7-420a-925d-9b33990c556c	7fd84f4a-c061-4774-a95d-415c4e67b6b6	customer	CUST	2	2026-07-30 17:14:59.477672+05:30	2026-07-30 17:14:59.569539+05:30
8bb9dcf5-c6a7-4d5b-9f19-c1ab440f8189	7fd84f4a-c061-4774-a95d-415c4e67b6b6	material	FG	2	2026-07-30 17:38:53.363608+05:30	2026-07-30 17:38:53.430922+05:30
0c98d84d-d918-48e7-b52b-d6584200e7cf	df413048-964e-45da-af55-91e90d7c54ee	supplier	SUP	2	2026-08-16 13:54:56.672546+05:30	2026-08-16 13:54:56.705048+05:30
dc300e75-cab9-4c61-a803-e01d616c4a73	df413048-964e-45da-af55-91e90d7c54ee	material	RM	3	2026-10-01 20:50:07.00919+05:30	2026-10-01 20:52:03.963781+05:30
\.


--
-- Data for Name: operations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.operations (id, tenant_id, name, workstation_id, setup_time, run_time, description, is_active, is_deleted, created_at, updated_at, operation_code, operation_type, default_sequence, estimated_time_minutes, qc_required, color, icon_code, created_by, deleted_at) FROM stdin;
a786d4ce-f6fd-4b90-8d00-17478a4a38c1	ecd10cf6-8f87-4799-977e-329aa315fce5	Final Assembly	a344f734-88d6-43e4-a0a3-5ca4bd65600c	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:49:44.126149+05:30	2026-03-25 00:49:44.126149+05:30	\N	other	10	\N	f	\N	\N	\N	\N
578bafb5-8025-42f1-804d-8d134c056b59	7b49262e-fa65-429c-af38-e8202ea42a19	Final Assembly c582c485	84593aab-b841-4ef5-b458-2467f0d6aed1	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:51:21.444766+05:30	2026-03-25 00:51:21.444766+05:30	\N	other	10	\N	f	\N	\N	\N	\N
1cfb2c4c-2cac-42f2-b692-6a32b30b584c	6761d5db-efea-4b6c-846a-2149fe6a9ce8	Final Assembly fefc3912	d05241b9-867e-45ca-ba7d-5cc7caaf49dc	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:53:04.93364+05:30	2026-03-25 00:53:04.93364+05:30	\N	other	10	\N	f	\N	\N	\N	\N
faee8d55-f6f2-4c7e-91ca-aac0cf57469d	e0bac4d7-0c65-4431-84c7-689d3e36fe96	Final Assembly 715b396c	b3a4cd1c-6f1f-40ed-a845-fbad36d09645	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:53:28.6537+05:30	2026-03-25 00:53:28.6537+05:30	\N	other	10	\N	f	\N	\N	\N	\N
a7421aa7-ca7c-4eaf-8f6a-15c349b0ec81	034b1e67-f747-4bd2-814a-c42edb05118f	Final Assembly e3c721c3	b197f881-87c3-4a40-a955-ff5030ae91ec	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:56:33.145618+05:30	2026-03-25 00:56:33.145618+05:30	\N	other	10	\N	f	\N	\N	\N	\N
724d1e6f-7e3d-489a-adc4-e5b80310bf7e	da7238a4-595f-4444-9c6b-129a843ea42a	Final Assembly a22d8d28	79a5a5e1-9eab-4b18-a8bb-51a56e8027b8	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:58:41.046641+05:30	2026-03-25 00:58:41.046641+05:30	\N	other	10	\N	f	\N	\N	\N	\N
ab800f38-1c58-4247-8283-3244924335c5	e7379c9c-57db-46df-99a6-93ef64558339	Final Assembly df6441c6	4d5cfecd-daf9-4628-beb2-d23258ecff17	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:59:34.777193+05:30	2026-03-25 00:59:34.777193+05:30	\N	other	10	\N	f	\N	\N	\N	\N
26dce8a1-ee56-4250-9e64-947eb9c7b4c6	a3f0c1be-c5e4-417e-8da2-32ea3724327f	Final Assembly 9646d609	7d542f3c-14bc-4094-8a93-cfcd19a27131	30.00	15.00	Assemble components into final product	t	f	2026-03-25 00:59:59.276669+05:30	2026-03-25 00:59:59.276669+05:30	\N	other	10	\N	f	\N	\N	\N	\N
83833e82-6ada-45d2-95ea-80f36f326c77	5d335ba3-e57b-4de0-92b2-1777f6171e22	Final Assembly 99a36abc	09e58201-873e-4a0e-bb7c-ce08035a51eb	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:01:25.404752+05:30	2026-03-25 01:01:25.404752+05:30	\N	other	10	\N	f	\N	\N	\N	\N
93de85ba-d728-4a68-8c7e-590f9414bc33	1dad4af1-4778-4b1b-9903-8743b42e39f9	Final Assembly f402cbe0	7483abc2-3c07-4833-a8f0-dec13441d7fb	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:02:17.984896+05:30	2026-03-25 01:02:17.984896+05:30	\N	other	10	\N	f	\N	\N	\N	\N
a543cb9e-e009-4fb3-92b0-2d765aaa2ca6	162f0993-8bb2-49bb-9e0f-5d7e7e194cb7	Final Assembly d575a166	1f1a439d-6a19-46ca-8a42-725e6dfa8984	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:03:10.145596+05:30	2026-03-25 01:03:10.145596+05:30	\N	other	10	\N	f	\N	\N	\N	\N
9ff5ffe0-c7f9-4409-8b55-9aa4f595f1d5	6e48eee2-1bab-4551-bce5-6a657d1fae9f	Final Assembly 88cc3b70	97adba67-3e66-46c7-aa8d-4de468519579	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:04:44.43576+05:30	2026-03-25 01:04:44.43576+05:30	\N	other	10	\N	f	\N	\N	\N	\N
cae5a290-d46a-48a6-9160-29209e7fc619	eeedd636-a313-40df-9a2d-2621ab48c0e1	Final Assembly b33437b0	fac5ec60-527f-44e0-abce-4fb092eda352	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:06:10.999939+05:30	2026-03-25 01:06:10.999939+05:30	\N	other	10	\N	f	\N	\N	\N	\N
ee84d58d-0b5b-43af-bf77-a411e157b885	6afa3b75-463b-4011-bd29-698b1dae95f2	Final Assembly fc1f6c2c	4093ae43-f26f-494b-83c0-3168eb2cf80f	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:07:53.874161+05:30	2026-03-25 01:07:53.874161+05:30	\N	other	10	\N	f	\N	\N	\N	\N
0c2f00fc-df24-4bc2-85c1-46204e93b420	a423b246-7db4-4dbf-b891-760e9c35d893	Final Assembly 6d41e4f6	c10853ea-d61c-43bf-8976-105e086f6c22	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:22:18.045834+05:30	2026-03-25 01:22:18.045834+05:30	\N	other	10	\N	f	\N	\N	\N	\N
9ce35d3e-f608-4ddd-ad1e-a6bf8f6d6699	642dcd91-014a-4499-9ba1-2fe7a08cd38b	Final Assembly cf0c6331	682a6620-676e-4602-b7a8-5d063a1b2696	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:23:13.104911+05:30	2026-03-25 01:23:13.104911+05:30	\N	other	10	\N	f	\N	\N	\N	\N
f30d572b-3610-409e-8f64-549ba07b6e38	5d6c5ec5-1446-4857-8dc9-29a4d988a1fd	Final Assembly f1d4b7dd	8a5851f8-69c6-4485-a95f-0b0d856fbffd	30.00	15.00	Assemble components into final product	t	f	2026-03-25 01:23:55.721776+05:30	2026-03-25 01:23:55.721776+05:30	\N	other	10	\N	f	\N	\N	\N	\N
80487af5-5efc-417b-8ae8-cba55f5c3453	e3804850-ccb5-47da-b1af-35799d48e960	SMT Component Placement	7cff87eb-292a-472f-8a52-29c658f5e561	30.00	45.00	\N	t	f	2026-03-27 15:17:37.479136+05:30	2026-03-27 15:17:37.479136+05:30	\N	other	10	\N	f	\N	\N	\N	\N
414ea770-c27a-4044-a1c7-7a5ebc40763e	e3804850-ccb5-47da-b1af-35799d48e960	SMT Reflow Soldering	7cff87eb-292a-472f-8a52-29c658f5e561	20.00	25.00	\N	t	f	2026-03-27 15:17:37.520024+05:30	2026-03-27 15:17:37.520024+05:30	\N	other	10	\N	f	\N	\N	\N	\N
29807f0e-8e6c-41da-9914-b4775a307716	e3804850-ccb5-47da-b1af-35799d48e960	AOI Inspection	cd3e87cf-be0c-454d-a573-4eb277f87992	10.00	15.00	\N	t	f	2026-03-27 15:17:37.547475+05:30	2026-03-27 15:17:37.547475+05:30	\N	other	10	\N	f	\N	\N	\N	\N
8a87ac91-f6d9-4960-b7f9-cf9cb1e5e34b	e3804850-ccb5-47da-b1af-35799d48e960	Through-Hole Insertion	6353efd7-1cdb-45d3-9fd0-47368c72699e	15.00	30.00	\N	t	f	2026-03-27 15:17:37.572372+05:30	2026-03-27 15:17:37.572372+05:30	\N	other	10	\N	f	\N	\N	\N	\N
13c30a83-dad8-4ac8-9671-b6f040a6ec27	e3804850-ccb5-47da-b1af-35799d48e960	Wave Soldering	86af6a79-430c-434e-be3c-fe79de509716	20.00	20.00	\N	t	f	2026-03-27 15:17:37.597489+05:30	2026-03-27 15:17:37.597489+05:30	\N	other	10	\N	f	\N	\N	\N	\N
dba72a54-94f6-4602-b385-2b756ddbee27	e3804850-ccb5-47da-b1af-35799d48e960	Housing Assembly	0a846638-5348-406b-8265-378bb343962d	10.00	20.00	\N	t	f	2026-03-27 15:17:37.620292+05:30	2026-03-27 15:17:37.620292+05:30	\N	other	10	\N	f	\N	\N	\N	\N
d710d130-b364-4b44-b602-2ebcc4db40e0	e3804850-ccb5-47da-b1af-35799d48e960	Functional Testing	34b59a02-9260-427f-8c67-a174b0a27431	5.00	30.00	\N	t	f	2026-03-27 15:17:37.647388+05:30	2026-03-27 15:17:37.647388+05:30	\N	other	10	\N	f	\N	\N	\N	\N
57728c6e-03cb-4a1a-9640-bc35d55f9f01	e3804850-ccb5-47da-b1af-35799d48e960	Quality Check	4d599e55-c73f-4a53-be6f-cb97daae037a	5.00	15.00	\N	t	f	2026-03-27 15:17:37.67135+05:30	2026-03-27 15:17:37.67135+05:30	\N	other	10	\N	f	\N	\N	\N	\N
4a26b54b-b205-4aeb-87ba-ac704b0b5e74	e3804850-ccb5-47da-b1af-35799d48e960	Final Packaging	6af843a3-cdfd-4502-a403-3588fa00317c	5.00	10.00	\N	t	f	2026-03-27 15:17:37.698906+05:30	2026-03-27 15:17:37.698906+05:30	\N	other	10	\N	f	\N	\N	\N	\N
cb207919-929d-4661-b50b-66bf7fc0da78	e3804850-ccb5-47da-b1af-35799d48e960	Firmware Flash	34b59a02-9260-427f-8c67-a174b0a27431	10.00	15.00	\N	t	f	2026-03-27 15:17:37.726471+05:30	2026-03-27 15:17:37.726471+05:30	\N	other	10	\N	f	\N	\N	\N	\N
03cfa061-82fd-4b7b-b062-0059593e778b	5fea589e-6bfc-4147-a1ea-bb7c939c384e	SMT Component Placement	9a1559d3-8ab6-45bf-b06d-ff396e5ff537	30.00	45.00	\N	t	f	2026-03-27 17:31:19.991641+05:30	2026-03-27 17:31:19.991641+05:30	\N	other	10	\N	f	\N	\N	\N	\N
89a11918-e8c9-4994-b705-16540e82a81b	5fea589e-6bfc-4147-a1ea-bb7c939c384e	SMT Reflow Soldering	9a1559d3-8ab6-45bf-b06d-ff396e5ff537	20.00	25.00	\N	t	f	2026-03-27 17:31:20.029574+05:30	2026-03-27 17:31:20.029574+05:30	\N	other	10	\N	f	\N	\N	\N	\N
1c0e10a5-7714-4183-94f5-a8b720f3cb13	5fea589e-6bfc-4147-a1ea-bb7c939c384e	AOI Inspection	fc06d78f-d995-4049-b39a-5101e8663fe0	10.00	15.00	\N	t	f	2026-03-27 17:31:20.054203+05:30	2026-03-27 17:31:20.054203+05:30	\N	other	10	\N	f	\N	\N	\N	\N
278355ff-9831-4e5b-b751-f4cdfbf53334	5fea589e-6bfc-4147-a1ea-bb7c939c384e	Through-Hole Insertion	5b125a53-ad73-4dc1-8177-072fb6fed9a9	15.00	30.00	\N	t	f	2026-03-27 17:31:20.077407+05:30	2026-03-27 17:31:20.077407+05:30	\N	other	10	\N	f	\N	\N	\N	\N
2fc4d1fd-f946-4ea4-87a3-fb4f24b2d825	5fea589e-6bfc-4147-a1ea-bb7c939c384e	Wave Soldering	562786f2-59de-468c-a307-14ad399db89c	20.00	20.00	\N	t	f	2026-03-27 17:31:20.102516+05:30	2026-03-27 17:31:20.102516+05:30	\N	other	10	\N	f	\N	\N	\N	\N
caf58be1-7896-40ff-a6ff-c6f576c26d99	5fea589e-6bfc-4147-a1ea-bb7c939c384e	Housing Assembly	eb56d441-26d6-4c52-98d1-b433ad878554	10.00	20.00	\N	t	f	2026-03-27 17:31:20.127067+05:30	2026-03-27 17:31:20.127067+05:30	\N	other	10	\N	f	\N	\N	\N	\N
7206a4b5-d4be-4675-9c38-7352269e7d11	5fea589e-6bfc-4147-a1ea-bb7c939c384e	Functional Testing	02ee9bcc-a160-40c7-bc23-51bac13a89fe	5.00	30.00	\N	t	f	2026-03-27 17:31:20.150448+05:30	2026-03-27 17:31:20.150448+05:30	\N	other	10	\N	f	\N	\N	\N	\N
f6c66930-30b2-4c90-aa13-e827a5794fd2	5fea589e-6bfc-4147-a1ea-bb7c939c384e	Quality Check	831eb7f5-b65e-47fb-8cda-9a553fd1d49d	5.00	15.00	\N	t	f	2026-03-27 17:31:20.175427+05:30	2026-03-27 17:31:20.175427+05:30	\N	other	10	\N	f	\N	\N	\N	\N
2a39f141-f809-47ca-a6fa-4356c697a236	5fea589e-6bfc-4147-a1ea-bb7c939c384e	Final Packaging	5b4e3a8c-5b65-4fbf-b348-4e3a84bfbaca	5.00	10.00	\N	t	f	2026-03-27 17:31:20.200237+05:30	2026-03-27 17:31:20.200237+05:30	\N	other	10	\N	f	\N	\N	\N	\N
3d9591d9-a6da-4798-8489-4c9387ded886	5fea589e-6bfc-4147-a1ea-bb7c939c384e	Firmware Flash	02ee9bcc-a160-40c7-bc23-51bac13a89fe	10.00	15.00	\N	t	f	2026-03-27 17:31:20.223774+05:30	2026-03-27 17:31:20.223774+05:30	\N	other	10	\N	f	\N	\N	\N	\N
900efbb3-5cd3-4bb4-8cef-ac2179d319ca	b786c809-d01e-42db-8bac-0d5215891da9	SMT Component Placement	e165fd0c-9089-4b1c-ae55-c4dd08c01ce2	30.00	45.00	\N	t	f	2026-03-27 17:35:00.660573+05:30	2026-03-27 17:35:00.660573+05:30	\N	other	10	\N	f	\N	\N	\N	\N
afd5e612-a9a2-463c-83a9-08e999bbab61	b786c809-d01e-42db-8bac-0d5215891da9	SMT Reflow Soldering	e165fd0c-9089-4b1c-ae55-c4dd08c01ce2	20.00	25.00	\N	t	f	2026-03-27 17:35:00.680764+05:30	2026-03-27 17:35:00.680764+05:30	\N	other	10	\N	f	\N	\N	\N	\N
99e58601-4ddd-4519-bfba-0e8061e39424	b786c809-d01e-42db-8bac-0d5215891da9	AOI Inspection	520d692b-36e1-4144-b67c-c8fcd83f8860	10.00	15.00	\N	t	f	2026-03-27 17:35:00.693104+05:30	2026-03-27 17:35:00.693104+05:30	\N	other	10	\N	f	\N	\N	\N	\N
05b09cc4-5bf8-4578-9943-5e92be22186a	b786c809-d01e-42db-8bac-0d5215891da9	Through-Hole Insertion	775b1569-4a79-4b61-8ba1-d142797ee63c	15.00	30.00	\N	t	f	2026-03-27 17:35:00.709934+05:30	2026-03-27 17:35:00.709934+05:30	\N	other	10	\N	f	\N	\N	\N	\N
0513168e-3e4a-4fdc-8c0f-6577a0cc56d3	b786c809-d01e-42db-8bac-0d5215891da9	Wave Soldering	7f52d8d9-561b-4d89-8e15-aeee0b3a5dda	20.00	20.00	\N	t	f	2026-03-27 17:35:00.721822+05:30	2026-03-27 17:35:00.721822+05:30	\N	other	10	\N	f	\N	\N	\N	\N
44131df1-cf33-4a47-add9-70a054fe154a	b786c809-d01e-42db-8bac-0d5215891da9	Housing Assembly	9644ed85-c21f-44b9-84ca-c556b271090a	10.00	20.00	\N	t	f	2026-03-27 17:35:00.732736+05:30	2026-03-27 17:35:00.732736+05:30	\N	other	10	\N	f	\N	\N	\N	\N
4c142b1a-8f4e-4d18-b8a1-0484d5e685a2	b786c809-d01e-42db-8bac-0d5215891da9	Functional Testing	b1f37c8e-e966-4656-87b3-e5cce9cc5573	5.00	30.00	\N	t	f	2026-03-27 17:35:00.744289+05:30	2026-03-27 17:35:00.744289+05:30	\N	other	10	\N	f	\N	\N	\N	\N
ab96aeb1-4ebb-40b7-bb8d-452f5e645a7e	b786c809-d01e-42db-8bac-0d5215891da9	Quality Check	7b9fbdb6-6d9d-423b-bd6c-cf1b94e94506	5.00	15.00	\N	t	f	2026-03-27 17:35:00.756372+05:30	2026-03-27 17:35:00.756372+05:30	\N	other	10	\N	f	\N	\N	\N	\N
a0c05547-0576-4211-bb98-cf69327a5bd2	b786c809-d01e-42db-8bac-0d5215891da9	Final Packaging	46b4e490-5163-4a2b-bfcb-bbe7728aa87c	5.00	10.00	\N	t	f	2026-03-27 17:35:00.768155+05:30	2026-03-27 17:35:00.768155+05:30	\N	other	10	\N	f	\N	\N	\N	\N
be4fe7d8-1329-4960-b1ea-1cb207a0c126	b786c809-d01e-42db-8bac-0d5215891da9	Firmware Flash	b1f37c8e-e966-4656-87b3-e5cce9cc5573	10.00	15.00	\N	t	f	2026-03-27 17:35:00.779628+05:30	2026-03-27 17:35:00.779628+05:30	\N	other	10	\N	f	\N	\N	\N	\N
2cb9bada-8afd-4cce-bb43-d6210a3dfd27	3b2413e8-d980-4aab-92f1-ea83e77d4702	SMT Component Placement	e9f3e606-c3cf-4fb6-9970-4396e4e5b806	30.00	45.00	\N	t	f	2026-03-27 17:42:41.178479+05:30	2026-03-27 17:42:41.178479+05:30	\N	other	10	\N	f	\N	\N	\N	\N
24d1e37a-5085-4281-a6d8-256495d57cb7	3b2413e8-d980-4aab-92f1-ea83e77d4702	SMT Reflow Soldering	e9f3e606-c3cf-4fb6-9970-4396e4e5b806	20.00	25.00	\N	t	f	2026-03-27 17:42:41.198748+05:30	2026-03-27 17:42:41.198748+05:30	\N	other	10	\N	f	\N	\N	\N	\N
9817db41-7410-4a59-87fb-b5e238a4024b	3b2413e8-d980-4aab-92f1-ea83e77d4702	AOI Inspection	93196495-f633-43a2-9b21-6538ddedf9c5	10.00	15.00	\N	t	f	2026-03-27 17:42:41.210917+05:30	2026-03-27 17:42:41.210917+05:30	\N	other	10	\N	f	\N	\N	\N	\N
8844f468-1345-4230-9b01-9794441e1477	3b2413e8-d980-4aab-92f1-ea83e77d4702	Through-Hole Insertion	e97ecf7d-1b64-42fc-91d6-2437f2d1e923	15.00	30.00	\N	t	f	2026-03-27 17:42:41.22396+05:30	2026-03-27 17:42:41.22396+05:30	\N	other	10	\N	f	\N	\N	\N	\N
dc1eac89-0672-42d6-80fd-29dcedf3cab2	3b2413e8-d980-4aab-92f1-ea83e77d4702	Wave Soldering	a9eb326c-7459-4976-b08d-105a82dda3e7	20.00	20.00	\N	t	f	2026-03-27 17:42:41.235184+05:30	2026-03-27 17:42:41.235184+05:30	\N	other	10	\N	f	\N	\N	\N	\N
543df843-a516-488c-afdd-3d38655bd728	3b2413e8-d980-4aab-92f1-ea83e77d4702	Housing Assembly	518a31a4-4384-44f7-950e-57efb7336da5	10.00	20.00	\N	t	f	2026-03-27 17:42:41.245792+05:30	2026-03-27 17:42:41.245792+05:30	\N	other	10	\N	f	\N	\N	\N	\N
aeecde53-c2c3-420d-ba12-42d5cd851061	3b2413e8-d980-4aab-92f1-ea83e77d4702	Functional Testing	c89c3dbf-472e-4691-9b48-5e749bead7b3	5.00	30.00	\N	t	f	2026-03-27 17:42:41.255658+05:30	2026-03-27 17:42:41.255658+05:30	\N	other	10	\N	f	\N	\N	\N	\N
13a9d32d-d5e9-4f38-b05e-dc2c3b2870b6	3b2413e8-d980-4aab-92f1-ea83e77d4702	Quality Check	c86c0514-cd53-46d6-a671-3f1d0749236d	5.00	15.00	\N	t	f	2026-03-27 17:42:41.266233+05:30	2026-03-27 17:42:41.266233+05:30	\N	other	10	\N	f	\N	\N	\N	\N
9de82029-909a-4209-80cc-fa4edb9367c4	3b2413e8-d980-4aab-92f1-ea83e77d4702	Final Packaging	a5249fa2-0491-4267-9c43-0a54e02dd73d	5.00	10.00	\N	t	f	2026-03-27 17:42:41.277408+05:30	2026-03-27 17:42:41.277408+05:30	\N	other	10	\N	f	\N	\N	\N	\N
2da8c9ae-5a4c-4df1-a811-93c05d05a9ac	3b2413e8-d980-4aab-92f1-ea83e77d4702	Firmware Flash	c89c3dbf-472e-4691-9b48-5e749bead7b3	10.00	15.00	\N	t	f	2026-03-27 17:42:41.287862+05:30	2026-03-27 17:42:41.287862+05:30	\N	other	10	\N	f	\N	\N	\N	\N
a9dc525e-b055-4900-81c8-817784386275	d419f37b-9866-40b0-8e5a-c908748fdbe7	SMT Component Placement	c8ff00df-de90-4a64-bba1-d0f14fe582b1	30.00	45.00	\N	t	f	2026-03-27 17:44:33.909523+05:30	2026-03-27 17:44:33.909523+05:30	\N	other	10	\N	f	\N	\N	\N	\N
0bab6f4e-3977-425b-9670-520ce0855f0d	d419f37b-9866-40b0-8e5a-c908748fdbe7	SMT Reflow Soldering	c8ff00df-de90-4a64-bba1-d0f14fe582b1	20.00	25.00	\N	t	f	2026-03-27 17:44:33.929091+05:30	2026-03-27 17:44:33.929091+05:30	\N	other	10	\N	f	\N	\N	\N	\N
3558c505-4b79-45eb-9b1d-e397c04eea68	d419f37b-9866-40b0-8e5a-c908748fdbe7	AOI Inspection	47609d10-e4fb-4479-832d-87bac0fdca93	10.00	15.00	\N	t	f	2026-03-27 17:44:33.93989+05:30	2026-03-27 17:44:33.93989+05:30	\N	other	10	\N	f	\N	\N	\N	\N
71702af6-4fcb-4291-9797-06b7cdefdf22	d419f37b-9866-40b0-8e5a-c908748fdbe7	Through-Hole Insertion	6842b4de-08c3-4e73-9007-86adaf78b136	15.00	30.00	\N	t	f	2026-03-27 17:44:33.950636+05:30	2026-03-27 17:44:33.950636+05:30	\N	other	10	\N	f	\N	\N	\N	\N
41c33769-d812-4740-9407-f6e95ba84d7e	d419f37b-9866-40b0-8e5a-c908748fdbe7	Wave Soldering	c788b138-40d8-4333-8a8b-c2e2bb934efd	20.00	20.00	\N	t	f	2026-03-27 17:44:33.962726+05:30	2026-03-27 17:44:33.962726+05:30	\N	other	10	\N	f	\N	\N	\N	\N
83295a18-7fe1-445b-9e64-97efbcde9d32	d419f37b-9866-40b0-8e5a-c908748fdbe7	Housing Assembly	f8fdc6e6-0950-46da-b34a-f23471a81a8a	10.00	20.00	\N	t	f	2026-03-27 17:44:33.972628+05:30	2026-03-27 17:44:33.972628+05:30	\N	other	10	\N	f	\N	\N	\N	\N
1625d9ea-3707-446e-9aeb-974e70b1f424	d419f37b-9866-40b0-8e5a-c908748fdbe7	Functional Testing	aa2dbc1e-8b93-453f-8576-d950e79ccc47	5.00	30.00	\N	t	f	2026-03-27 17:44:33.98415+05:30	2026-03-27 17:44:33.98415+05:30	\N	other	10	\N	f	\N	\N	\N	\N
4b8234e6-807a-4beb-918d-68cafcda54a0	d419f37b-9866-40b0-8e5a-c908748fdbe7	Quality Check	772bfc46-fafe-40e4-aced-399a57446e96	5.00	15.00	\N	t	f	2026-03-27 17:44:33.994112+05:30	2026-03-27 17:44:33.994112+05:30	\N	other	10	\N	f	\N	\N	\N	\N
f17b50a2-e819-4b79-a294-0c987cad07a5	d419f37b-9866-40b0-8e5a-c908748fdbe7	Final Packaging	ebd6ba54-e180-453f-bed6-2ba45cc0f36b	5.00	10.00	\N	t	f	2026-03-27 17:44:34.00397+05:30	2026-03-27 17:44:34.00397+05:30	\N	other	10	\N	f	\N	\N	\N	\N
957aea84-d12f-4e7d-97c4-14b1ddd0b0c5	d419f37b-9866-40b0-8e5a-c908748fdbe7	Firmware Flash	aa2dbc1e-8b93-453f-8576-d950e79ccc47	10.00	15.00	\N	t	f	2026-03-27 17:44:34.014645+05:30	2026-03-27 17:44:34.014645+05:30	\N	other	10	\N	f	\N	\N	\N	\N
ffdcc214-61c6-4540-a835-6efd2c4acf6d	234f9697-c95a-4356-91aa-b3c42a1d9a17	SMT Component Placement	837e8921-ebb2-4adc-bdd4-9e27dc544612	30.00	45.00	\N	t	f	2026-03-27 17:47:48.61568+05:30	2026-03-27 17:47:48.61568+05:30	\N	other	10	\N	f	\N	\N	\N	\N
bfd0c417-ae18-4d60-8206-631013b26580	234f9697-c95a-4356-91aa-b3c42a1d9a17	SMT Reflow Soldering	837e8921-ebb2-4adc-bdd4-9e27dc544612	20.00	25.00	\N	t	f	2026-03-27 17:47:48.653397+05:30	2026-03-27 17:47:48.653397+05:30	\N	other	10	\N	f	\N	\N	\N	\N
b29298fd-3d2e-4e27-ae46-b24bfce16138	234f9697-c95a-4356-91aa-b3c42a1d9a17	AOI Inspection	a19fc720-c92e-4579-bce9-10023767406c	10.00	15.00	\N	t	f	2026-03-27 17:47:48.683982+05:30	2026-03-27 17:47:48.683982+05:30	\N	other	10	\N	f	\N	\N	\N	\N
3f980b0d-3ec6-4b4f-b1f2-f9a30020bbe7	234f9697-c95a-4356-91aa-b3c42a1d9a17	Through-Hole Insertion	fdc841b4-d14a-4de2-acd7-4179b3c639eb	15.00	30.00	\N	t	f	2026-03-27 17:47:48.713883+05:30	2026-03-27 17:47:48.713883+05:30	\N	other	10	\N	f	\N	\N	\N	\N
81231838-7bb2-41bd-bb1d-bb09088659d5	234f9697-c95a-4356-91aa-b3c42a1d9a17	Wave Soldering	9a109e3b-fb5d-4b3b-bff3-24c728f8f467	20.00	20.00	\N	t	f	2026-03-27 17:47:48.738034+05:30	2026-03-27 17:47:48.738034+05:30	\N	other	10	\N	f	\N	\N	\N	\N
24e4554d-d19d-4b36-843d-982aa9e2942a	234f9697-c95a-4356-91aa-b3c42a1d9a17	Housing Assembly	0fa04225-e17e-4b7e-907f-ecc30b503d93	10.00	20.00	\N	t	f	2026-03-27 17:47:48.763217+05:30	2026-03-27 17:47:48.763217+05:30	\N	other	10	\N	f	\N	\N	\N	\N
4dc2fff2-8508-4f7a-8984-32a595188afd	234f9697-c95a-4356-91aa-b3c42a1d9a17	Functional Testing	f31f69c5-6701-4fb1-99c4-c256ecf9414e	5.00	30.00	\N	t	f	2026-03-27 17:47:48.788186+05:30	2026-03-27 17:47:48.788186+05:30	\N	other	10	\N	f	\N	\N	\N	\N
b6db2843-9164-45fe-9091-625370d5d173	234f9697-c95a-4356-91aa-b3c42a1d9a17	Quality Check	32b7bcdc-2431-4b32-85af-f0f04daf949f	5.00	15.00	\N	t	f	2026-03-27 17:47:48.812787+05:30	2026-03-27 17:47:48.812787+05:30	\N	other	10	\N	f	\N	\N	\N	\N
04884008-23b1-4172-864f-0b03cf232e66	234f9697-c95a-4356-91aa-b3c42a1d9a17	Final Packaging	01c0b5b4-91ef-4868-9972-cafa1a8145d4	5.00	10.00	\N	t	f	2026-03-27 17:47:48.834358+05:30	2026-03-27 17:47:48.834358+05:30	\N	other	10	\N	f	\N	\N	\N	\N
592e0c62-3a54-4a0d-aed0-3a54c941a006	234f9697-c95a-4356-91aa-b3c42a1d9a17	Firmware Flash	f31f69c5-6701-4fb1-99c4-c256ecf9414e	10.00	15.00	\N	t	f	2026-03-27 17:47:48.858083+05:30	2026-03-27 17:47:48.858083+05:30	\N	other	10	\N	f	\N	\N	\N	\N
f89e8583-fa04-44ce-9bfc-633d6e47e2dc	a12c668d-facf-4307-922f-0725d8578152	SMT Component Placement	79c07c21-4321-4250-8241-6e6b1acd7fd5	30.00	45.00	\N	t	f	2026-03-28 23:33:04.040294+05:30	2026-03-28 23:33:04.040294+05:30	\N	other	10	\N	f	\N	\N	\N	\N
1eccc5f9-a375-4497-a33f-3d2b00d44ecc	a12c668d-facf-4307-922f-0725d8578152	SMT Reflow Soldering	79c07c21-4321-4250-8241-6e6b1acd7fd5	20.00	25.00	\N	t	f	2026-03-28 23:33:04.085454+05:30	2026-03-28 23:33:04.085454+05:30	\N	other	10	\N	f	\N	\N	\N	\N
74566808-58fe-4c4f-abef-dda0f3235976	a12c668d-facf-4307-922f-0725d8578152	AOI Inspection	ac3e1ace-8a8a-4e10-a81c-a4c9e6511b10	10.00	15.00	\N	t	f	2026-03-28 23:33:04.100918+05:30	2026-03-28 23:33:04.100918+05:30	\N	other	10	\N	f	\N	\N	\N	\N
472ffd76-a2be-47d1-a32a-434bbca81c6e	a12c668d-facf-4307-922f-0725d8578152	Through-Hole Insertion	982b1983-e30f-4e2b-8b1a-d8d75f1aef7a	15.00	30.00	\N	t	f	2026-03-28 23:33:04.115633+05:30	2026-03-28 23:33:04.115633+05:30	\N	other	10	\N	f	\N	\N	\N	\N
45f23568-88cd-41c0-9b6f-aa37aca98543	a12c668d-facf-4307-922f-0725d8578152	Wave Soldering	adfc9a6a-642a-4d8c-a281-15726c51bcb7	20.00	20.00	\N	t	f	2026-03-28 23:33:04.131316+05:30	2026-03-28 23:33:04.131316+05:30	\N	other	10	\N	f	\N	\N	\N	\N
11c50b4f-ef31-49f2-a59d-36f16bc1ffda	a12c668d-facf-4307-922f-0725d8578152	Housing Assembly	4cca0316-5edb-4403-adf0-8250c1a243dc	10.00	20.00	\N	t	f	2026-03-28 23:33:04.152147+05:30	2026-03-28 23:33:04.152147+05:30	\N	other	10	\N	f	\N	\N	\N	\N
653f1f09-e1f7-471a-aff3-233bbefd60c0	a12c668d-facf-4307-922f-0725d8578152	Functional Testing	2e8ebd66-09a1-422e-a425-059405286479	5.00	30.00	\N	t	f	2026-03-28 23:33:04.170552+05:30	2026-03-28 23:33:04.170552+05:30	\N	other	10	\N	f	\N	\N	\N	\N
f598a206-9fb2-444b-9e0b-5594e5420005	a12c668d-facf-4307-922f-0725d8578152	Quality Check	7565ab64-4f61-4af1-aa48-5fdba324434e	5.00	15.00	\N	t	f	2026-03-28 23:33:04.191273+05:30	2026-03-28 23:33:04.191273+05:30	\N	other	10	\N	f	\N	\N	\N	\N
412b4e8c-e5b2-41e4-8c13-a32659de70fe	a12c668d-facf-4307-922f-0725d8578152	Final Packaging	40d2ea83-a8e6-4120-a087-6b6d103aecf9	5.00	10.00	\N	t	f	2026-03-28 23:33:04.211343+05:30	2026-03-28 23:33:04.211343+05:30	\N	other	10	\N	f	\N	\N	\N	\N
46fbdfd4-16d1-4230-8b37-2faeba80ecce	a12c668d-facf-4307-922f-0725d8578152	Firmware Flash	2e8ebd66-09a1-422e-a425-059405286479	10.00	15.00	\N	t	f	2026-03-28 23:33:04.226478+05:30	2026-03-28 23:33:04.226478+05:30	\N	other	10	\N	f	\N	\N	\N	\N
7f544476-bd23-428c-b13f-3ba57020b413	b5ef68c4-18be-4fa6-a439-a23c34877550	SMT Component Placement	2036eb5b-a347-40ae-a1b6-fdd013267e15	30.00	45.00	\N	t	f	2026-03-27 17:48:33.037933+05:30	2026-03-27 17:48:33.037933+05:30	\N	other	10	\N	f	\N	\N	\N	\N
45c2b0ec-2d02-4d17-8c66-15df383e3482	b5ef68c4-18be-4fa6-a439-a23c34877550	SMT Reflow Soldering	2036eb5b-a347-40ae-a1b6-fdd013267e15	20.00	25.00	\N	t	f	2026-03-27 17:48:33.076284+05:30	2026-03-27 17:48:33.076284+05:30	\N	other	10	\N	f	\N	\N	\N	\N
ea58f578-fd3d-48ee-815d-762088834e5a	b5ef68c4-18be-4fa6-a439-a23c34877550	AOI Inspection	de4fd658-8ae0-40ca-ad9a-e60f027b408a	10.00	15.00	\N	t	f	2026-03-27 17:48:33.10132+05:30	2026-03-27 17:48:33.10132+05:30	\N	other	10	\N	f	\N	\N	\N	\N
0c6bff48-6e6c-4a46-8163-6ca58c2cd7ba	b5ef68c4-18be-4fa6-a439-a23c34877550	Through-Hole Insertion	0828cb4a-1204-4a2f-a757-00cf27733277	15.00	30.00	\N	t	f	2026-03-27 17:48:33.125569+05:30	2026-03-27 17:48:33.125569+05:30	\N	other	10	\N	f	\N	\N	\N	\N
6aba7f08-a97c-4ccd-9311-0a9bd4477666	b5ef68c4-18be-4fa6-a439-a23c34877550	Wave Soldering	adb637d2-833a-42a7-85b5-1aee3ecf8e37	20.00	20.00	\N	t	f	2026-03-27 17:48:33.150299+05:30	2026-03-27 17:48:33.150299+05:30	\N	other	10	\N	f	\N	\N	\N	\N
a06904d1-7581-4b8f-b4b6-6b7309f94244	b5ef68c4-18be-4fa6-a439-a23c34877550	Housing Assembly	91636b98-95c2-4382-a605-4faf64a6bc91	10.00	20.00	\N	t	f	2026-03-27 17:48:33.174643+05:30	2026-03-27 17:48:33.174643+05:30	\N	other	10	\N	f	\N	\N	\N	\N
fb8accab-34e4-471a-a7a5-c0ebb90721e9	b5ef68c4-18be-4fa6-a439-a23c34877550	Functional Testing	6e51d092-4e87-4af3-bacd-6944d17feb16	5.00	30.00	\N	t	f	2026-03-27 17:48:33.198717+05:30	2026-03-27 17:48:33.198717+05:30	\N	other	10	\N	f	\N	\N	\N	\N
f4ff0abc-e270-468f-a1e2-6d77b95a3790	b5ef68c4-18be-4fa6-a439-a23c34877550	Quality Check	ab21d84a-7dbf-4bdd-82ec-dfcbe5e2e67e	5.00	15.00	\N	t	f	2026-03-27 17:48:33.230229+05:30	2026-03-27 17:48:33.230229+05:30	\N	other	10	\N	f	\N	\N	\N	\N
4f2a17d5-3891-4b81-aab5-ebfc7fd7bc19	b5ef68c4-18be-4fa6-a439-a23c34877550	Final Packaging	bc287060-c762-4d52-bdd6-971a5a57a3f2	5.00	10.00	\N	t	f	2026-03-27 17:48:33.253079+05:30	2026-03-27 17:48:33.253079+05:30	\N	other	10	\N	f	\N	\N	\N	\N
f36f41b3-7894-457b-b417-64c607ab0cfe	b5ef68c4-18be-4fa6-a439-a23c34877550	Firmware Flash	6e51d092-4e87-4af3-bacd-6944d17feb16	10.00	15.00	\N	t	f	2026-03-27 17:48:33.279061+05:30	2026-03-27 17:48:33.279061+05:30	\N	other	10	\N	f	\N	\N	\N	\N
e3d4e119-aba3-454a-b9c3-d55740369700	7fd84f4a-c061-4774-a95d-415c4e67b6b6	Arrange Raw Materials	85ebaa4f-7a17-49e5-a697-01401dccb8db	120.00	10.00	Arrange raw materials	t	f	2026-07-30 11:41:55.346051+05:30	2026-07-30 11:41:55.346097+05:30	ARM	other	10	\N	f	\N	\N	71677bc0-be81-4b5b-94e0-3ac4de233185	\N
ada5d5a6-a6b0-41a0-ae86-d51c5de5df53	1e26d822-336a-4caf-b726-d5bc873bcd47	operartion1	b5be9f76-5a08-4b2d-8463-c2b2b5362153	1.00	2.10	\N	t	f	2026-07-24 17:48:30.066373+05:30	2026-07-25 09:16:02.582111+05:30	OPERAR	other	10	\N	f	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	\N
74dfeac7-63dd-45e1-af00-d07dd74c0869	7fd84f4a-c061-4774-a95d-415c4e67b6b6	Assemble	85ebaa4f-7a17-49e5-a697-01401dccb8db	360.00	60.00	Assemble all items	t	f	2026-07-30 11:42:40.882652+05:30	2026-07-30 11:42:40.882668+05:30	ASSEMB	other	10	\N	f	\N	\N	71677bc0-be81-4b5b-94e0-3ac4de233185	\N
25d80b77-9769-453c-9c7f-65abca112e78	df413048-964e-45da-af55-91e90d7c54ee	Monthly Roti Plan	e69c6344-fe6e-4751-8314-5ca30f3ee966	1.00	1.00	\N	t	f	2026-08-16 14:15:41.698146+05:30	2026-08-16 14:15:41.698157+05:30	CUT	other	10	\N	f	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	\N
\.


--
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.password_reset_tokens (id, tenant_id, user_id, token_hash, expires_at, used_at, created_at) FROM stdin;
29d44de3-dfdd-440a-9ce3-6eb20d7c37a1	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	3359931f5dd521536c825d7c3eac591294338ea610382bc07c136a15b136d122	2026-08-24 00:50:21.518497+05:30	2026-08-23 23:50:53.555579+05:30	2026-08-23 23:50:21.522517+05:30
70792900-2f1d-4d8f-ab47-3a592c33f2d3	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	bec35829abba69243dc74252515a080f9b4f08f5b56cc6567984c98af6ae71eb	2026-09-14 18:44:00.808461+05:30	2026-09-14 17:44:20.305844+05:30	2026-09-14 17:44:00.818997+05:30
d1372115-1166-43e7-b803-5c311439565b	df413048-964e-45da-af55-91e90d7c54ee	2c743518-1f62-43be-80ed-c09988b3a0ec	176cea4f3785d99abac4783e98684f7a93fa603725e637b1c029dde4fc434fde	2026-09-23 22:10:20.093223+05:30	2026-09-23 21:10:33.435777+05:30	2026-09-23 21:10:20.100374+05:30
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payments (id, tenant_id, payment_number, invoice_id, client_id, amount, payment_date, payment_method, reference_number, notes, created_by, created_at) FROM stdin;
b142a464-d55d-48e0-b9b6-d321e0763b55	1e26d822-336a-4caf-b726-d5bc873bcd47	PAY-000001	1cc3df73-6266-4e93-b6e3-60755454f576	8566fc0d-5da9-4655-9342-1c1cf9b4f261	500.00	2026-07-25	BANK_TRANSFER	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:20:04.0881+05:30
8bcd307e-34d2-47bb-a1cb-0e67fdb5ae35	1e26d822-336a-4caf-b726-d5bc873bcd47	PAY-000002	03871f18-778b-4c1b-8ba4-0d2cf6fef04a	8566fc0d-5da9-4655-9342-1c1cf9b4f261	2500.00	2026-07-25	BANK_TRANSFER	\N	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-26 00:04:38.671572+05:30
82284836-2e58-403f-ac23-a6866e64db79	df413048-964e-45da-af55-91e90d7c54ee	PAY-000001	d94d0a9c-8975-4615-857f-0bd2137e61b3	63bd0ed6-7e32-4c12-a6d6-ea8eb901006b	10000.00	2026-08-16	CASH	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:56:45.793035+05:30
ae4af7ba-8919-4189-b98d-5ff7bbca7243	df413048-964e-45da-af55-91e90d7c54ee	PAY-000002	72e65e59-bd98-46c0-9c63-d103ea1e0989	63bd0ed6-7e32-4c12-a6d6-ea8eb901006b	10000.00	2026-08-16	CASH	\N	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 22:22:12.525119+05:30
\.


--
-- Data for Name: pick_list_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.pick_list_lines (id, pick_list_id, material_id, location_id, quantity, sequence, batch_id) FROM stdin;
\.


--
-- Data for Name: pick_lists; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.pick_lists (id, tenant_id, work_order_id, pick_list_number, warehouse_id, status, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: po_number_sequences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.po_number_sequences (tenant_id, current_value) FROM stdin;
1e26d822-336a-4caf-b726-d5bc873bcd47	4
df413048-964e-45da-af55-91e90d7c54ee	8
\.


--
-- Data for Name: product_images; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.product_images (id, tenant_id, template_id, variant_id, file_name, file_path, file_size, file_mime_type, image_order, is_primary, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: production_records; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.production_records (id, work_order_id, produced_quantity, scrap_quantity, recorded_by, notes, recorded_at) FROM stdin;
5e94312e-eacd-4b97-b6d7-29c6dffa69a3	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	1.000	0.000	69ebd965-54bc-4d0d-8231-db1f55e0cde4	Testing record production	2026-07-25 20:08:09.743674+05:30
d5a1dc6e-51f4-470e-baea-619f0ac5fcdb	88b79ec2-96c1-4242-a023-9889ea0d430b	5.000	0.000	69ebd965-54bc-4d0d-8231-db1f55e0cde4	\N	2026-07-25 23:56:27.17192+05:30
62a054bf-3f74-408b-922f-448f557f4ba6	6b2cc088-c47c-471d-9247-d33974e47a84	1.000	0.000	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	2026-08-16 20:04:44.913368+05:30
02945f64-7cff-41b5-9500-d4160d624e2e	66863c47-2254-44a6-b93e-6f9c7633c58b	1.000	0.000	2c743518-1f62-43be-80ed-c09988b3a0ec	\N	2026-08-16 22:10:35.461824+05:30
\.


--
-- Data for Name: purchase_order_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.purchase_order_lines (id, tenant_id, purchase_order_id, material_id, quantity, received_quantity, unit_price, line_total, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
830391b9-e210-4b48-94e1-83a06c757ee8	1e26d822-336a-4caf-b726-d5bc873bcd47	68d8baa0-90bc-4078-92f1-ec5d95ce6847	e2c1deee-51be-4698-8c4c-20aa0d7b027d	100.000	100.000	60.0000	6000.0000	f	\N	2026-07-26 00:30:26.095361+05:30	2026-07-26 00:31:01.677638+05:30
df3f24d9-cd00-4329-9411-f9ec451eedfc	1e26d822-336a-4caf-b726-d5bc873bcd47	5e8a2c69-5ef3-4e80-9a0e-9e4a37a277a8	a8b13e4d-51c9-4786-8cc4-a3197b305a27	10.000	0.000	10.0000	100.0000	f	\N	2026-07-29 00:16:38.808553+05:30	2026-07-29 00:16:38.808566+05:30
ec613c4b-6664-4389-a1b3-bd6375719f26	1e26d822-336a-4caf-b726-d5bc873bcd47	454ef4aa-8beb-4d73-b164-84f798730598	dd1b4662-08e8-4f92-8d58-35f3015f9ea5	1.000	0.000	10.0000	10.0000	f	\N	2026-07-29 00:23:26.134018+05:30	2026-07-29 00:23:26.13403+05:30
4700df5e-da34-4e97-b27f-e94112ec2183	df413048-964e-45da-af55-91e90d7c54ee	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	72723bde-d01b-4182-9517-bd64f80d3c5f	10.000	10.000	10.0000	100.0000	f	\N	2026-09-29 17:57:32.070411+05:30	2026-09-29 17:58:29.284244+05:30
5c156afe-f018-44a5-9322-e3cb6c7f0020	df413048-964e-45da-af55-91e90d7c54ee	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	55c87cf5-af2f-4204-a575-2a1e8523e075	10.000	10.000	4.0000	40.0000	f	\N	2026-09-29 17:58:07.580083+05:30	2026-09-29 18:27:49.774183+05:30
752cc22c-0088-484a-8e2c-2f79be19437c	df413048-964e-45da-af55-91e90d7c54ee	13ee59cc-e503-43d4-83dc-44eaa53b5172	55c87cf5-af2f-4204-a575-2a1e8523e075	10.000	10.000	100.0000	1000.0000	f	\N	2026-09-29 18:27:27.312487+05:30	2026-09-29 18:33:04.721548+05:30
305a2d19-ea88-4831-a4e9-ad2c614abd6a	df413048-964e-45da-af55-91e90d7c54ee	360f4ed6-0526-445c-abeb-250977dfe563	626920a3-a4e1-41ca-af9f-fb9e2631a46f	10.000	10.000	10.0000	100.0000	f	\N	2026-09-29 18:34:57.810846+05:30	2026-09-29 18:35:14.537656+05:30
\.


--
-- Data for Name: purchase_orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.purchase_orders (id, tenant_id, po_number, supplier_id, order_date, expected_delivery, status, total_amount, notes, created_by, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
68d8baa0-90bc-4078-92f1-ec5d95ce6847	1e26d822-336a-4caf-b726-d5bc873bcd47	PO-20260726-0001	1fbed590-c8a6-4215-86ee-7b6cb61629b3	2026-07-26	2026-07-26	received	6000.0000	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-26 00:30:26.073056+05:30	2026-07-26 00:31:01.6427+05:30
5e8a2c69-5ef3-4e80-9a0e-9e4a37a277a8	1e26d822-336a-4caf-b726-d5bc873bcd47	PO-20260729-0003	1fbed590-c8a6-4215-86ee-7b6cb61629b3	2026-07-29	2026-07-30	acknowledged	100.0000	test	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-29 00:16:38.7643+05:30	2026-07-29 00:20:25.838951+05:30
454ef4aa-8beb-4d73-b164-84f798730598	1e26d822-336a-4caf-b726-d5bc873bcd47	PO-20260729-0004	1fbed590-c8a6-4215-86ee-7b6cb61629b3	2026-07-29	\N	acknowledged	10.0000	\N	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-29 00:23:26.114625+05:30	2026-07-29 00:24:04.36027+05:30
8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	df413048-964e-45da-af55-91e90d7c54ee	PO-20260929-0001	96ad7e79-2424-4d35-8960-c471b942ff16	2026-09-29	2026-09-30	received	100.0000	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 17:57:31.947157+05:30	2026-09-29 17:58:29.219306+05:30
d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	df413048-964e-45da-af55-91e90d7c54ee	PO-20260929-0002	96ad7e79-2424-4d35-8960-c471b942ff16	2026-09-29	2026-09-30	received	40.0000	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 17:58:07.534023+05:30	2026-09-29 18:27:49.748613+05:30
13ee59cc-e503-43d4-83dc-44eaa53b5172	df413048-964e-45da-af55-91e90d7c54ee	PO-20260929-0004	96ad7e79-2424-4d35-8960-c471b942ff16	2026-09-29	2026-09-30	received	1000.0000	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:27:27.30367+05:30	2026-09-29 18:33:04.673464+05:30
360f4ed6-0526-445c-abeb-250977dfe563	df413048-964e-45da-af55-91e90d7c54ee	PO-20260929-0007	96ad7e79-2424-4d35-8960-c471b942ff16	2026-09-29	2026-09-30	received	100.0000	\N	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-09-29 18:34:57.784346+05:30	2026-09-29 18:35:14.51301+05:30
\.


--
-- Data for Name: purchase_requisitions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.purchase_requisitions (id, tenant_id, requisition_number, status, material_id, work_order_id, required_quantity, shortage_quantity, created_by, approved_by, linked_po_id, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: quality_inspections; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.quality_inspections (id, tenant_id, reference_type, reference_id, inspection_date, inspector_id, result, remarks, created_at) FROM stdin;
f7d58ab8-29f8-4186-9d45-0e0d8ebe257b	1e26d822-336a-4caf-b726-d5bc873bcd47	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	2026-07-25	69ebd965-54bc-4d0d-8231-db1f55e0cde4	pass	Automated test script approval	2026-07-25 21:52:14.49906+05:30
f9aed37d-2934-4e66-92c5-87472ab435e6	1e26d822-336a-4caf-b726-d5bc873bcd47	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	2026-07-25	69ebd965-54bc-4d0d-8231-db1f55e0cde4	pass	ok	2026-07-25 23:57:17.232802+05:30
166f619c-bb4d-47aa-9a72-3a6c46ff5713	df413048-964e-45da-af55-91e90d7c54ee	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	2026-08-16	2c743518-1f62-43be-80ed-c09988b3a0ec	pass	s	2026-08-16 20:49:04.737545+05:30
3c4f4602-9f54-40fb-b277-ad864f7d9869	df413048-964e-45da-af55-91e90d7c54ee	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	2026-08-16	2c743518-1f62-43be-80ed-c09988b3a0ec	pass	a	2026-08-16 22:11:03.59403+05:30
\.


--
-- Data for Name: quarantine_releases; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.quarantine_releases (id, tenant_id, ncr_id, released_by, released_at, new_location_id, reason) FROM stdin;
\.


--
-- Data for Name: report_executions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report_executions (id, tenant_id, report_id, executed_by, export_format, execution_time_ms, row_count, file_url, file_size_kb, status, error_message, created_at, is_deleted, deleted_at) FROM stdin;
\.


--
-- Data for Name: report_schedules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report_schedules (id, tenant_id, created_by, report_id, schedule_type, schedule_time, day_of_week, day_of_month, recipients, is_active, created_at, last_executed_at, is_deleted, deleted_at) FROM stdin;
\.


--
-- Data for Name: rfq_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rfq_lines (id, tenant_id, rfq_id, material_id, quantity, description, created_at) FROM stdin;
\.


--
-- Data for Name: rfq_number_sequences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rfq_number_sequences (tenant_id, current_value) FROM stdin;
\.


--
-- Data for Name: rfq_suppliers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rfq_suppliers (id, tenant_id, rfq_id, supplier_id, status, quotation_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: rfqs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rfqs (id, tenant_id, rfq_number, material_request_id, title, status, deadline, notes, awarded_supplier_id, awarded_po_id, created_by, is_deleted, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sales_clients; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sales_clients (id, tenant_id, code, name, email, phone, address, gst_number, credit_limit, credit_used, payment_terms_days, is_active, is_deleted, deleted_at, created_at, updated_at, default_price_list_id) FROM stdin;
8566fc0d-5da9-4655-9342-1c1cf9b4f261	1e26d822-336a-4caf-b726-d5bc873bcd47	CUST-000001	tanveer	tanveer@gmail.com	8169020290	tes		0.0000	3000.0000	1	t	f	\N	2026-07-25 17:19:12.128538+05:30	2026-07-25 23:45:20.488975+05:30	\N
7b7076a0-7341-4482-a3ac-01a80b276e83	7fd84f4a-c061-4774-a95d-415c4e67b6b6	CUST-000001	Ashar Enterprise	ashu@ashar.com	+919876123450	ro.no 18, 4 floor, building number 39, l.i.g colony kurla west		0.0000	0.0000	0	t	f	\N	2026-07-30 17:14:59.528582+05:30	2026-07-30 17:14:59.528598+05:30	\N
63bd0ed6-7e32-4c12-a6d6-ea8eb901006b	df413048-964e-45da-af55-91e90d7c54ee	None	test	test@gamil.com	1231231231	test	\N	0.0000	20000.0000	0	t	f	\N	2026-08-11 20:10:03.9011+05:30	2026-08-16 21:01:48.345731+05:30	\N
\.


--
-- Data for Name: sales_order_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sales_order_lines (id, sales_order_id, product_id, product_type, uom_id, quantity, unit_price, tax_rate, tax_amount, line_total, allocated_quantity, shipped_quantity, backorder_quantity, work_order_id, status, notes, created_at, updated_at, dispatched_quantity, line_status, shortfall_quantity, production_required) FROM stdin;
c7c8d198-17b8-4fac-9a7b-40ea353726e2	b0e1d83e-fd9b-4b77-b53c-04568725f32b	fb929cf7-6354-433e-b66f-d66fad60a0d5	variant	533498de-dc4d-4842-840c-43ddc8206c9a	1.0000	500.0000	0.00	0.0000	500.0000	1.0000	1.0000	1.0000	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	shipped	\N	2026-07-25 17:20:52.763319+05:30	2026-07-25 22:12:48.94599+05:30	1.0000	ALLOCATED	1.0000	t
cdab60e1-50bb-4870-93fd-80da6daf549b	d13e28dd-d1db-4710-a628-1cf7cfb3d596	fb929cf7-6354-433e-b66f-d66fad60a0d5	variant	533498de-dc4d-4842-840c-43ddc8206c9a	5.0000	500.0000	0.00	0.0000	2500.0000	5.0000	5.0000	5.0000	88b79ec2-96c1-4242-a023-9889ea0d430b	shipped	\N	2026-07-25 23:44:41.18245+05:30	2026-07-26 00:03:37.051576+05:30	5.0000	ALLOCATED	5.0000	t
33c5204f-d592-4f17-9f19-e8987fe60caf	cdea16ef-befb-4d97-a598-25fa710f6ce8	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	variant	18f11e18-dd91-45f5-8ac1-2340161e2a4e	1.0000	10000.0000	0.00	0.0000	10000.0000	1.0000	1.0000	1.0000	6b2cc088-c47c-471d-9247-d33974e47a84	shipped	\N	2026-08-16 20:02:04.608361+05:30	2026-08-16 20:53:42.66206+05:30	1.0000	ALLOCATED	1.0000	t
6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	bbe75209-17d6-4626-ad3e-df0bbdce24f9	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	variant	18f11e18-dd91-45f5-8ac1-2340161e2a4e	1.0000	10000.0000	0.00	0.0000	10000.0000	1.0000	1.0000	1.0000	66863c47-2254-44a6-b93e-6f9c7633c58b	shipped	\N	2026-08-16 21:01:27.155335+05:30	2026-08-16 22:11:36.2646+05:30	1.0000	ALLOCATED	1.0000	t
\.


--
-- Data for Name: sales_orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sales_orders (id, tenant_id, order_number, client_id, order_date, delivery_date, status, payment_status, subtotal, discount_amount, tax_amount, grand_total, notes, created_by, is_active, is_deleted, deleted_at, created_at, updated_at, approver_id, submitted_at, approved_at, rejected_at, approval_notes, estimated_completion_date, expected_dispatch_date, expected_delivery_date, confirmed_at, confirmed_by, ready_at, priority) FROM stdin;
d13e28dd-d1db-4710-a628-1cf7cfb3d596	1e26d822-336a-4caf-b726-d5bc873bcd47	SO-20260725-002	8566fc0d-5da9-4655-9342-1c1cf9b4f261	2026-07-25	2026-07-25	COMPLETED	PENDING	2500.0000	0.0000	0.0000	2500.0000		69ebd965-54bc-4d0d-8231-db1f55e0cde4	t	f	\N	2026-07-25 23:42:51.74625+05:30	2026-07-26 00:04:38.722342+05:30	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 23:45:01.685559+05:30	2026-07-25 23:45:20.418411+05:30	\N	\N	\N	\N	\N	\N	\N	\N	NORMAL
b0e1d83e-fd9b-4b77-b53c-04568725f32b	1e26d822-336a-4caf-b726-d5bc873bcd47	SO-20260725-001	8566fc0d-5da9-4655-9342-1c1cf9b4f261	2026-07-25	2026-07-31	COMPLETED	PENDING	500.0000	0.0000	0.0000	500.0000		69ebd965-54bc-4d0d-8231-db1f55e0cde4	t	f	\N	2026-07-25 17:20:30.457423+05:30	2026-07-29 22:13:47.790393+05:30	69ebd965-54bc-4d0d-8231-db1f55e0cde4	2026-07-25 17:36:17.317013+05:30	2026-07-25 17:40:04.989456+05:30	\N	\N	\N	\N	\N	\N	\N	\N	NORMAL
30ab12a2-301a-4c95-967a-df1b56b03526	7fd84f4a-c061-4774-a95d-415c4e67b6b6	SO-20260730-001	7b7076a0-7341-4482-a3ac-01a80b276e83	2026-07-30	2026-08-06	DRAFT	PENDING	0.0000	0.0000	0.0000	0.0000	100 thermometer	71677bc0-be81-4b5b-94e0-3ac4de233185	t	f	\N	2026-07-30 17:16:53.045342+05:30	2026-07-30 17:16:53.045361+05:30	71677bc0-be81-4b5b-94e0-3ac4de233185	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	NORMAL
cdea16ef-befb-4d97-a598-25fa710f6ce8	df413048-964e-45da-af55-91e90d7c54ee	SO-20260816-001	63bd0ed6-7e32-4c12-a6d6-ea8eb901006b	2026-08-16	2026-08-17	COMPLETED	PENDING	10000.0000	0.0000	0.0000	10000.0000		2c743518-1f62-43be-80ed-c09988b3a0ec	t	f	\N	2026-08-16 20:01:46.998022+05:30	2026-08-16 20:56:45.859997+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 20:02:09.894885+05:30	2026-08-16 20:02:24.579187+05:30	\N	\N	\N	\N	\N	\N	\N	\N	NORMAL
bbe75209-17d6-4626-ad3e-df0bbdce24f9	df413048-964e-45da-af55-91e90d7c54ee	SO-20260816-002	63bd0ed6-7e32-4c12-a6d6-ea8eb901006b	2026-08-16	2026-08-17	COMPLETED	PENDING	10000.0000	0.0000	0.0000	10000.0000		2c743518-1f62-43be-80ed-c09988b3a0ec	t	f	\N	2026-08-16 21:01:14.201171+05:30	2026-08-16 22:22:12.571032+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-08-16 21:01:31.861722+05:30	2026-08-16 21:01:48.294626+05:30	\N	\N	\N	\N	\N	\N	\N	\N	NORMAL
\.


--
-- Data for Name: sales_price_list_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sales_price_list_lines (id, price_list_id, product_id, product_type, unit_price, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sales_price_lists; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sales_price_lists (id, tenant_id, name, is_default, valid_from, valid_to, is_active, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
b42796ac-6c55-47e6-8d3a-b6d111513002	1e26d822-336a-4caf-b726-d5bc873bcd47	tanveer	f	2026-07-25	2026-07-25	t	f	\N	2026-07-25 17:26:51.999441+05:30	2026-07-25 17:26:51.999448+05:30
\.


--
-- Data for Name: saved_reports; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.saved_reports (id, tenant_id, created_by, name, description, report_type, query_config, is_public, created_at, updated_at, is_deleted, deleted_at) FROM stdin;
\.


--
-- Data for Name: serial_numbers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.serial_numbers (id, tenant_id, material_id, serial_number, status, current_location_id, reference_id, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: stock_ledger_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.stock_ledger_entries (id, tenant_id, material_id, location_id, transaction_date, transaction_type, quantity_change, running_balance, unit_cost, total_value, reference_type, reference_id, created_at) FROM stdin;
075512fe-a9f3-4c05-a87c-d1864c77b513	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	e9312a72-f06e-4e5e-b9d7-2973da769656	2026-07-25 19:05:20.448493+05:30	IN	100.000	100.000	\N	\N	manual	\N	2026-07-25 19:05:20.452445+05:30
c3b3accc-8814-4aca-a23c-296b9bc173da	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	\N	2026-07-25 19:42:26.925306+05:30	ISSUE	-2.000	98.000	\N	\N	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	2026-07-25 19:42:26.927297+05:30
437e6b9e-c115-45b2-93ab-485a7e294eec	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	\N	2026-07-25 20:08:09.925059+05:30	PRODUCTION_CONSUMPTION	-2.000	98.000	\N	\N	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	2026-07-25 20:08:09.927531+05:30
74da9e46-e90e-493f-8558-f6e181c00b22	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	732e6349-8c10-4a9b-ac52-19d1c83ea805	2026-07-25 21:52:14.512494+05:30	FG_RECEIPT	1.000	1.000	\N	\N	work_order	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	2026-07-25 21:52:14.531263+05:30
83ce52ec-4d73-4643-ac46-e7f9280c4700	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	\N	2026-07-25 22:12:48.945468+05:30	SALES_SHIPMENT	-1.000	0.000	\N	\N	sales_order_line	c7c8d198-17b8-4fac-9a7b-40ea353726e2	2026-07-25 22:12:48.956682+05:30
18f384e1-12ee-44ab-8171-449962febda5	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	\N	2026-07-25 23:46:19.292688+05:30	ISSUE	-10.000	88.000	\N	\N	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	2026-07-25 23:46:19.314416+05:30
45220577-c76a-4c2e-b685-6eceb16661f2	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	\N	2026-07-25 23:56:27.377893+05:30	PRODUCTION_CONSUMPTION	-10.000	88.000	\N	\N	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	2026-07-25 23:56:27.38139+05:30
fc1a6905-2de8-4848-8293-e5ace1b020e2	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	732e6349-8c10-4a9b-ac52-19d1c83ea805	2026-07-25 23:57:17.254457+05:30	FG_RECEIPT	5.000	5.000	\N	\N	work_order	88b79ec2-96c1-4242-a023-9889ea0d430b	2026-07-25 23:57:17.30471+05:30
54ff7012-ec77-4bf1-821b-9f7fdc1470ca	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	\N	2026-07-26 00:03:37.051257+05:30	SALES_SHIPMENT	-5.000	0.000	\N	\N	sales_order_line	cdab60e1-50bb-4870-93fd-80da6daf549b	2026-07-26 00:03:37.058142+05:30
0819bdef-9d9b-4ebd-9379-8c7c5c2953f4	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	732e6349-8c10-4a9b-ac52-19d1c83ea805	2026-07-26 00:31:01.613575+05:30	RECEIPT	100.000	188.000	\N	\N	purchase_order	68d8baa0-90bc-4078-92f1-ec5d95ce6847	2026-07-26 00:31:01.648787+05:30
7b8c6cad-bb8d-4d03-a56b-4167ecef1d33	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	2026-08-16 20:04:09.835624+05:30	MATERIAL_ISSUE	-1.000	0.000	\N	\N	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	2026-08-16 20:04:09.859141+05:30
d6bd3270-06c8-4e6f-8ec7-1d9207b62168	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	2026-08-16 20:04:45.000948+05:30	PRODUCTION_CONSUMPTION	-1.000	0.000	\N	\N	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	2026-08-16 20:04:45.002573+05:30
fb06415f-1505-45a0-89b4-54125f66829e	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	a7054e96-1ae5-4800-b414-d556c437b796	2026-08-16 20:49:04.771606+05:30	FG_RECEIPT	1.000	1.000	\N	\N	work_order	6b2cc088-c47c-471d-9247-d33974e47a84	2026-08-16 20:49:04.825214+05:30
08da3883-121c-4f74-a23b-15f916910d98	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	\N	2026-08-16 20:53:42.661593+05:30	DISPATCH	-1.000	0.000	\N	\N	sales_order_line	33c5204f-d592-4f17-9f19-e8987fe60caf	2026-08-16 20:53:42.673683+05:30
2fda9cff-8868-4d0b-8935-2a85b33c913a	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	2026-08-16 21:11:13.315515+05:30	MATERIAL_ISSUE	-1.000	0.000	\N	\N	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	2026-08-16 21:11:13.331307+05:30
8511215a-16e8-4372-8e6d-c6f96124ea94	df413048-964e-45da-af55-91e90d7c54ee	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	\N	2026-08-16 22:10:35.591508+05:30	PRODUCTION_CONSUMPTION	-1.000	0.000	\N	\N	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	2026-08-16 22:10:35.5979+05:30
b25084df-c5ed-4bed-be71-8c4923fe3a59	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	a7054e96-1ae5-4800-b414-d556c437b796	2026-08-16 22:11:03.611297+05:30	FG_RECEIPT	1.000	1.000	\N	\N	work_order	66863c47-2254-44a6-b93e-6f9c7633c58b	2026-08-16 22:11:03.668695+05:30
6546ab72-945f-4851-8e16-a809878606df	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	\N	2026-08-16 22:11:36.264332+05:30	DISPATCH	-1.000	0.000	\N	\N	sales_order_line	6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	2026-08-16 22:11:36.269086+05:30
fa2e0f09-b903-46ca-9e1b-01aec9d83a5b	df413048-964e-45da-af55-91e90d7c54ee	72723bde-d01b-4182-9517-bd64f80d3c5f	a7054e96-1ae5-4800-b414-d556c437b796	2026-09-29 17:58:29.17873+05:30	PURCHASE_RECEIPT	10.000	10.000	\N	\N	purchase_order	8876707a-a8a8-43b0-bbc9-ffc5b4d37a10	2026-09-29 17:58:29.224504+05:30
c9c34ab5-f0a9-4993-a106-2cb3073ac37d	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	a7054e96-1ae5-4800-b414-d556c437b796	2026-09-29 18:27:49.726467+05:30	PURCHASE_RECEIPT	10.000	10.000	\N	\N	purchase_order	d960f23e-c7ec-4cd3-95ec-88b01e3f4bab	2026-09-29 18:27:49.750627+05:30
0ee07629-c9f2-4fe9-ac6e-75d9f182be5f	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	a7054e96-1ae5-4800-b414-d556c437b796	2026-09-29 18:33:04.644029+05:30	PURCHASE_RECEIPT	10.000	20.000	\N	\N	purchase_order	13ee59cc-e503-43d4-83dc-44eaa53b5172	2026-09-29 18:33:04.680309+05:30
b7b0811b-0b91-4b49-b2b8-de45c5862119	df413048-964e-45da-af55-91e90d7c54ee	626920a3-a4e1-41ca-af9f-fb9e2631a46f	a7054e96-1ae5-4800-b414-d556c437b796	2026-09-29 18:35:14.497155+05:30	PURCHASE_RECEIPT	10.000	10.000	\N	\N	purchase_order	360f4ed6-0526-445c-abeb-250977dfe563	2026-09-29 18:35:14.514772+05:30
\.


--
-- Data for Name: stock_levels; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.stock_levels (id, tenant_id, material_id, location_id, stock_status, quantity, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
264ff44e-2805-4cfc-bb30-47596bdc18ab	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	a7054e96-1ae5-4800-b414-d556c437b796	available	17.0000	f	\N	2026-09-29 18:27:49.703326+05:30	2026-10-01 13:51:05.174075+05:30
97693499-17ef-492f-94ab-640b9e5f5337	df413048-964e-45da-af55-91e90d7c54ee	626920a3-a4e1-41ca-af9f-fb9e2631a46f	a7054e96-1ae5-4800-b414-d556c437b796	available	7.0000	f	\N	2026-09-29 18:35:14.474883+05:30	2026-10-01 13:51:21.179297+05:30
c0fa6adb-8283-4dd2-96ec-f215d754ce20	df413048-964e-45da-af55-91e90d7c54ee	72723bde-d01b-4182-9517-bd64f80d3c5f	a7054e96-1ae5-4800-b414-d556c437b796	available	7.0000	f	\N	2026-09-29 17:58:29.146144+05:30	2026-10-01 13:51:36.085125+05:30
1cb99ee7-0f72-475e-a3ea-c51f7de011f7	df413048-964e-45da-af55-91e90d7c54ee	b2876e59-29fe-4c9b-86a6-be45d3a6c479	a7054e96-1ae5-4800-b414-d556c437b796	available	3.0000	f	\N	2026-09-29 19:30:36.574467+05:30	2026-10-01 13:54:15.354283+05:30
39e64584-c6dc-4158-87eb-af480dcb9d97	df413048-964e-45da-af55-91e90d7c54ee	55c87cf5-af2f-4204-a575-2a1e8523e075	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	available	1.0000	f	\N	2026-09-29 18:34:25.227813+05:30	2026-10-01 13:54:15.443463+05:30
68dfe5eb-2a8e-47ef-8f68-016d02888d1b	df413048-964e-45da-af55-91e90d7c54ee	626920a3-a4e1-41ca-af9f-fb9e2631a46f	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	available	1.0000	f	\N	2026-09-29 18:35:30.184259+05:30	2026-10-01 13:54:15.477415+05:30
083d390b-e312-4b82-b96d-5488ab54f127	df413048-964e-45da-af55-91e90d7c54ee	72723bde-d01b-4182-9517-bd64f80d3c5f	b28a8a9b-08ab-470f-b6b2-6e43b1aad297	available	1.0000	f	\N	2026-09-29 18:25:32.387515+05:30	2026-10-01 13:54:15.500673+05:30
df216855-9908-4aed-8dc4-ee983a1e0f94	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	e9312a72-f06e-4e5e-b9d7-2973da769656	available	88.0000	f	\N	2026-07-25 19:05:20.430984+05:30	2026-07-25 23:46:19.280585+05:30
9a175ead-9e75-4d7d-82c9-754c3003bde7	1e26d822-336a-4caf-b726-d5bc873bcd47	0104ddea-8623-463e-aa8c-000a8ce0b8f9	732e6349-8c10-4a9b-ac52-19d1c83ea805	available	0.0000	f	\N	2026-07-25 21:52:14.502587+05:30	2026-07-26 00:03:37.042808+05:30
92b37627-030f-47f4-b1aa-7babf659f04a	1e26d822-336a-4caf-b726-d5bc873bcd47	e2c1deee-51be-4698-8c4c-20aa0d7b027d	732e6349-8c10-4a9b-ac52-19d1c83ea805	available	100.0000	f	\N	2026-07-26 00:31:01.586121+05:30	2026-07-26 00:31:01.598253+05:30
87dab45d-1f93-4a6e-8adc-1e4384b36fcc	df413048-964e-45da-af55-91e90d7c54ee	1c172b0b-ce97-415b-89aa-96c489f24560	a7054e96-1ae5-4800-b414-d556c437b796	available	0.0000	f	\N	2026-08-16 20:49:04.746551+05:30	2026-08-16 22:11:36.256792+05:30
\.


--
-- Data for Name: stock_reservations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.stock_reservations (id, tenant_id, material_id, location_id, quantity, status, reference_type, reference_id, notes, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: subcontract_material_issues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.subcontract_material_issues (id, tenant_id, subcontract_order_id, material_id, quantity, batch_number, issued_at, batch_id, returned_quantity, from_location_id, issued_by) FROM stdin;
d83bcac7-fdd2-4500-9548-f8a0b01c7777	df413048-964e-45da-af55-91e90d7c54ee	4412fe8e-b123-4b2f-a766-b2d15db2c89e	72723bde-d01b-4182-9517-bd64f80d3c5f	1.000	\N	2026-09-29 18:25:32.424973+05:30	\N	0.000	a7054e96-1ae5-4800-b414-d556c437b796	2c743518-1f62-43be-80ed-c09988b3a0ec
4e36ab2c-2a33-4fb5-84b3-7ac20811fb19	df413048-964e-45da-af55-91e90d7c54ee	4412fe8e-b123-4b2f-a766-b2d15db2c89e	55c87cf5-af2f-4204-a575-2a1e8523e075	1.000	\N	2026-09-29 18:34:25.272879+05:30	\N	0.000	a7054e96-1ae5-4800-b414-d556c437b796	2c743518-1f62-43be-80ed-c09988b3a0ec
cdce91fd-3f92-467b-a635-756423dcbc29	df413048-964e-45da-af55-91e90d7c54ee	4412fe8e-b123-4b2f-a766-b2d15db2c89e	626920a3-a4e1-41ca-af9f-fb9e2631a46f	1.000	\N	2026-09-29 18:35:30.209228+05:30	\N	0.000	a7054e96-1ae5-4800-b414-d556c437b796	2c743518-1f62-43be-80ed-c09988b3a0ec
70fd9fec-55af-43a4-8704-6d7201129fda	df413048-964e-45da-af55-91e90d7c54ee	4798a3c4-8865-47af-9fc4-539f4742c39d	55c87cf5-af2f-4204-a575-2a1e8523e075	2.000	\N	2026-10-01 13:51:05.430569+05:30	\N	0.000	a7054e96-1ae5-4800-b414-d556c437b796	2c743518-1f62-43be-80ed-c09988b3a0ec
3728d1e9-c672-4fcb-9865-e8a41f52aafb	df413048-964e-45da-af55-91e90d7c54ee	4798a3c4-8865-47af-9fc4-539f4742c39d	626920a3-a4e1-41ca-af9f-fb9e2631a46f	2.000	\N	2026-10-01 13:51:21.217546+05:30	\N	0.000	a7054e96-1ae5-4800-b414-d556c437b796	2c743518-1f62-43be-80ed-c09988b3a0ec
f1cba9b9-9db5-4436-b89d-7c074aa3b878	df413048-964e-45da-af55-91e90d7c54ee	4798a3c4-8865-47af-9fc4-539f4742c39d	72723bde-d01b-4182-9517-bd64f80d3c5f	2.000	\N	2026-10-01 13:51:36.138204+05:30	\N	0.000	a7054e96-1ae5-4800-b414-d556c437b796	2c743518-1f62-43be-80ed-c09988b3a0ec
\.


--
-- Data for Name: subcontract_number_sequences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.subcontract_number_sequences (tenant_id, current_value) FROM stdin;
df413048-964e-45da-af55-91e90d7c54ee	2
\.


--
-- Data for Name: subcontract_order_lines; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.subcontract_order_lines (id, tenant_id, subcontract_order_id, material_id, required_quantity, issued_quantity, returned_quantity, created_at, consumed_quantity) FROM stdin;
778c7371-a39e-44fd-b5fd-726868b5ff39	df413048-964e-45da-af55-91e90d7c54ee	4412fe8e-b123-4b2f-a766-b2d15db2c89e	72723bde-d01b-4182-9517-bd64f80d3c5f	1.000	1.000	0.000	2026-09-29 16:34:54.387803+05:30	0.000
1c8d4d08-ccab-4762-8d23-8326da347d90	df413048-964e-45da-af55-91e90d7c54ee	4412fe8e-b123-4b2f-a766-b2d15db2c89e	55c87cf5-af2f-4204-a575-2a1e8523e075	1.000	1.000	0.000	2026-09-29 16:34:54.387778+05:30	0.000
cfcd7739-d0f3-47eb-9a46-031626163fe8	df413048-964e-45da-af55-91e90d7c54ee	4412fe8e-b123-4b2f-a766-b2d15db2c89e	626920a3-a4e1-41ca-af9f-fb9e2631a46f	1.000	1.000	0.000	2026-09-29 16:34:54.387798+05:30	0.000
f2afc107-cdad-419c-9ea7-4933b2012f6b	df413048-964e-45da-af55-91e90d7c54ee	4798a3c4-8865-47af-9fc4-539f4742c39d	55c87cf5-af2f-4204-a575-2a1e8523e075	2.000	2.000	0.000	2026-10-01 13:48:00.830474+05:30	2.000
10af281f-06c7-4c9e-83a4-d8da2b58931d	df413048-964e-45da-af55-91e90d7c54ee	4798a3c4-8865-47af-9fc4-539f4742c39d	626920a3-a4e1-41ca-af9f-fb9e2631a46f	2.000	2.000	0.000	2026-10-01 13:48:00.830485+05:30	2.000
4d6ecda7-24af-4ea4-bcee-a8b94662ae6a	df413048-964e-45da-af55-91e90d7c54ee	4798a3c4-8865-47af-9fc4-539f4742c39d	72723bde-d01b-4182-9517-bd64f80d3c5f	2.000	2.000	0.000	2026-10-01 13:48:00.830489+05:30	2.000
\.


--
-- Data for Name: subcontract_orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.subcontract_orders (id, tenant_id, order_number, supplier_id, product_id, product_type, quantity, status, is_deleted, deleted_at, created_at, updated_at, bom_id, due_date, notes, output_batch_id, received_quantity, created_by, approved_by, approved_at) FROM stdin;
4412fe8e-b123-4b2f-a766-b2d15db2c89e	df413048-964e-45da-af55-91e90d7c54ee	SCO-20260929-0001	96ad7e79-2424-4d35-8960-c471b942ff16	b2876e59-29fe-4c9b-86a6-be45d3a6c479	variant	1.000	completed	f	\N	2026-09-29 14:46:34.377212+05:30	2026-09-29 19:30:36.687906+05:30	999899db-aaa8-4e02-aefd-475295a9c64b	\N	\N	70f2f536-55ca-4d7b-a039-fa6945235031	1.000	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-09-29 16:34:53.866828+05:30
4798a3c4-8865-47af-9fc4-539f4742c39d	df413048-964e-45da-af55-91e90d7c54ee	SCO-20261001-0002	96ad7e79-2424-4d35-8960-c471b942ff16	b2876e59-29fe-4c9b-86a6-be45d3a6c479	variant	2.000	completed	f	\N	2026-10-01 13:47:40.522789+05:30	2026-10-01 13:54:15.516215+05:30	999899db-aaa8-4e02-aefd-475295a9c64b	2026-10-07	\N	0ff6d195-7859-49fb-904f-836b878de529	2.000	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec	2026-10-01 13:48:00.810848+05:30
\.


--
-- Data for Name: supplier_invoices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.supplier_invoices (id, tenant_id, invoice_number, supplier_invoice_ref, purchase_order_id, supplier_id, supplier_name, status, invoice_date, due_date, subtotal, tax_amount, grand_total, paid_amount, notes, created_by, is_deleted, deleted_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: supplier_payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.supplier_payments (id, tenant_id, payment_number, supplier_invoice_id, supplier_id, amount, payment_date, payment_method, reference_number, notes, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: supplier_price_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.supplier_price_history (id, tenant_id, supplier_id, material_id, unit_price, effective_from, effective_to, created_at) FROM stdin;
e51d6289-2f6d-4056-9cc8-f05e1a973542	1e26d822-336a-4caf-b726-d5bc873bcd47	1fbed590-c8a6-4215-86ee-7b6cb61629b3	e2c1deee-51be-4698-8c4c-20aa0d7b027d	60.0000	2026-07-26	\N	2026-07-26 00:31:01.633441+05:30
e4fb7666-6fad-4616-845d-c178208ad7ea	df413048-964e-45da-af55-91e90d7c54ee	96ad7e79-2424-4d35-8960-c471b942ff16	72723bde-d01b-4182-9517-bd64f80d3c5f	10.0000	2026-09-29	\N	2026-09-29 17:58:29.197113+05:30
cefbb172-8fc3-45d3-a866-99d138094f5d	df413048-964e-45da-af55-91e90d7c54ee	96ad7e79-2424-4d35-8960-c471b942ff16	55c87cf5-af2f-4204-a575-2a1e8523e075	4.0000	2026-09-29	\N	2026-09-29 18:27:49.741997+05:30
ea9cd969-3394-44c2-97cd-a2776b760134	df413048-964e-45da-af55-91e90d7c54ee	96ad7e79-2424-4d35-8960-c471b942ff16	55c87cf5-af2f-4204-a575-2a1e8523e075	100.0000	2026-09-29	\N	2026-09-29 18:33:04.661927+05:30
03a67435-7b49-4ba5-8852-98d3bc5903e3	df413048-964e-45da-af55-91e90d7c54ee	96ad7e79-2424-4d35-8960-c471b942ff16	626920a3-a4e1-41ca-af9f-fb9e2631a46f	10.0000	2026-09-29	\N	2026-09-29 18:35:14.506187+05:30
\.


--
-- Data for Name: supplier_quotations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.supplier_quotations (id, tenant_id, supplier_id, purchase_order_id, material_id, quantity, unit_price, valid_until, status, is_deleted, deleted_at, created_at, updated_at, rfq_id, quotation_number) FROM stdin;
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.suppliers (id, tenant_id, code, name, contact_person, email, phone, address, gst, payment_terms, performance_rating, is_active, is_deleted, deleted_at, created_at, updated_at, created_by, updated_by) FROM stdin;
1fbed590-c8a6-4215-86ee-7b6cb61629b3	1e26d822-336a-4caf-b726-d5bc873bcd47	SUP-000001	supplier1	Anjum	rotihai.mumbai@gmail.com	9876543214	ro.no 18, 4 floor, building number 39, l.i.g colony kurla west	\N	\N	\N	t	f	\N	2026-07-26 00:26:34.507424+05:30	2026-07-26 00:26:34.507434+05:30	69ebd965-54bc-4d0d-8231-db1f55e0cde4	69ebd965-54bc-4d0d-8231-db1f55e0cde4
96ad7e79-2424-4d35-8960-c471b942ff16	df413048-964e-45da-af55-91e90d7c54ee	SUP-000001	test1	test1	test1@gmail.com	9878987868	kurla	\N	\N	\N	t	f	\N	2026-08-16 13:54:56.712053+05:30	2026-08-16 13:54:56.712062+05:30	2c743518-1f62-43be-80ed-c09988b3a0ec	2c743518-1f62-43be-80ed-c09988b3a0ec
\.


--
-- Data for Name: technical_documents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.technical_documents (id, tenant_id, document_number, name, document_category, is_active, created_at, updated_at) FROM stdin;
3f79bde3-7063-469e-97ff-ee3bc820a7df	df413048-964e-45da-af55-91e90d7c54ee	DOC-1790180535050	Tanveer_Sayyed_Executive_CV_Final_Reviewed.pdf	Attachment	t	2026-09-23 21:52:15.45919+05:30	2026-09-23 21:52:15.459198+05:30
ace3aa15-2518-40a3-b96d-9318bc587288	df413048-964e-45da-af55-91e90d7c54ee	DOC-1790348859440	WO-WO-20260913-0004	Drawing	t	2026-09-25 20:37:39.65505+05:30	2026-09-25 20:37:39.655061+05:30
c4ac909a-718a-4e3b-a33b-636c2c1e4679	df413048-964e-45da-af55-91e90d7c54ee	DOC-1790421654124	WhatsApp Image 2026-09-24 at 9.42.04 PM (1)	Drawing	t	2026-09-26 16:50:54.300235+05:30	2026-09-26 16:50:54.300244+05:30
\.


--
-- Data for Name: tenant_audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenant_audit_logs (id, tenant_id, action, reason, acted_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tenant_finance_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenant_finance_settings (id, tenant_id, invoice_prefix, supplier_invoice_prefix, payment_prefix, supplier_payment_prefix, invoice_template, default_tax_rate, default_payment_terms_days, gst_number, logo_url, custom_template, ar_account_code, bank_account_code, ap_account_code, revenue_account_code, expense_account_code, created_at, updated_at) FROM stdin;
df230a17-fc81-401a-ad29-5f7edef5a105	1e26d822-336a-4caf-b726-d5bc873bcd47	INV	SINV	PAY	SPAY	standard	0.00	30	\N	\N	{}	1100	1000	2000	4000	5000	2026-07-25 23:09:03.141749+05:30	2026-07-25 23:09:03.141752+05:30
07b86ff2-0521-4a43-b592-366ad974a2de	df413048-964e-45da-af55-91e90d7c54ee	INV	SINV	PAY	SPAY	standard	0.00	30	\N	\N	{}	1100	1000	2000	4000	5000	2026-08-16 20:54:00.50945+05:30	2026-08-16 20:54:00.509458+05:30
\.


--
-- Data for Name: tenant_role_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenant_role_permissions (id, role_id, permission, created_at) FROM stdin;
9350d36b-c048-4cf5-984b-ea940256b700	860e0b86-e2a9-470f-987b-ae2ab53869c7	*	2026-07-25 19:14:16.116887+05:30
1ecd3034-351b-4e7a-8b9b-8594f78fa16f	e4713c0e-a734-4df0-bd30-25c8d0b1190f	*	2026-07-25 19:14:16.16315+05:30
373488bd-bb3e-4ae9-a7de-d4ca86fb4967	02f3edff-454f-4eea-9bb6-205dd0cb0f56	inventory:write	2026-07-25 19:14:16.214494+05:30
c606a202-2be1-4f2c-abdd-d8830541d3c6	02f3edff-454f-4eea-9bb6-205dd0cb0f56	procurement:write	2026-07-25 19:14:16.214501+05:30
83f28dac-8fa8-4083-9a61-2a6a74d9f09d	02f3edff-454f-4eea-9bb6-205dd0cb0f56	admin:read	2026-07-25 19:14:16.214523+05:30
38db6c2a-7490-4ab6-8649-ab12eb7cd6d2	02f3edff-454f-4eea-9bb6-205dd0cb0f56	report.view_financial	2026-07-25 19:14:16.214525+05:30
0efbd449-4e12-4db1-bc1b-95c7425051bf	02f3edff-454f-4eea-9bb6-205dd0cb0f56	supplier_payment.record	2026-07-25 19:14:16.214526+05:30
da54a6c8-42a4-491e-b2cc-b132fc482c77	02f3edff-454f-4eea-9bb6-205dd0cb0f56	manufacturing:write	2026-07-25 19:14:16.214527+05:30
595bc936-1aab-4625-90c2-60831f54af58	02f3edff-454f-4eea-9bb6-205dd0cb0f56	reports:read	2026-07-25 19:14:16.214529+05:30
fdd18440-a63d-421b-9253-620afafc8901	02f3edff-454f-4eea-9bb6-205dd0cb0f56	ledger.view	2026-07-25 19:14:16.21453+05:30
e1e83c4c-e0b2-47f2-a890-55b55f0a00fd	02f3edff-454f-4eea-9bb6-205dd0cb0f56	worker:read	2026-07-25 19:14:16.214532+05:30
e906cfcf-b814-4b34-bc61-44d9bf066b11	02f3edff-454f-4eea-9bb6-205dd0cb0f56	supplier_invoice.view	2026-07-25 19:14:16.214534+05:30
7eb0d829-a04f-4d47-b139-dceddbba5def	02f3edff-454f-4eea-9bb6-205dd0cb0f56	sales:approve_order	2026-07-25 19:14:16.214535+05:30
95671ecc-12fa-4823-8744-20b86c9822af	02f3edff-454f-4eea-9bb6-205dd0cb0f56	manufacturing:read	2026-07-25 19:14:16.214536+05:30
b6989e9b-003b-4baf-a372-b41c61379eef	02f3edff-454f-4eea-9bb6-205dd0cb0f56	tenant:read	2026-07-25 19:14:16.214538+05:30
c1f9dd42-9392-4129-8c4c-38d93afca52f	02f3edff-454f-4eea-9bb6-205dd0cb0f56	finance:read	2026-07-25 19:14:16.214539+05:30
65ee3a40-c6ba-469e-9ff4-f2a22ac9c291	02f3edff-454f-4eea-9bb6-205dd0cb0f56	payment.record	2026-07-25 19:14:16.21454+05:30
3398a585-82eb-428a-bd24-6e96c6578936	02f3edff-454f-4eea-9bb6-205dd0cb0f56	invoice.view	2026-07-25 19:14:16.214541+05:30
ebb3c643-0eec-47a4-a01d-31a11c848f67	02f3edff-454f-4eea-9bb6-205dd0cb0f56	procurement:read	2026-07-25 19:14:16.214543+05:30
4338830b-4be5-44bf-a9ac-144891a4726b	02f3edff-454f-4eea-9bb6-205dd0cb0f56	storekeeper:read	2026-07-25 19:14:16.214544+05:30
fbb82e9b-7875-46e5-802e-2eaea477361d	02f3edff-454f-4eea-9bb6-205dd0cb0f56	invoice.approve	2026-07-25 19:14:16.214556+05:30
49f3c639-1ccc-414b-ad98-c6ffca138a3f	02f3edff-454f-4eea-9bb6-205dd0cb0f56	sales:read	2026-07-25 19:14:16.214559+05:30
7ffca668-9df4-44c2-8e2c-ebde5816dabf	02f3edff-454f-4eea-9bb6-205dd0cb0f56	finance_settings.view	2026-07-25 19:14:16.214612+05:30
ae5bebf8-ea34-4f5b-9d25-e6057921be2f	02f3edff-454f-4eea-9bb6-205dd0cb0f56	rbac:read	2026-07-25 19:14:16.214656+05:30
36c83dbc-6f93-43d3-97bc-eead7f6eda99	02f3edff-454f-4eea-9bb6-205dd0cb0f56	sales:write	2026-07-25 19:14:16.214658+05:30
38dbefa9-4823-4646-9a7d-051411e6c5ac	02f3edff-454f-4eea-9bb6-205dd0cb0f56	user:read	2026-07-25 19:14:16.21466+05:30
ba454826-f0f3-44c2-b4ce-14a9041c052e	02f3edff-454f-4eea-9bb6-205dd0cb0f56	quality:write	2026-07-25 19:14:16.214662+05:30
ae659ff6-58ea-43af-acd1-537fad1ed20b	02f3edff-454f-4eea-9bb6-205dd0cb0f56	sales:view_orders	2026-07-25 19:14:16.214663+05:30
15ff556d-0a69-4ff9-8ce2-dfa444153bb3	02f3edff-454f-4eea-9bb6-205dd0cb0f56	inventory:read	2026-07-25 19:14:16.214664+05:30
e1540519-28b5-4884-9551-21c949bc2b8b	02f3edff-454f-4eea-9bb6-205dd0cb0f56	invoice.create	2026-07-25 19:14:16.214666+05:30
1ac92ea2-ea9c-44c2-bc6b-c15113ecc673	02f3edff-454f-4eea-9bb6-205dd0cb0f56	quality:read	2026-07-25 19:14:16.214667+05:30
24f8a3a0-5193-40be-9bc7-9a756caf89d1	02f3edff-454f-4eea-9bb6-205dd0cb0f56	sales:create_order	2026-07-25 19:14:16.214668+05:30
a8a5ee34-a91c-4e34-adb8-edf4156debb2	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	inventory:write	2026-07-25 19:14:16.22778+05:30
bdf5024d-2978-4cb2-b004-9b5b99052f95	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	procurement:write	2026-07-25 19:14:16.227784+05:30
0939fafb-1ae1-4796-99d6-b748f8a6080c	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	procurement:read	2026-07-25 19:14:16.227785+05:30
515a2c1a-839c-45ec-8f58-fd74c955541e	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	manufacturing:read	2026-07-25 19:14:16.227786+05:30
f79dc158-f8db-4af7-9210-ab3d6263afb5	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	storekeeper:read	2026-07-25 19:14:16.227787+05:30
922d39e0-1285-4533-a894-0a7ca40b01ba	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	manufacturing:write	2026-07-25 19:14:16.227789+05:30
9e7a436d-cd0f-45af-a3e9-9779af56fdd3	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	inventory:read	2026-07-25 19:14:16.22779+05:30
bf6dcbb3-2ee6-45d2-9a9b-7057169a68a9	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	quality:write	2026-07-25 19:14:16.227791+05:30
bf78f8db-1764-478a-98d4-22594abbcbc3	cc0dcdef-a6a0-4f88-9288-fb22c46231f8	quality:read	2026-07-25 19:14:16.227792+05:30
c1b5b639-294f-4825-a3e1-b1bb97bf048e	b8b4f8aa-3055-418b-868b-14dcab660388	inventory:write	2026-07-25 19:14:16.234479+05:30
875bc953-0679-4b75-9f00-9775a02e88d7	b8b4f8aa-3055-418b-868b-14dcab660388	procurement:write	2026-07-25 19:14:16.234491+05:30
5bd80dd8-5742-4d05-a635-f56f761cc73e	b8b4f8aa-3055-418b-868b-14dcab660388	procurement:read	2026-07-25 19:14:16.234495+05:30
57816387-e8ae-432f-9ba6-493e1b855d6a	b8b4f8aa-3055-418b-868b-14dcab660388	manufacturing:read	2026-07-25 19:14:16.234499+05:30
f5e6780f-ef4e-430f-a9e4-f6b106e71ee5	b8b4f8aa-3055-418b-868b-14dcab660388	storekeeper:read	2026-07-25 19:14:16.234502+05:30
7242f645-268b-4db1-b99f-aaa47d98dab8	b8b4f8aa-3055-418b-868b-14dcab660388	manufacturing:write	2026-07-25 19:14:16.234505+05:30
22a2d458-635e-4c4c-9cf2-d59683873303	b8b4f8aa-3055-418b-868b-14dcab660388	inventory:read	2026-07-25 19:14:16.234508+05:30
c3b961cd-93f9-4820-aa3d-3e053accd3ca	b8b4f8aa-3055-418b-868b-14dcab660388	quality:write	2026-07-25 19:14:16.234511+05:30
e1fd60c4-8645-48ed-8d4f-f7df2a02cc8c	b8b4f8aa-3055-418b-868b-14dcab660388	quality:read	2026-07-25 19:14:16.234514+05:30
25385b90-54db-44d7-a0c0-f540e20291fb	81f65b36-3188-4a59-a5e9-9ce4266d77fa	procurement:write	2026-07-25 19:14:16.240453+05:30
35d5f86c-f71c-47f4-bc02-efb3e990d814	81f65b36-3188-4a59-a5e9-9ce4266d77fa	procurement:read	2026-07-25 19:14:16.24046+05:30
2bbe6f8f-e596-4b73-91c7-c8129d0c33e6	81f65b36-3188-4a59-a5e9-9ce4266d77fa	storekeeper:read	2026-07-25 19:14:16.240462+05:30
481acf91-80cc-4543-9c4a-d3b4d8f5ea9d	81f65b36-3188-4a59-a5e9-9ce4266d77fa	manufacturing:write	2026-07-25 19:14:16.240464+05:30
fb3e4ee4-d38e-4f39-b3d6-76497197e1f5	81f65b36-3188-4a59-a5e9-9ce4266d77fa	reports:read	2026-07-25 19:14:16.240466+05:30
74808634-fb43-4e65-8666-3c6c28c8c17a	81f65b36-3188-4a59-a5e9-9ce4266d77fa	inventory:read	2026-07-25 19:14:16.240467+05:30
763b85d1-b68b-4f13-9488-817b70119b91	81f65b36-3188-4a59-a5e9-9ce4266d77fa	quality:read	2026-07-25 19:14:16.240469+05:30
7b1147c4-e3f5-4eeb-97d9-b30c114e385f	81f65b36-3188-4a59-a5e9-9ce4266d77fa	manufacturing:read	2026-07-25 19:14:16.240472+05:30
4eaa6079-da51-4c66-9683-d8c72bcbd7cc	510e460a-fdaa-4d8c-94dc-d411fb9ae0cd	quality:write	2026-07-25 19:14:16.245983+05:30
fdd4b243-2548-4453-850a-748f96889998	510e460a-fdaa-4d8c-94dc-d411fb9ae0cd	quality:read	2026-07-25 19:14:16.245994+05:30
fda514d8-9d70-481b-8b96-c0e781adfdad	510e460a-fdaa-4d8c-94dc-d411fb9ae0cd	inventory:read	2026-07-25 19:14:16.245998+05:30
36128bd1-1e3d-4ce5-b217-ba7b8ce7b55d	510e460a-fdaa-4d8c-94dc-d411fb9ae0cd	procurement:read	2026-07-25 19:14:16.246001+05:30
3555726b-2dd5-457f-b8eb-9e23f4c5ac7a	41b8b307-0c79-41c2-9c3a-e85d550695d2	invoice.view	2026-07-25 19:14:16.248684+05:30
474dd0f1-53ec-4903-8c42-7fd51ce803e4	41b8b307-0c79-41c2-9c3a-e85d550695d2	sales:read	2026-07-25 19:14:16.248687+05:30
5fabd688-e3e2-47c6-95da-317e41aef2fd	41b8b307-0c79-41c2-9c3a-e85d550695d2	reports:read	2026-07-25 19:14:16.248688+05:30
177d7992-9a5d-46e0-a293-bca6700b415d	41b8b307-0c79-41c2-9c3a-e85d550695d2	sales:view_orders	2026-07-25 19:14:16.248689+05:30
8471b7bb-a16a-4a32-9725-169e6ceaa92e	41b8b307-0c79-41c2-9c3a-e85d550695d2	sales:write	2026-07-25 19:14:16.24869+05:30
42bdebbe-f86c-4aff-a4b4-f2ed22683781	41b8b307-0c79-41c2-9c3a-e85d550695d2	inventory:read	2026-07-25 19:14:16.248691+05:30
68e7da6f-195a-41dc-8843-4d58eeb180c4	41b8b307-0c79-41c2-9c3a-e85d550695d2	invoice.create	2026-07-25 19:14:16.248691+05:30
a55084f3-a727-414d-8b08-fa1022153866	41b8b307-0c79-41c2-9c3a-e85d550695d2	manufacturing:read	2026-07-25 19:14:16.248692+05:30
06f2adbc-9b25-4920-a4e4-25f579b846c5	41b8b307-0c79-41c2-9c3a-e85d550695d2	sales:create_order	2026-07-25 19:14:16.248693+05:30
6bb608a7-8a1d-4a97-981b-935ce06182f6	8c26ad6f-dd49-4b71-837b-d5f03e39b192	payment.record	2026-07-25 19:14:16.252459+05:30
20d2e38f-322c-4520-9d73-1b4688317954	8c26ad6f-dd49-4b71-837b-d5f03e39b192	invoice.view	2026-07-25 19:14:16.252467+05:30
e5a0d289-f396-4609-99f7-ecf0378db139	8c26ad6f-dd49-4b71-837b-d5f03e39b192	invoice.approve	2026-07-25 19:14:16.252469+05:30
00b58476-ee22-438f-99f1-611be4d37f91	8c26ad6f-dd49-4b71-837b-d5f03e39b192	report.view_financial	2026-07-25 19:14:16.252471+05:30
854a9b15-4b1b-4e27-80a8-179625dbb99f	8c26ad6f-dd49-4b71-837b-d5f03e39b192	supplier_invoice.create	2026-07-25 19:14:16.252473+05:30
bd86eae7-3e74-43c3-84f8-1389713916bc	8c26ad6f-dd49-4b71-837b-d5f03e39b192	supplier_payment.record	2026-07-25 19:14:16.252474+05:30
052d7d3e-f996-4e2d-ae12-3b6d66e0237f	8c26ad6f-dd49-4b71-837b-d5f03e39b192	finance_settings.view	2026-07-25 19:14:16.252476+05:30
1406fc97-adbf-436e-a646-dc867203b559	8c26ad6f-dd49-4b71-837b-d5f03e39b192	reports:read	2026-07-25 19:14:16.252478+05:30
26e0adbb-a44e-4bac-9f97-3cedc7f9f9fe	8c26ad6f-dd49-4b71-837b-d5f03e39b192	finance:write	2026-07-25 19:14:16.252479+05:30
c0e12f62-1122-4c68-a09e-b8a814b8543d	8c26ad6f-dd49-4b71-837b-d5f03e39b192	supplier_invoice.view	2026-07-25 19:14:16.252481+05:30
220cd015-2529-467a-b9a5-1b6c78242334	8c26ad6f-dd49-4b71-837b-d5f03e39b192	finance_settings.write	2026-07-25 19:14:16.252482+05:30
37c974a1-867c-44c2-b547-769f99d308a9	8c26ad6f-dd49-4b71-837b-d5f03e39b192	invoice.create	2026-07-25 19:14:16.252484+05:30
ec621db0-bb49-4d0a-b19b-402dc9b82b91	8c26ad6f-dd49-4b71-837b-d5f03e39b192	ledger.view	2026-07-25 19:14:16.252485+05:30
a5671216-e52e-47bb-829a-ada48cedba19	8c26ad6f-dd49-4b71-837b-d5f03e39b192	finance:read	2026-07-25 19:14:16.252487+05:30
d8965f0f-56d5-4044-84d6-f08fe0ce6060	6047d624-6b36-4c24-8839-bb5a2bf14746	worker:read	2026-07-25 19:14:16.257944+05:30
f6a31d5e-84b1-4d99-8173-7f6cd2457edb	6047d624-6b36-4c24-8839-bb5a2bf14746	manufacturing:read	2026-07-25 19:14:16.257954+05:30
5bf3e514-c5b8-417d-ada7-5165f7228977	6047d624-6b36-4c24-8839-bb5a2bf14746	inventory:read	2026-07-25 19:14:16.257958+05:30
bc13ea0e-7ac3-4709-8c50-42ee4cb2abc6	6047d624-6b36-4c24-8839-bb5a2bf14746	manufacturing:write	2026-07-25 19:14:16.257961+05:30
7f1f2e9d-1849-45c7-a8e4-3850ac7aa03b	948e9704-3bc4-4dbc-b56d-04894ecc11e0	sales:view_orders	2026-07-25 19:14:16.264139+05:30
6e0e5d9d-cd8f-4ff9-a687-fb3c7539c088	948e9704-3bc4-4dbc-b56d-04894ecc11e0	client:read	2026-07-25 19:14:16.264143+05:30
9bae661c-5f22-4d67-85c6-7f89028a6bc8	948e9704-3bc4-4dbc-b56d-04894ecc11e0	inventory:read	2026-07-25 19:14:16.264144+05:30
336ad4b3-f403-400e-9a02-3ee85af30169	948e9704-3bc4-4dbc-b56d-04894ecc11e0	invoice.view	2026-07-25 19:14:16.264145+05:30
33f77c0b-3391-411f-9a9f-12e7f9a535aa	948e9704-3bc4-4dbc-b56d-04894ecc11e0	sales:read	2026-07-25 19:14:16.264146+05:30
6b610988-1792-4e2b-843e-b54f82fc391e	948e9704-3bc4-4dbc-b56d-04894ecc11e0	sales:create_order	2026-07-25 19:14:16.264147+05:30
032c8f8c-e51b-48e4-ab32-00897351e9d1	e86dce63-4066-4120-9b1a-1fbc0abc2e52	supplier:write	2026-07-25 19:14:16.271304+05:30
638eaaf1-0ed5-4088-b3cc-40b7be4c04d4	e86dce63-4066-4120-9b1a-1fbc0abc2e52	supplier:read	2026-07-25 19:14:16.271308+05:30
d1e0d9a4-0a34-49a5-bf4e-ee57608af2cf	e86dce63-4066-4120-9b1a-1fbc0abc2e52	procurement:write	2026-07-25 19:14:16.271309+05:30
3dd31369-567b-4e13-9534-9d749f0b5ef0	e86dce63-4066-4120-9b1a-1fbc0abc2e52	supplier_invoice.view	2026-07-25 19:14:16.27131+05:30
97b6e19f-f560-4439-9b4b-a366982a20ac	e86dce63-4066-4120-9b1a-1fbc0abc2e52	procurement:read	2026-07-25 19:14:16.271311+05:30
48ae0901-626a-447e-a490-d01f1848ae74	e86dce63-4066-4120-9b1a-1fbc0abc2e52	supplier_invoice.create	2026-07-25 19:14:16.271311+05:30
edbcef70-9559-4479-acda-07aa153f102e	2e59d634-964a-42db-ba90-5df9c9b84b0e	quality:read	2026-07-25 19:14:16.273477+05:30
e0b4e228-e224-43e6-bafe-5ee5050d302d	2e59d634-964a-42db-ba90-5df9c9b84b0e	inventory:read	2026-07-25 19:14:16.273481+05:30
54ded07f-c2ad-4907-b68c-4564f7a788c9	2e59d634-964a-42db-ba90-5df9c9b84b0e	procurement:read	2026-07-25 19:14:16.273482+05:30
c0b2c9fa-4570-4708-8feb-91e6bf85be87	2e59d634-964a-42db-ba90-5df9c9b84b0e	manufacturing:read	2026-07-25 19:14:16.273482+05:30
26eb1e2f-3c8a-4533-90cc-c767887feee9	2e59d634-964a-42db-ba90-5df9c9b84b0e	sales:read	2026-07-25 19:14:16.273483+05:30
b911bc7d-f5e0-4f20-8f62-c54032f5bc6e	2e59d634-964a-42db-ba90-5df9c9b84b0e	finance:read	2026-07-25 19:14:16.273484+05:30
b154bf03-3918-4f40-8b1f-9a2c91c415ae	2e59d634-964a-42db-ba90-5df9c9b84b0e	reports:read	2026-07-25 19:14:16.273485+05:30
f4869f5d-dede-4732-b845-5bff1fc48f76	876be0ef-2074-4ddb-93d3-26169ca12e12	*	2026-08-16 19:41:57.267017+05:30
0c6fed51-2450-4eb4-94ae-b3d73cde94b7	1972fc1b-9d6a-4680-b581-b280b444eb45	*	2026-08-16 19:41:57.289093+05:30
bb1c76c6-c053-4a30-9008-6ae98ad34a43	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	sales:write	2026-08-16 19:41:57.307777+05:30
51c63a69-50cf-46f7-92d2-487f4d11d65c	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	inventory:read	2026-08-16 19:41:57.307787+05:30
a4add695-ebbd-49e5-90b4-fb474e7702d4	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	inventory:write	2026-08-16 19:41:57.30779+05:30
3ec98e40-bbc1-4860-a682-350b42302e1f	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	report.view_financial	2026-08-16 19:41:57.307792+05:30
2b995ced-53d1-4de9-8b5b-c56150a461bb	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	admin:read	2026-08-16 19:41:57.307794+05:30
3c3daa9b-2dbd-46db-80f9-a8271c3c431a	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	ledger.view	2026-08-16 19:41:57.307796+05:30
8a915270-0a09-4b84-bae0-393461581353	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	supplier_invoice.view	2026-08-16 19:41:57.307797+05:30
3cff75c8-ff54-4881-98c1-565578500f2e	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	finance:read	2026-08-16 19:41:57.307799+05:30
41b5d824-cd45-40e2-9b86-d460280436e6	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	payment.record	2026-08-16 19:41:57.307801+05:30
ee4b98fd-4a0f-4ec3-a440-0d20bd184733	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	sales:create_order	2026-08-16 19:41:57.307803+05:30
9e1cb8cb-516d-4447-9cfa-42b4f2f85368	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	invoice.create	2026-08-16 19:41:57.307804+05:30
ee99c9ee-ca5e-4c3c-85c5-0c80ff19807d	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	supplier_payment.record	2026-08-16 19:41:57.307805+05:30
1bd10a22-ddea-4a17-9963-654a229c8266	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	invoice.approve	2026-08-16 19:41:57.307807+05:30
be12e3b3-7339-4716-a3b9-1acce8043acc	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	procurement:write	2026-08-16 19:41:57.307809+05:30
7f6aa041-a00a-4d89-98ab-e8f9a5e3c73e	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	procurement:read	2026-08-16 19:41:57.30781+05:30
cdf6fe9b-0e8d-4da7-850a-c99515bfa846	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	sales:view_orders	2026-08-16 19:41:57.307812+05:30
0873d82a-0eb3-4209-a822-754d1fa9f8c3	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	invoice.view	2026-08-16 19:41:57.307813+05:30
7d7777c5-1cb9-4aad-9387-b3e0185ee73f	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	rbac:read	2026-08-16 19:41:57.307815+05:30
103f8e8a-0c34-4a56-9fc3-8b62638a301a	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	storekeeper:read	2026-08-16 19:41:57.307816+05:30
fbb38148-cd22-4fe1-b83a-9650193f4d8d	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	tenant:read	2026-08-16 19:41:57.307818+05:30
5a1f3c3e-600d-4810-8f18-843755bde5d2	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	reports:read	2026-08-16 19:41:57.30782+05:30
f3096d46-cc5f-4916-9fc6-3df3af2872aa	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	manufacturing:write	2026-08-16 19:41:57.307821+05:30
b89445b8-2ecc-4e00-a1ec-14f7871c6b5e	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	finance_settings.view	2026-08-16 19:41:57.307823+05:30
3829f8e2-f58d-43fa-b017-30448d00ae94	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	worker:read	2026-08-16 19:41:57.307824+05:30
f31ada06-c911-4255-a405-08ae4fcc425f	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	quality:write	2026-08-16 19:41:57.307826+05:30
97922745-e0ed-4c32-ac92-100cc90a30db	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	user:read	2026-08-16 19:41:57.307827+05:30
d816a304-46be-494d-97fd-54659e3b4e69	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	sales:approve_order	2026-08-16 19:41:57.307829+05:30
5114433f-1309-4f91-97fd-8b3f9dbfd669	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	manufacturing:read	2026-08-16 19:41:57.30783+05:30
ea4f4e4e-f5db-4f75-83d3-c9085df1ce4f	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	quality:read	2026-08-16 19:41:57.307832+05:30
3e6a344e-0183-4821-8263-dfce5f2815f5	ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	sales:read	2026-08-16 19:41:57.307833+05:30
c1389e4b-62e2-4fe2-8e49-2c6c48b3fc85	d9b239bd-c808-471d-92c2-c236baa2fd35	inventory:read	2026-08-16 19:41:57.331719+05:30
4d15654d-7173-494d-9f10-bd614ca8a3b1	d9b239bd-c808-471d-92c2-c236baa2fd35	inventory:write	2026-08-16 19:41:57.331727+05:30
8467e3ff-4a6a-4fca-a4b6-176efd64e14b	d9b239bd-c808-471d-92c2-c236baa2fd35	storekeeper:read	2026-08-16 19:41:57.331729+05:30
6e1ac3dc-fdcd-4f72-b4e2-d5cff9044b9e	d9b239bd-c808-471d-92c2-c236baa2fd35	manufacturing:write	2026-08-16 19:41:57.331731+05:30
99fb63e4-6394-4a19-a718-a22983d7c833	d9b239bd-c808-471d-92c2-c236baa2fd35	quality:write	2026-08-16 19:41:57.331733+05:30
9b8b6289-84a5-4c4e-9091-dedc8028a8e5	d9b239bd-c808-471d-92c2-c236baa2fd35	manufacturing:read	2026-08-16 19:41:57.331734+05:30
5552d66c-b166-4bcc-9fc5-487df5f162f8	d9b239bd-c808-471d-92c2-c236baa2fd35	quality:read	2026-08-16 19:41:57.331736+05:30
02eb224c-50c8-4c2c-918b-d3df47321f6d	d9b239bd-c808-471d-92c2-c236baa2fd35	procurement:write	2026-08-16 19:41:57.331738+05:30
d0837a88-ae87-477f-af2e-9440809f57ae	d9b239bd-c808-471d-92c2-c236baa2fd35	procurement:read	2026-08-16 19:41:57.33174+05:30
3a368cc6-dc33-4323-9aa4-cdfd7296de3c	e843ac0f-852c-4e60-9a4f-091869b790f3	inventory:read	2026-08-16 19:41:57.340463+05:30
1f8af9e7-bc5f-4ab9-96a5-cd08cc247e63	e843ac0f-852c-4e60-9a4f-091869b790f3	inventory:write	2026-08-16 19:41:57.34047+05:30
e0717bb1-3641-498c-b99f-23c4f37bfec7	e843ac0f-852c-4e60-9a4f-091869b790f3	storekeeper:read	2026-08-16 19:41:57.340472+05:30
7cdef4f6-97c9-415a-9e61-bddfeb4913ac	e843ac0f-852c-4e60-9a4f-091869b790f3	manufacturing:write	2026-08-16 19:41:57.340474+05:30
e3e64c12-7530-4346-97ba-d49e7e40f73c	e843ac0f-852c-4e60-9a4f-091869b790f3	quality:write	2026-08-16 19:41:57.340475+05:30
c39147fe-43e6-4495-9d0c-f63fde9df30f	e843ac0f-852c-4e60-9a4f-091869b790f3	manufacturing:read	2026-08-16 19:41:57.340477+05:30
95f65f0d-7168-4179-9f12-16abfd009651	e843ac0f-852c-4e60-9a4f-091869b790f3	quality:read	2026-08-16 19:41:57.34048+05:30
0f5b2226-673d-4247-ad10-3ee9422bcf4e	e843ac0f-852c-4e60-9a4f-091869b790f3	procurement:write	2026-08-16 19:41:57.340481+05:30
14a4b153-66cc-42f7-afc9-8e2d5b0d67e9	e843ac0f-852c-4e60-9a4f-091869b790f3	procurement:read	2026-08-16 19:41:57.340483+05:30
8b82c53e-1a8a-43f8-b502-fc69f39e1f70	6ec6fd1d-deac-4b13-926b-4180fedf5a31	inventory:read	2026-08-16 19:41:57.346489+05:30
95a3394a-d15f-4942-b9a8-9584db95acc5	6ec6fd1d-deac-4b13-926b-4180fedf5a31	storekeeper:read	2026-08-16 19:41:57.346497+05:30
aa676f3d-e474-41bc-858a-734e3db49394	6ec6fd1d-deac-4b13-926b-4180fedf5a31	reports:read	2026-08-16 19:41:57.3465+05:30
05abff8f-1490-44c9-9a72-ec87902c2337	6ec6fd1d-deac-4b13-926b-4180fedf5a31	manufacturing:write	2026-08-16 19:41:57.346502+05:30
4728a192-1367-41a2-bf84-da0db88281ad	6ec6fd1d-deac-4b13-926b-4180fedf5a31	manufacturing:read	2026-08-16 19:41:57.346503+05:30
dcf1e04e-ae47-4536-a87b-3ac9a652b376	6ec6fd1d-deac-4b13-926b-4180fedf5a31	quality:read	2026-08-16 19:41:57.346505+05:30
80126cee-1c30-4381-9cc0-82ee032bc7fa	6ec6fd1d-deac-4b13-926b-4180fedf5a31	procurement:write	2026-08-16 19:41:57.346506+05:30
9a58fb15-8b6f-4dc8-af13-ee9124472aaa	6ec6fd1d-deac-4b13-926b-4180fedf5a31	procurement:read	2026-08-16 19:41:57.346508+05:30
195c4d41-a71c-46a6-8e86-b35486ee8579	c12c9e92-43b1-436a-9f62-c5dbaf5531d8	inventory:read	2026-08-16 19:41:57.350428+05:30
20bbfdd7-6f91-447e-ac92-6f6efaefeb8f	c12c9e92-43b1-436a-9f62-c5dbaf5531d8	quality:write	2026-08-16 19:41:57.350434+05:30
16ccb328-a067-41d3-9243-7eb4b2d7cae2	c12c9e92-43b1-436a-9f62-c5dbaf5531d8	procurement:read	2026-08-16 19:41:57.350436+05:30
194c2314-0375-4f84-81aa-a6db0fb22d85	c12c9e92-43b1-436a-9f62-c5dbaf5531d8	quality:read	2026-08-16 19:41:57.350438+05:30
6098ec34-7237-4fca-9034-9df3b0e78615	6cedfd2f-1159-404a-855f-1f68f2b97ad1	inventory:read	2026-08-16 19:41:57.354455+05:30
d51b712a-dc63-4064-884d-ce9780fa2c3d	6cedfd2f-1159-404a-855f-1f68f2b97ad1	sales:write	2026-08-16 19:41:57.354462+05:30
9518d1ab-a61c-417e-a53a-c48b6b995cf0	6cedfd2f-1159-404a-855f-1f68f2b97ad1	sales:view_orders	2026-08-16 19:41:57.354465+05:30
49ae1310-8115-4b33-8f19-f29fa10ba456	6cedfd2f-1159-404a-855f-1f68f2b97ad1	invoice.view	2026-08-16 19:41:57.354467+05:30
db980c72-7343-4bdf-99fe-194e3cfcf4ef	6cedfd2f-1159-404a-855f-1f68f2b97ad1	reports:read	2026-08-16 19:41:57.354469+05:30
dbc3be7f-29d6-480a-9581-2daf249fb970	6cedfd2f-1159-404a-855f-1f68f2b97ad1	sales:create_order	2026-08-16 19:41:57.35447+05:30
2a957055-9400-4f87-8baa-af0653dfe7f7	6cedfd2f-1159-404a-855f-1f68f2b97ad1	invoice.create	2026-08-16 19:41:57.354472+05:30
cd19b4b5-e018-45ce-b48a-d2b09bd72bed	6cedfd2f-1159-404a-855f-1f68f2b97ad1	manufacturing:read	2026-08-16 19:41:57.354473+05:30
f07fc2e7-1792-4960-85fd-07d111ab7074	6cedfd2f-1159-404a-855f-1f68f2b97ad1	sales:read	2026-08-16 19:41:57.354475+05:30
ee5ea6e1-ad15-4a3f-a0ca-685454ba12ad	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	invoice.view	2026-08-16 19:41:57.360974+05:30
2de490bc-7202-4cbb-8c84-dab22f45e095	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	supplier_invoice.create	2026-08-16 19:41:57.360977+05:30
400abdfe-8541-47d7-9eef-f5bd1c923035	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	report.view_financial	2026-08-16 19:41:57.360979+05:30
8891f079-64a9-4ca5-86c7-8d52b5cf8482	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	ledger.view	2026-08-16 19:41:57.36098+05:30
5227b11d-385e-41b6-9ca4-08f56ca43c1c	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	reports:read	2026-08-16 19:41:57.360981+05:30
ac9a16e5-5f78-475e-85c9-765391d8fa9b	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	supplier_invoice.view	2026-08-16 19:41:57.360982+05:30
4792f89d-f906-4437-82ac-85aa2795d758	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	finance_settings.view	2026-08-16 19:41:57.360983+05:30
c567d915-8a6d-4bc3-95b3-d475add31a2f	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	finance:write	2026-08-16 19:41:57.360984+05:30
1bcfaeea-8c78-4705-bb8f-8c02f939073b	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	finance:read	2026-08-16 19:41:57.360984+05:30
c00d48f2-6142-4ee2-ae4b-4363e8daac8f	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	invoice.create	2026-08-16 19:41:57.360985+05:30
ae50c992-8f85-428a-9b87-377b3f3086e5	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	payment.record	2026-08-16 19:41:57.360986+05:30
bbbae8f9-162c-4076-8350-06c14f3fae4a	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	supplier_payment.record	2026-08-16 19:41:57.360987+05:30
36052d42-cccb-40d9-9517-711dcd66a74e	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	finance_settings.write	2026-08-16 19:41:57.360988+05:30
85e6012d-a0fa-44dd-a0b8-c2eb07e05091	ba29d145-d858-4b78-9e41-7fe0bebfd3ac	invoice.approve	2026-08-16 19:41:57.360989+05:30
6e65f799-c209-482a-8d80-ec3da36d0336	77c8d5a0-9427-4b67-90d7-42bd85df7086	inventory:read	2026-08-16 19:41:57.36687+05:30
c30364e7-9feb-4063-b7d0-9985f41f035d	77c8d5a0-9427-4b67-90d7-42bd85df7086	worker:read	2026-08-16 19:41:57.366875+05:30
7b2148d3-90be-4f7b-ab84-116867ffcac2	77c8d5a0-9427-4b67-90d7-42bd85df7086	manufacturing:read	2026-08-16 19:41:57.366877+05:30
d4d66c4f-c9f6-4747-a45c-d03d917f5f6f	77c8d5a0-9427-4b67-90d7-42bd85df7086	manufacturing:write	2026-08-16 19:41:57.366878+05:30
3bd81b2d-132d-402a-9b23-d00000e0660c	79cab7d3-5eeb-4151-96fc-93c98ded0912	inventory:read	2026-08-16 19:41:57.369588+05:30
17dc063b-602f-4cba-a156-698ea9593cb5	79cab7d3-5eeb-4151-96fc-93c98ded0912	sales:view_orders	2026-08-16 19:41:57.369595+05:30
271a1593-1e64-4938-ab29-d12d30a3674c	79cab7d3-5eeb-4151-96fc-93c98ded0912	invoice.view	2026-08-16 19:41:57.369597+05:30
b96d7a92-1f37-4dd9-8258-293c5a85a607	79cab7d3-5eeb-4151-96fc-93c98ded0912	sales:create_order	2026-08-16 19:41:57.369599+05:30
ceacccf0-80dc-45c6-99d2-35bd326354da	79cab7d3-5eeb-4151-96fc-93c98ded0912	sales:read	2026-08-16 19:41:57.3696+05:30
d5841822-337d-41ed-903d-2b2c941a3cd4	79cab7d3-5eeb-4151-96fc-93c98ded0912	client:read	2026-08-16 19:41:57.369602+05:30
c5c961b7-9d04-421f-9b52-40fc2efe4af2	a1271188-885d-49fc-9920-ece472e74523	supplier_invoice.create	2026-08-16 19:41:57.373116+05:30
1846082c-86be-4ba8-ae9a-c2c2b612cb01	a1271188-885d-49fc-9920-ece472e74523	supplier:read	2026-08-16 19:41:57.373122+05:30
7108a371-efee-4dc8-ae37-e3cb6262cc5e	a1271188-885d-49fc-9920-ece472e74523	supplier:write	2026-08-16 19:41:57.373124+05:30
4956d700-b455-4319-9e73-fb7919c8d22e	a1271188-885d-49fc-9920-ece472e74523	procurement:write	2026-08-16 19:41:57.373125+05:30
cb4e6b2d-ec24-47a0-bb44-d4584e23867c	a1271188-885d-49fc-9920-ece472e74523	supplier_invoice.view	2026-08-16 19:41:57.373127+05:30
1dc06d1a-2f24-45a7-b48d-118352da042b	a1271188-885d-49fc-9920-ece472e74523	procurement:read	2026-08-16 19:41:57.373128+05:30
062f68ba-66c7-49d0-a816-da0dc34724fe	e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	inventory:read	2026-08-16 19:41:57.375846+05:30
4db431d4-f2bc-4986-bdb7-4768fdeee9fd	e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	finance:read	2026-08-16 19:41:57.375852+05:30
73c829fd-f245-4080-815e-f35bb7f00f10	e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	manufacturing:read	2026-08-16 19:41:57.375854+05:30
38151801-e4a2-412f-9fce-f5fa38938c4a	e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	quality:read	2026-08-16 19:41:57.375856+05:30
8afe5ef2-7050-4807-9dae-da7155d6007d	e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	sales:read	2026-08-16 19:41:57.375858+05:30
0a4527d0-722e-4dde-bf60-2d35ecdf95b0	e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	reports:read	2026-08-16 19:41:57.37586+05:30
421daad3-bff1-4fe9-9534-1d0dbf5c2822	e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	procurement:read	2026-08-16 19:41:57.375861+05:30
\.


--
-- Data for Name: tenant_roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenant_roles (id, tenant_id, name, label, description, is_system, is_active, created_at, updated_at) FROM stdin;
860e0b86-e2a9-470f-987b-ae2ab53869c7	1e26d822-336a-4caf-b726-d5bc873bcd47	admin	Admin	Built-in ERP role	t	t	2026-07-25 19:14:16.083238+05:30	2026-07-25 19:14:16.083248+05:30
e4713c0e-a734-4df0-bd30-25c8d0b1190f	1e26d822-336a-4caf-b726-d5bc873bcd47	tenant_admin	Tenant Admin	Built-in ERP role	t	t	2026-07-25 19:14:16.106061+05:30	2026-07-25 19:14:16.106066+05:30
02f3edff-454f-4eea-9bb6-205dd0cb0f56	1e26d822-336a-4caf-b726-d5bc873bcd47	manager	Manager	Built-in ERP role	t	t	2026-07-25 19:14:16.140421+05:30	2026-07-25 19:14:16.140427+05:30
cc0dcdef-a6a0-4f88-9288-fb22c46231f8	1e26d822-336a-4caf-b726-d5bc873bcd47	operator	Operator	Built-in ERP role	t	t	2026-07-25 19:14:16.193432+05:30	2026-07-25 19:14:16.193442+05:30
b8b4f8aa-3055-418b-868b-14dcab660388	1e26d822-336a-4caf-b726-d5bc873bcd47	storekeeper	Storekeeper	Built-in ERP role	t	t	2026-07-25 19:14:16.225683+05:30	2026-07-25 19:14:16.225697+05:30
81f65b36-3188-4a59-a5e9-9ce4266d77fa	1e26d822-336a-4caf-b726-d5bc873bcd47	planner	Planner	Built-in ERP role	t	t	2026-07-25 19:14:16.232903+05:30	2026-07-25 19:14:16.232914+05:30
510e460a-fdaa-4d8c-94dc-d411fb9ae0cd	1e26d822-336a-4caf-b726-d5bc873bcd47	qc	Qc	Built-in ERP role	t	t	2026-07-25 19:14:16.238211+05:30	2026-07-25 19:14:16.238221+05:30
41b8b307-0c79-41c2-9c3a-e85d550695d2	1e26d822-336a-4caf-b726-d5bc873bcd47	sales	Sales	Built-in ERP role	t	t	2026-07-25 19:14:16.244706+05:30	2026-07-25 19:14:16.244711+05:30
8c26ad6f-dd49-4b71-837b-d5f03e39b192	1e26d822-336a-4caf-b726-d5bc873bcd47	accountant	Accountant	Built-in ERP role	t	t	2026-07-25 19:14:16.248002+05:30	2026-07-25 19:14:16.248006+05:30
6047d624-6b36-4c24-8839-bb5a2bf14746	1e26d822-336a-4caf-b726-d5bc873bcd47	worker	Worker	Built-in ERP role	t	t	2026-07-25 19:14:16.250955+05:30	2026-07-25 19:14:16.250959+05:30
948e9704-3bc4-4dbc-b56d-04894ecc11e0	1e26d822-336a-4caf-b726-d5bc873bcd47	client	Client	Built-in ERP role	t	t	2026-07-25 19:14:16.255+05:30	2026-07-25 19:14:16.255003+05:30
e86dce63-4066-4120-9b1a-1fbc0abc2e52	1e26d822-336a-4caf-b726-d5bc873bcd47	supplier	Supplier	Built-in ERP role	t	t	2026-07-25 19:14:16.262444+05:30	2026-07-25 19:14:16.262448+05:30
2e59d634-964a-42db-ba90-5df9c9b84b0e	1e26d822-336a-4caf-b726-d5bc873bcd47	viewer	Viewer	Built-in ERP role	t	t	2026-07-25 19:14:16.269482+05:30	2026-07-25 19:14:16.269486+05:30
876be0ef-2074-4ddb-93d3-26169ca12e12	df413048-964e-45da-af55-91e90d7c54ee	admin	Admin	Built-in ERP role	t	t	2026-08-16 19:41:57.251823+05:30	2026-08-16 19:41:57.251831+05:30
1972fc1b-9d6a-4680-b581-b280b444eb45	df413048-964e-45da-af55-91e90d7c54ee	tenant_admin	Tenant Admin	Built-in ERP role	t	t	2026-08-16 19:41:57.260526+05:30	2026-08-16 19:41:57.260534+05:30
ec0457d4-08ee-4cb8-8915-157dd7aa1cbb	df413048-964e-45da-af55-91e90d7c54ee	manager	Manager	Built-in ERP role	t	t	2026-08-16 19:41:57.281258+05:30	2026-08-16 19:41:57.281267+05:30
d9b239bd-c808-471d-92c2-c236baa2fd35	df413048-964e-45da-af55-91e90d7c54ee	operator	Operator	Built-in ERP role	t	t	2026-08-16 19:41:57.301085+05:30	2026-08-16 19:41:57.301094+05:30
e843ac0f-852c-4e60-9a4f-091869b790f3	df413048-964e-45da-af55-91e90d7c54ee	storekeeper	Storekeeper	Built-in ERP role	t	t	2026-08-16 19:41:57.324686+05:30	2026-08-16 19:41:57.324696+05:30
6ec6fd1d-deac-4b13-926b-4180fedf5a31	df413048-964e-45da-af55-91e90d7c54ee	planner	Planner	Built-in ERP role	t	t	2026-08-16 19:41:57.337286+05:30	2026-08-16 19:41:57.337294+05:30
c12c9e92-43b1-436a-9f62-c5dbaf5531d8	df413048-964e-45da-af55-91e90d7c54ee	qc	Qc	Built-in ERP role	t	t	2026-08-16 19:41:57.344365+05:30	2026-08-16 19:41:57.344371+05:30
6cedfd2f-1159-404a-855f-1f68f2b97ad1	df413048-964e-45da-af55-91e90d7c54ee	sales	Sales	Built-in ERP role	t	t	2026-08-16 19:41:57.349445+05:30	2026-08-16 19:41:57.349452+05:30
ba29d145-d858-4b78-9e41-7fe0bebfd3ac	df413048-964e-45da-af55-91e90d7c54ee	accountant	Accountant	Built-in ERP role	t	t	2026-08-16 19:41:57.353218+05:30	2026-08-16 19:41:57.353223+05:30
77c8d5a0-9427-4b67-90d7-42bd85df7086	df413048-964e-45da-af55-91e90d7c54ee	worker	Worker	Built-in ERP role	t	t	2026-08-16 19:41:57.36006+05:30	2026-08-16 19:41:57.360065+05:30
79cab7d3-5eeb-4151-96fc-93c98ded0912	df413048-964e-45da-af55-91e90d7c54ee	client	Client	Built-in ERP role	t	t	2026-08-16 19:41:57.365778+05:30	2026-08-16 19:41:57.365784+05:30
a1271188-885d-49fc-9920-ece472e74523	df413048-964e-45da-af55-91e90d7c54ee	supplier	Supplier	Built-in ERP role	t	t	2026-08-16 19:41:57.368598+05:30	2026-08-16 19:41:57.368602+05:30
e914a7f9-76ed-4ab0-8a1a-44b6a069f09d	df413048-964e-45da-af55-91e90d7c54ee	viewer	Viewer	Built-in ERP role	t	t	2026-08-16 19:41:57.372002+05:30	2026-08-16 19:41:57.372009+05:30
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants (id, name, slug, plan, is_active, is_deleted, deleted_at, created_at, updated_at, currency_code, currency_symbol, company_name, logo_url, gst_number, address, phone, email, footer_text, signature_image_url, timezone, default_warehouse_name, status, is_system_tenant) FROM stdin;
1e26d822-336a-4caf-b726-d5bc873bcd47	berynx	berync-com	starter	t	f	\N	2026-07-24 22:50:02.455936+05:30	2026-07-24 22:50:02.455944+05:30	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	f
7fd84f4a-c061-4774-a95d-415c4e67b6b6	ShafCorporate	shaf-corp	starter	f	f	\N	2026-07-30 16:37:48.898203+05:30	2026-07-30 16:47:18.300512+05:30	INR	₹	Shafaque Corporatio	\N	12TTTTT1231K1Z5	ro.no 18, 4 floor, building number 30, l.i.g colony kurla west	+919998889988	shafCorp@gmail.com	Corp Shaf	\N	Asia/Kolkata	ro.no 18, 4 floor, building number 40, l.i.g colony kurla west	active	f
df413048-964e-45da-af55-91e90d7c54ee	Berynx HQ	berynx-hq	starter	t	f	\N	2026-08-08 18:46:24.95937+05:30	2026-08-08 18:46:24.959378+05:30	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	t
\.


--
-- Data for Name: units_of_measure; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.units_of_measure (id, tenant_id, code, name, is_active, created_at, updated_at, is_deleted, deleted_at, "precision") FROM stdin;
d934af9a-bb85-4fc2-a23c-abcf44f7394a	52323f77-709b-4cb8-818e-c1ad16262541	KG	kilogram	t	2026-07-24 22:27:22.586692+05:30	2026-07-24 22:27:22.586701+05:30	f	\N	2
533498de-dc4d-4842-840c-43ddc8206c9a	1e26d822-336a-4caf-b726-d5bc873bcd47	KG	kilogram	t	2026-07-24 22:50:51.371175+05:30	2026-07-24 22:50:51.371181+05:30	f	\N	2
5a4cd2fb-e55f-4784-a87b-2a3b2c804437	1e26d822-336a-4caf-b726-d5bc873bcd47	PCS	PCS	t	2026-07-28 19:55:14.299443+05:30	2026-07-28 19:55:14.299449+05:30	f	\N	2
d91ce611-6b54-4db6-82d5-9e03e0bc56e3	7fd84f4a-c061-4774-a95d-415c4e67b6b6	KG	Kilogram	t	2026-07-30 16:54:11.792399+05:30	2026-07-30 16:54:11.792408+05:30	f	\N	2
a33298b4-5eb8-4e05-9064-02934a693062	7fd84f4a-c061-4774-a95d-415c4e67b6b6	ML	Milliliters	t	2026-07-30 16:54:48.870145+05:30	2026-07-30 16:54:48.870151+05:30	f	\N	2
18f11e18-dd91-45f5-8ac1-2340161e2a4e	df413048-964e-45da-af55-91e90d7c54ee	KG	kilo	t	2026-08-16 14:10:46.750613+05:30	2026-08-16 14:10:46.75062+05:30	f	\N	2
\.


--
-- Data for Name: uom_conversions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.uom_conversions (id, tenant_id, from_uom_id, to_uom_id, conversion_factor, created_at, updated_at, is_deleted, deleted_at) FROM stdin;
\.


--
-- Data for Name: user_devices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_devices (id, tenant_id, user_id, device_fingerprint, device_name, ip_address, trusted_until, created_at, last_used_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, tenant_id, email, hashed_password, first_name, last_name, role, is_active, is_deleted, deleted_at, created_at, updated_at, supplier_id, client_id, totp_secret, totp_enabled, backup_codes) FROM stdin;
69ebd965-54bc-4d0d-8231-db1f55e0cde4	1e26d822-336a-4caf-b726-d5bc873bcd47	sayyedtanveer1410@gmail.com	$2b$12$2isVNYg2D5OPSXhYUZBYauRfZlycmkDMLR7CcqPan2IhRWmQpJE06	shafaque	sayyed	admin	t	f	\N	2026-07-24 22:50:03.102352+05:30	2026-07-24 22:50:03.102361+05:30	\N	\N	\N	f	[]
50a4b4fa-eb2a-4e40-a864-34989d88b429	1e26d822-336a-4caf-b726-d5bc873bcd47	tanveer@gmail.com	$2b$12$NjWOs/7fqcuGxwBiaT8PyOSvnuSHci87v.sr9DfdB.hJhjWm/DvfK	tanveer	Portal	client	t	f	\N	2026-07-25 17:19:21.540821+05:30	2026-07-25 17:19:21.54083+05:30	\N	8566fc0d-5da9-4655-9342-1c1cf9b4f261	\N	f	[]
71677bc0-be81-4b5b-94e0-3ac4de233185	7fd84f4a-c061-4774-a95d-415c4e67b6b6	shafaque.sk@gmail.com	$2b$12$2gs.okrx7b33.NvQcP1ssuGwfFiuidXffUyLsl78htmRT9TGVvfES	seher	sayyed	admin	t	f	\N	2026-07-30 16:37:49.608836+05:30	2026-07-30 16:37:49.608852+05:30	\N	\N	\N	f	[]
2c743518-1f62-43be-80ed-c09988b3a0ec	df413048-964e-45da-af55-91e90d7c54ee	sayyedtanveer1410@gmail.com	$2b$12$RFpEICkcI5h/mBbGar4vF.bedFocM0QcsIaFNUfTbg.H6EGBYnasy	 berynx	w	admin	t	f	\N	2026-08-08 18:46:25.813067+05:30	2026-09-23 21:10:33.435748+05:30	\N	\N	\N	f	[]
\.


--
-- Data for Name: warehouse_zones; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.warehouse_zones (id, tenant_id, warehouse_location_id, zone_name, zone_type, capacity, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: wo_number_sequences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.wo_number_sequences (tenant_id, current_value) FROM stdin;
b5ef68c4-18be-4fa6-a439-a23c34877550	61
1e26d822-336a-4caf-b726-d5bc873bcd47	2
df413048-964e-45da-af55-91e90d7c54ee	2
\.


--
-- Data for Name: work_order_materials; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.work_order_materials (id, work_order_id, material_id, unit_id, required_quantity, issued_quantity) FROM stdin;
8fcbc9fc-dfc3-483b-b8ff-05d95acbbc30	5faa5b8c-025c-4637-84e7-0c6a07d57c7f	e2c1deee-51be-4698-8c4c-20aa0d7b027d	533498de-dc4d-4842-840c-43ddc8206c9a	2.000	2.000
4dbc6df3-0361-4d66-bdf6-f81845e96537	88b79ec2-96c1-4242-a023-9889ea0d430b	e2c1deee-51be-4698-8c4c-20aa0d7b027d	533498de-dc4d-4842-840c-43ddc8206c9a	10.000	10.000
0519f934-87f1-4d40-8d79-945477637f98	6b2cc088-c47c-471d-9247-d33974e47a84	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	18f11e18-dd91-45f5-8ac1-2340161e2a4e	1.000	1.000
52a5e4ef-b186-48de-98cd-b7361bf68fe3	66863c47-2254-44a6-b93e-6f9c7633c58b	0541d7e8-e92b-4cc9-af8b-f8ab7e350b97	18f11e18-dd91-45f5-8ac1-2340161e2a4e	1.000	1.000
\.


--
-- Data for Name: work_orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.work_orders (id, wo_number, tenant_id, product_id, bom_id, sales_order_id, planned_quantity, produced_quantity, scrap_quantity, status, priority, start_date, due_date, notes, created_by, is_deleted, deleted_at, created_at, updated_at, sales_order_line_id, hold_reason, hold_started_at) FROM stdin;
5faa5b8c-025c-4637-84e7-0c6a07d57c7f	WO-20260725-0001	1e26d822-336a-4caf-b726-d5bc873bcd47	fb929cf7-6354-433e-b66f-d66fad60a0d5	da32a5b5-375f-4b8f-b40f-a680cb109103	b0e1d83e-fd9b-4b77-b53c-04568725f32b	1.000	1.000	0.000	COMPLETED	HIGH	2026-07-24	2026-07-31	Auto-generated for Sales shortage.	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 18:04:19.336019+05:30	2026-07-25 22:15:33.959965+05:30	c7c8d198-17b8-4fac-9a7b-40ea353726e2	\N	\N
88b79ec2-96c1-4242-a023-9889ea0d430b	WO-20260725-0002	1e26d822-336a-4caf-b726-d5bc873bcd47	fb929cf7-6354-433e-b66f-d66fad60a0d5	da32a5b5-375f-4b8f-b40f-a680cb109103	d13e28dd-d1db-4710-a628-1cf7cfb3d596	5.000	5.000	0.000	COMPLETED	HIGH	2026-07-18	2026-07-25	Auto-generated for Sales shortage.	69ebd965-54bc-4d0d-8231-db1f55e0cde4	f	\N	2026-07-25 23:45:20.585406+05:30	2026-07-26 00:05:33.963764+05:30	cdab60e1-50bb-4870-93fd-80da6daf549b	\N	\N
6b2cc088-c47c-471d-9247-d33974e47a84	WO-20260816-0001	df413048-964e-45da-af55-91e90d7c54ee	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	1b22fd6c-0b9f-4ed8-8f4c-675996dd6b78	cdea16ef-befb-4d97-a598-25fa710f6ce8	1.000	1.000	0.000	COMPLETED	HIGH	2026-08-10	2026-08-17	Auto-generated for Sales shortage.	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 20:02:24.714526+05:30	2026-08-16 20:49:22.765568+05:30	33c5204f-d592-4f17-9f19-e8987fe60caf	\N	\N
66863c47-2254-44a6-b93e-6f9c7633c58b	WO-20260816-0002	df413048-964e-45da-af55-91e90d7c54ee	d18b4ef8-fa0e-47ec-bdf3-1dee4747286b	1b22fd6c-0b9f-4ed8-8f4c-675996dd6b78	bbe75209-17d6-4626-ad3e-df0bbdce24f9	1.000	1.000	0.000	COMPLETED	HIGH	2026-08-10	2026-08-17	Auto-generated for Sales shortage.	2c743518-1f62-43be-80ed-c09988b3a0ec	f	\N	2026-08-16 21:01:48.441582+05:30	2026-08-16 22:34:07.388468+05:30	6cd1b29a-fcfd-4e23-afae-8ff5022e9ee1	\N	\N
\.


--
-- Data for Name: workstations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.workstations (id, tenant_id, code, name, capacity_hours_per_day, hourly_rate, is_active, is_deleted, created_at, updated_at) FROM stdin;
a344f734-88d6-43e4-a0a3-5ca4bd65600c	ecd10cf6-8f87-4799-977e-329aa315fce5	WS-ASSEMBLY-01	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:49:44.093629+05:30	2026-03-25 00:49:44.093629+05:30
84593aab-b841-4ef5-b458-2467f0d6aed1	7b49262e-fa65-429c-af38-e8202ea42a19	WS-ASSEMBLY-c582c485	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:51:21.417495+05:30	2026-03-25 00:51:21.417495+05:30
d05241b9-867e-45ca-ba7d-5cc7caaf49dc	6761d5db-efea-4b6c-846a-2149fe6a9ce8	WS-ASSEMBLY-fefc3912	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:53:04.907263+05:30	2026-03-25 00:53:04.907263+05:30
b3a4cd1c-6f1f-40ed-a845-fbad36d09645	e0bac4d7-0c65-4431-84c7-689d3e36fe96	WS-ASSEMBLY-715b396c	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:53:28.630467+05:30	2026-03-25 00:53:28.630467+05:30
b197f881-87c3-4a40-a955-ff5030ae91ec	034b1e67-f747-4bd2-814a-c42edb05118f	WS-ASSEMBLY-e3c721c3	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:56:33.11732+05:30	2026-03-25 00:56:33.11732+05:30
79a5a5e1-9eab-4b18-a8bb-51a56e8027b8	da7238a4-595f-4444-9c6b-129a843ea42a	WS-ASSEMBLY-a22d8d28	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:58:41.026873+05:30	2026-03-25 00:58:41.026873+05:30
4d5cfecd-daf9-4628-beb2-d23258ecff17	e7379c9c-57db-46df-99a6-93ef64558339	WS-ASSEMBLY-df6441c6	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:59:34.761789+05:30	2026-03-25 00:59:34.761789+05:30
7d542f3c-14bc-4094-8a93-cfcd19a27131	a3f0c1be-c5e4-417e-8da2-32ea3724327f	WS-ASSEMBLY-9646d609	Main Assembly Line	8.00	120.00	t	f	2026-03-25 00:59:59.257082+05:30	2026-03-25 00:59:59.257082+05:30
09e58201-873e-4a0e-bb7c-ce08035a51eb	5d335ba3-e57b-4de0-92b2-1777f6171e22	WS-ASSEMBLY-99a36abc	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:01:25.383515+05:30	2026-03-25 01:01:25.383515+05:30
7483abc2-3c07-4833-a8f0-dec13441d7fb	1dad4af1-4778-4b1b-9903-8743b42e39f9	WS-ASSEMBLY-f402cbe0	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:02:17.965335+05:30	2026-03-25 01:02:17.965335+05:30
1f1a439d-6a19-46ca-8a42-725e6dfa8984	162f0993-8bb2-49bb-9e0f-5d7e7e194cb7	WS-ASSEMBLY-d575a166	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:03:10.129514+05:30	2026-03-25 01:03:10.129514+05:30
97adba67-3e66-46c7-aa8d-4de468519579	6e48eee2-1bab-4551-bce5-6a657d1fae9f	WS-ASSEMBLY-88cc3b70	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:04:44.420136+05:30	2026-03-25 01:04:44.420136+05:30
fac5ec60-527f-44e0-abce-4fb092eda352	eeedd636-a313-40df-9a2d-2621ab48c0e1	WS-ASSEMBLY-b33437b0	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:06:10.980045+05:30	2026-03-25 01:06:10.980045+05:30
4093ae43-f26f-494b-83c0-3168eb2cf80f	6afa3b75-463b-4011-bd29-698b1dae95f2	WS-ASSEMBLY-fc1f6c2c	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:07:53.856063+05:30	2026-03-25 01:07:53.856063+05:30
c10853ea-d61c-43bf-8976-105e086f6c22	a423b246-7db4-4dbf-b891-760e9c35d893	WS-ASSEMBLY-6d41e4f6	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:22:18.029765+05:30	2026-03-25 01:22:18.029765+05:30
682a6620-676e-4602-b7a8-5d063a1b2696	642dcd91-014a-4499-9ba1-2fe7a08cd38b	WS-ASSEMBLY-cf0c6331	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:23:13.088578+05:30	2026-03-25 01:23:13.088578+05:30
8a5851f8-69c6-4485-a95f-0b0d856fbffd	5d6c5ec5-1446-4857-8dc9-29a4d988a1fd	WS-ASSEMBLY-f1d4b7dd	Main Assembly Line	8.00	120.00	t	f	2026-03-25 01:23:55.704787+05:30	2026-03-25 01:23:55.704787+05:30
a69bc7f2-f8ce-4bd7-bde1-ae6c077ee7a4	bb6b4ae4-2d30-46f6-8d25-eca0751eb364	SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 14:03:23.694234+05:30	2026-03-27 14:03:23.694234+05:30
7cff87eb-292a-472f-8a52-29c658f5e561	e3804850-ccb5-47da-b1af-35799d48e960	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 15:17:37.29533+05:30	2026-03-27 15:17:37.29533+05:30
cd3e87cf-be0c-454d-a573-4eb277f87992	e3804850-ccb5-47da-b1af-35799d48e960	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-27 15:17:37.318717+05:30	2026-03-27 15:17:37.318717+05:30
6353efd7-1cdb-45d3-9fd0-47368c72699e	e3804850-ccb5-47da-b1af-35799d48e960	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-27 15:17:37.340656+05:30	2026-03-27 15:17:37.340656+05:30
86af6a79-430c-434e-be3c-fe79de509716	e3804850-ccb5-47da-b1af-35799d48e960	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-27 15:17:37.362233+05:30	2026-03-27 15:17:37.362233+05:30
0a846638-5348-406b-8265-378bb343962d	e3804850-ccb5-47da-b1af-35799d48e960	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-27 15:17:37.384719+05:30	2026-03-27 15:17:37.384719+05:30
34b59a02-9260-427f-8c67-a174b0a27431	e3804850-ccb5-47da-b1af-35799d48e960	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-27 15:17:37.405921+05:30	2026-03-27 15:17:37.405921+05:30
4d599e55-c73f-4a53-be6f-cb97daae037a	e3804850-ccb5-47da-b1af-35799d48e960	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-27 15:17:37.430321+05:30	2026-03-27 15:17:37.430321+05:30
6af843a3-cdfd-4502-a403-3588fa00317c	e3804850-ccb5-47da-b1af-35799d48e960	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-27 15:17:37.453964+05:30	2026-03-27 15:17:37.453964+05:30
7f0f8454-9cf5-460c-9bb1-ca1df7674136	54c91aeb-6ae6-468c-8eee-c0ba5cfe3a78	TEST-e3ed	Test WS	8.00	10.00	t	f	2026-03-27 16:54:19.361801+05:30	2026-03-27 16:54:19.361801+05:30
d785512e-a0ae-41c4-a8f1-933f1530b130	81a76cbb-7377-415b-be06-88e456f8b0f6	WS-1	Test	8.00	10.00	t	f	2026-03-27 17:23:06.274096+05:30	2026-03-27 17:23:06.274096+05:30
9a1559d3-8ab6-45bf-b06d-ff396e5ff537	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 17:31:19.801735+05:30	2026-03-27 17:31:19.801735+05:30
fc06d78f-d995-4049-b39a-5101e8663fe0	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-27 17:31:19.832489+05:30	2026-03-27 17:31:19.832489+05:30
5b125a53-ad73-4dc1-8177-072fb6fed9a9	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-27 17:31:19.855209+05:30	2026-03-27 17:31:19.855209+05:30
562786f2-59de-468c-a307-14ad399db89c	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-27 17:31:19.877909+05:30	2026-03-27 17:31:19.877909+05:30
eb56d441-26d6-4c52-98d1-b433ad878554	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-27 17:31:19.899315+05:30	2026-03-27 17:31:19.899315+05:30
02ee9bcc-a160-40c7-bc23-51bac13a89fe	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-27 17:31:19.919902+05:30	2026-03-27 17:31:19.919902+05:30
831eb7f5-b65e-47fb-8cda-9a553fd1d49d	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-27 17:31:19.942523+05:30	2026-03-27 17:31:19.942523+05:30
5b4e3a8c-5b65-4fbf-b348-4e3a84bfbaca	5fea589e-6bfc-4147-a1ea-bb7c939c384e	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-27 17:31:19.965081+05:30	2026-03-27 17:31:19.965081+05:30
e165fd0c-9089-4b1c-ae55-c4dd08c01ce2	b786c809-d01e-42db-8bac-0d5215891da9	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 17:35:00.498755+05:30	2026-03-27 17:35:00.498755+05:30
520d692b-36e1-4144-b67c-c8fcd83f8860	b786c809-d01e-42db-8bac-0d5215891da9	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-27 17:35:00.584331+05:30	2026-03-27 17:35:00.584331+05:30
775b1569-4a79-4b61-8ba1-d142797ee63c	b786c809-d01e-42db-8bac-0d5215891da9	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-27 17:35:00.594914+05:30	2026-03-27 17:35:00.594914+05:30
7f52d8d9-561b-4d89-8e15-aeee0b3a5dda	b786c809-d01e-42db-8bac-0d5215891da9	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-27 17:35:00.604296+05:30	2026-03-27 17:35:00.604296+05:30
9644ed85-c21f-44b9-84ca-c556b271090a	b786c809-d01e-42db-8bac-0d5215891da9	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-27 17:35:00.615715+05:30	2026-03-27 17:35:00.615715+05:30
b1f37c8e-e966-4656-87b3-e5cce9cc5573	b786c809-d01e-42db-8bac-0d5215891da9	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-27 17:35:00.626779+05:30	2026-03-27 17:35:00.626779+05:30
7b9fbdb6-6d9d-423b-bd6c-cf1b94e94506	b786c809-d01e-42db-8bac-0d5215891da9	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-27 17:35:00.637917+05:30	2026-03-27 17:35:00.637917+05:30
46b4e490-5163-4a2b-bfcb-bbe7728aa87c	b786c809-d01e-42db-8bac-0d5215891da9	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-27 17:35:00.64832+05:30	2026-03-27 17:35:00.64832+05:30
e9f3e606-c3cf-4fb6-9970-4396e4e5b806	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 17:42:41.02376+05:30	2026-03-27 17:42:41.02376+05:30
93196495-f633-43a2-9b21-6538ddedf9c5	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-27 17:42:41.109044+05:30	2026-03-27 17:42:41.109044+05:30
e97ecf7d-1b64-42fc-91d6-2437f2d1e923	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-27 17:42:41.117476+05:30	2026-03-27 17:42:41.117476+05:30
a9eb326c-7459-4976-b08d-105a82dda3e7	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-27 17:42:41.1273+05:30	2026-03-27 17:42:41.1273+05:30
518a31a4-4384-44f7-950e-57efb7336da5	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-27 17:42:41.135631+05:30	2026-03-27 17:42:41.135631+05:30
c89c3dbf-472e-4691-9b48-5e749bead7b3	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-27 17:42:41.144951+05:30	2026-03-27 17:42:41.144951+05:30
c86c0514-cd53-46d6-a671-3f1d0749236d	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-27 17:42:41.153764+05:30	2026-03-27 17:42:41.153764+05:30
a5249fa2-0491-4267-9c43-0a54e02dd73d	3b2413e8-d980-4aab-92f1-ea83e77d4702	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-27 17:42:41.165089+05:30	2026-03-27 17:42:41.165089+05:30
c8ff00df-de90-4a64-bba1-d0f14fe582b1	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 17:44:33.836218+05:30	2026-03-27 17:44:33.836218+05:30
47609d10-e4fb-4479-832d-87bac0fdca93	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-27 17:44:33.845744+05:30	2026-03-27 17:44:33.845744+05:30
6842b4de-08c3-4e73-9007-86adaf78b136	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-27 17:44:33.854512+05:30	2026-03-27 17:44:33.854512+05:30
c788b138-40d8-4333-8a8b-c2e2bb934efd	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-27 17:44:33.864283+05:30	2026-03-27 17:44:33.864283+05:30
f8fdc6e6-0950-46da-b34a-f23471a81a8a	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-27 17:44:33.873114+05:30	2026-03-27 17:44:33.873114+05:30
aa2dbc1e-8b93-453f-8576-d950e79ccc47	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-27 17:44:33.882024+05:30	2026-03-27 17:44:33.882024+05:30
772bfc46-fafe-40e4-aced-399a57446e96	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-27 17:44:33.890617+05:30	2026-03-27 17:44:33.890617+05:30
ebd6ba54-e180-453f-bed6-2ba45cc0f36b	d419f37b-9866-40b0-8e5a-c908748fdbe7	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-27 17:44:33.900334+05:30	2026-03-27 17:44:33.900334+05:30
837e8921-ebb2-4adc-bdd4-9e27dc544612	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 17:47:48.429737+05:30	2026-03-27 17:47:48.429737+05:30
a19fc720-c92e-4579-bce9-10023767406c	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-27 17:47:48.454391+05:30	2026-03-27 17:47:48.454391+05:30
fdc841b4-d14a-4de2-acd7-4179b3c639eb	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-27 17:47:48.475843+05:30	2026-03-27 17:47:48.475843+05:30
9a109e3b-fb5d-4b3b-bff3-24c728f8f467	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-27 17:47:48.501588+05:30	2026-03-27 17:47:48.501588+05:30
0fa04225-e17e-4b7e-907f-ecc30b503d93	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-27 17:47:48.523061+05:30	2026-03-27 17:47:48.523061+05:30
f31f69c5-6701-4fb1-99c4-c256ecf9414e	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-27 17:47:48.545208+05:30	2026-03-27 17:47:48.545208+05:30
32b7bcdc-2431-4b32-85af-f0f04daf949f	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-27 17:47:48.566683+05:30	2026-03-27 17:47:48.566683+05:30
01c0b5b4-91ef-4868-9972-cafa1a8145d4	234f9697-c95a-4356-91aa-b3c42a1d9a17	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-27 17:47:48.588284+05:30	2026-03-27 17:47:48.588284+05:30
79c07c21-4321-4250-8241-6e6b1acd7fd5	a12c668d-facf-4307-922f-0725d8578152	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-28 23:33:03.87228+05:30	2026-03-28 23:33:03.87228+05:30
ac3e1ace-8a8a-4e10-a81c-a4c9e6511b10	a12c668d-facf-4307-922f-0725d8578152	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-28 23:33:03.9128+05:30	2026-03-28 23:33:03.9128+05:30
982b1983-e30f-4e2b-8b1a-d8d75f1aef7a	a12c668d-facf-4307-922f-0725d8578152	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-28 23:33:03.926951+05:30	2026-03-28 23:33:03.926951+05:30
adfc9a6a-642a-4d8c-a281-15726c51bcb7	a12c668d-facf-4307-922f-0725d8578152	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-28 23:33:03.949598+05:30	2026-03-28 23:33:03.949598+05:30
4cca0316-5edb-4403-adf0-8250c1a243dc	a12c668d-facf-4307-922f-0725d8578152	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-28 23:33:03.969919+05:30	2026-03-28 23:33:03.969919+05:30
2e8ebd66-09a1-422e-a425-059405286479	a12c668d-facf-4307-922f-0725d8578152	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-28 23:33:03.988608+05:30	2026-03-28 23:33:03.988608+05:30
7565ab64-4f61-4af1-aa48-5fdba324434e	a12c668d-facf-4307-922f-0725d8578152	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-28 23:33:04.012561+05:30	2026-03-28 23:33:04.012561+05:30
40d2ea83-a8e6-4120-a087-6b6d103aecf9	a12c668d-facf-4307-922f-0725d8578152	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-28 23:33:04.026937+05:30	2026-03-28 23:33:04.026937+05:30
2036eb5b-a347-40ae-a1b6-fdd013267e15	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-SMT-L1	SMT Line 1	8.00	1200.00	t	f	2026-03-27 17:48:32.817804+05:30	2026-03-27 17:48:32.817804+05:30
de4fd658-8ae0-40ca-ad9a-e60f027b408a	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-SMT-L2	SMT Line 2	8.00	1350.00	t	f	2026-03-27 17:48:32.855143+05:30	2026-03-27 17:48:32.855143+05:30
0828cb4a-1204-4a2f-a757-00cf27733277	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-THL-01	Through-Hole Line	8.00	800.00	t	f	2026-03-27 17:48:32.879621+05:30	2026-03-27 17:48:32.879621+05:30
adb637d2-833a-42a7-85b5-1aee3ecf8e37	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-SOL-01	Soldering Station	8.00	600.00	t	f	2026-03-27 17:48:32.904324+05:30	2026-03-27 17:48:32.904324+05:30
91636b98-95c2-4382-a605-4faf64a6bc91	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-HSG-ASY	Housing Assembly	8.00	450.00	t	f	2026-03-27 17:48:32.940306+05:30	2026-03-27 17:48:32.940306+05:30
6e51d092-4e87-4af3-bacd-6944d17feb16	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-TST-B1	Test Bench 1	8.00	700.00	t	f	2026-03-27 17:48:32.964248+05:30	2026-03-27 17:48:32.964248+05:30
ab21d84a-7dbf-4bdd-82ec-dfcbe5e2e67e	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-QC-INS	QC Inspection	8.00	500.00	t	f	2026-03-27 17:48:32.984391+05:30	2026-03-27 17:48:32.984391+05:30
bc287060-c762-4d52-bdd6-971a5a57a3f2	b5ef68c4-18be-4fa6-a439-a23c34877550	V5-PKG-LN	Packaging Line	8.00	350.00	t	f	2026-03-27 17:48:33.006665+05:30	2026-03-27 17:48:33.006665+05:30
550880b9-d2b6-4f74-a8e5-e3bf98838279	52323f77-709b-4cb8-818e-c1ad16262541	ws	cnc	8.00	1.00	t	f	2026-07-21 15:58:18.226926+05:30	2026-07-21 15:58:18.226926+05:30
b5be9f76-5a08-4b2d-8463-c2b2b5362153	1e26d822-336a-4caf-b726-d5bc873bcd47	ws	cnc machine	8.00	0.00	t	f	2026-07-24 22:55:21.773727+05:30	2026-07-24 22:55:21.773727+05:30
85ebaa4f-7a17-49e5-a697-01401dccb8db	7fd84f4a-c061-4774-a95d-415c4e67b6b6	WS-01	Seher	8.00	0.10	t	f	2026-07-30 17:09:19.740028+05:30	2026-07-30 17:09:19.740028+05:30
e69c6344-fe6e-4751-8314-5ca30f3ee966	df413048-964e-45da-af55-91e90d7c54ee	RM-BRA-000002	Plain Roti	8.00	1.00	t	f	2026-08-16 19:42:46.023062+05:30	2026-08-16 19:42:46.023062+05:30
\.


--
-- Name: invoice_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.invoice_seq', 62, true);


--
-- Name: payment_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payment_seq', 9, true);


--
-- Name: supplier_invoice_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.supplier_invoice_seq', 1, true);


--
-- Name: supplier_payment_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.supplier_payment_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: background_jobs background_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.background_jobs
    ADD CONSTRAINT background_jobs_pkey PRIMARY KEY (id);


--
-- Name: batches batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_pkey PRIMARY KEY (id);


--
-- Name: bom_lines bom_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_lines
    ADD CONSTRAINT bom_lines_pkey PRIMARY KEY (id);


--
-- Name: bom_operations bom_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_operations
    ADD CONSTRAINT bom_operations_pkey PRIMARY KEY (id);


--
-- Name: boms boms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boms
    ADD CONSTRAINT boms_pkey PRIMARY KEY (id);


--
-- Name: chart_of_accounts chart_of_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT chart_of_accounts_pkey PRIMARY KEY (id);


--
-- Name: client_addresses client_addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_addresses
    ADD CONSTRAINT client_addresses_pkey PRIMARY KEY (id);


--
-- Name: client_notification_settings client_notification_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_notification_settings
    ADD CONSTRAINT client_notification_settings_pkey PRIMARY KEY (id);


--
-- Name: dashboard_metrics dashboard_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboard_metrics
    ADD CONSTRAINT dashboard_metrics_pkey PRIMARY KEY (id);


--
-- Name: delivery_lines delivery_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_lines
    ADD CONSTRAINT delivery_lines_pkey PRIMARY KEY (id);


--
-- Name: delivery_orders delivery_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_orders
    ADD CONSTRAINT delivery_orders_pkey PRIMARY KEY (id);


--
-- Name: document_associations document_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_associations
    ADD CONSTRAINT document_associations_pkey PRIMARY KEY (id);


--
-- Name: document_revisions document_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_revisions
    ADD CONSTRAINT document_revisions_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: error_logs error_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_pkey PRIMARY KEY (id);


--
-- Name: failed_tasks failed_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_tasks
    ADD CONSTRAINT failed_tasks_pkey PRIMARY KEY (id);


--
-- Name: file_attachments file_attachments_cloudinary_public_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_attachments
    ADD CONSTRAINT file_attachments_cloudinary_public_id_key UNIQUE (cloudinary_public_id);


--
-- Name: file_attachments file_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_attachments
    ADD CONSTRAINT file_attachments_pkey PRIMARY KEY (id);


--
-- Name: financial_transactions financial_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.financial_transactions
    ADD CONSTRAINT financial_transactions_pkey PRIMARY KEY (id);


--
-- Name: goods_receipt_notes goods_receipt_notes_grn_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_grn_number_key UNIQUE (grn_number);


--
-- Name: goods_receipt_notes goods_receipt_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_pkey PRIMARY KEY (id);


--
-- Name: grn_lines grn_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grn_lines
    ADD CONSTRAINT grn_lines_pkey PRIMARY KEY (id);


--
-- Name: import_session_rows import_session_rows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_session_rows
    ADD CONSTRAINT import_session_rows_pkey PRIMARY KEY (id);


--
-- Name: import_sessions import_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_sessions
    ADD CONSTRAINT import_sessions_pkey PRIMARY KEY (id);


--
-- Name: inspection_details inspection_details_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspection_details
    ADD CONSTRAINT inspection_details_pkey PRIMARY KEY (id);


--
-- Name: inspection_templates inspection_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspection_templates
    ADD CONSTRAINT inspection_templates_pkey PRIMARY KEY (id);


--
-- Name: inventory_reservations inventory_reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_reservations
    ADD CONSTRAINT inventory_reservations_pkey PRIMARY KEY (id);


--
-- Name: inventory_transactions inventory_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_pkey PRIMARY KEY (id);


--
-- Name: invoice_disputes invoice_disputes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_disputes
    ADD CONSTRAINT invoice_disputes_pkey PRIMARY KEY (id);


--
-- Name: invoice_lines invoice_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_lines
    ADD CONSTRAINT invoice_lines_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: item_code_sequences item_code_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_code_sequences
    ADD CONSTRAINT item_code_sequences_pkey PRIMARY KEY (id);


--
-- Name: item_templates item_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_templates
    ADD CONSTRAINT item_templates_pkey PRIMARY KEY (id);


--
-- Name: item_variants item_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_variants
    ADD CONSTRAINT item_variants_pkey PRIMARY KEY (id);


--
-- Name: job_cards job_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_cards
    ADD CONSTRAINT job_cards_pkey PRIMARY KEY (id);


--
-- Name: journal_entries journal_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_entries
    ADD CONSTRAINT journal_entries_pkey PRIMARY KEY (id);


--
-- Name: journal_lines journal_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_lines
    ADD CONSTRAINT journal_lines_pkey PRIMARY KEY (id);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (id);


--
-- Name: material_categories material_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_categories
    ADD CONSTRAINT material_categories_pkey PRIMARY KEY (id);


--
-- Name: material_consumption_records material_consumption_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_consumption_records
    ADD CONSTRAINT material_consumption_records_pkey PRIMARY KEY (id);


--
-- Name: material_import_mappings material_import_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_import_mappings
    ADD CONSTRAINT material_import_mappings_pkey PRIMARY KEY (id);


--
-- Name: material_onboarding_profiles material_onboarding_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_onboarding_profiles
    ADD CONSTRAINT material_onboarding_profiles_pkey PRIMARY KEY (id);


--
-- Name: material_onboarding_rows material_onboarding_rows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_onboarding_rows
    ADD CONSTRAINT material_onboarding_rows_pkey PRIMARY KEY (id);


--
-- Name: material_onboarding_sessions material_onboarding_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_onboarding_sessions
    ADD CONSTRAINT material_onboarding_sessions_pkey PRIMARY KEY (id);


--
-- Name: material_requests material_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_pkey PRIMARY KEY (id);


--
-- Name: material_shortages material_shortages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_shortages
    ADD CONSTRAINT material_shortages_pkey PRIMARY KEY (id);


--
-- Name: materials materials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_pkey PRIMARY KEY (id);


--
-- Name: mrp_suggestions mrp_suggestions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mrp_suggestions
    ADD CONSTRAINT mrp_suggestions_pkey PRIMARY KEY (id);


--
-- Name: non_conformance_reports non_conformance_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_conformance_reports
    ADD CONSTRAINT non_conformance_reports_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: number_series_audit_log number_series_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_audit_log
    ADD CONSTRAINT number_series_audit_log_pkey PRIMARY KEY (id);


--
-- Name: number_series_config number_series_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_config
    ADD CONSTRAINT number_series_config_pkey PRIMARY KEY (id);


--
-- Name: number_series_prefixes number_series_prefixes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_prefixes
    ADD CONSTRAINT number_series_prefixes_pkey PRIMARY KEY (id);


--
-- Name: number_series_sequences number_series_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_sequences
    ADD CONSTRAINT number_series_sequences_pkey PRIMARY KEY (id);


--
-- Name: operations operations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operations
    ADD CONSTRAINT operations_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: pick_list_lines pick_list_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_list_lines
    ADD CONSTRAINT pick_list_lines_pkey PRIMARY KEY (id);


--
-- Name: pick_lists pick_lists_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT pick_lists_pkey PRIMARY KEY (id);


--
-- Name: po_number_sequences po_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.po_number_sequences
    ADD CONSTRAINT po_number_sequences_pkey PRIMARY KEY (tenant_id);


--
-- Name: product_images product_images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_images
    ADD CONSTRAINT product_images_pkey PRIMARY KEY (id);


--
-- Name: production_records production_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_records
    ADD CONSTRAINT production_records_pkey PRIMARY KEY (id);


--
-- Name: purchase_order_lines purchase_order_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_pkey PRIMARY KEY (id);


--
-- Name: purchase_orders purchase_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT purchase_orders_pkey PRIMARY KEY (id);


--
-- Name: purchase_requisitions purchase_requisitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_pkey PRIMARY KEY (id);


--
-- Name: purchase_requisitions purchase_requisitions_requisition_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_requisition_number_key UNIQUE (requisition_number);


--
-- Name: quality_inspections quality_inspections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_inspections
    ADD CONSTRAINT quality_inspections_pkey PRIMARY KEY (id);


--
-- Name: quarantine_releases quarantine_releases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_pkey PRIMARY KEY (id);


--
-- Name: report_executions report_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_executions
    ADD CONSTRAINT report_executions_pkey PRIMARY KEY (id);


--
-- Name: report_schedules report_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_schedules
    ADD CONSTRAINT report_schedules_pkey PRIMARY KEY (id);


--
-- Name: rfq_lines rfq_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_lines
    ADD CONSTRAINT rfq_lines_pkey PRIMARY KEY (id);


--
-- Name: rfq_number_sequences rfq_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_number_sequences
    ADD CONSTRAINT rfq_number_sequences_pkey PRIMARY KEY (tenant_id);


--
-- Name: rfq_suppliers rfq_suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_pkey PRIMARY KEY (id);


--
-- Name: rfqs rfqs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_pkey PRIMARY KEY (id);


--
-- Name: sales_clients sales_clients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_clients
    ADD CONSTRAINT sales_clients_pkey PRIMARY KEY (id);


--
-- Name: sales_order_lines sales_order_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_order_lines
    ADD CONSTRAINT sales_order_lines_pkey PRIMARY KEY (id);


--
-- Name: sales_orders sales_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_orders
    ADD CONSTRAINT sales_orders_pkey PRIMARY KEY (id);


--
-- Name: sales_price_list_lines sales_price_list_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_price_list_lines
    ADD CONSTRAINT sales_price_list_lines_pkey PRIMARY KEY (id);


--
-- Name: sales_price_lists sales_price_lists_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_price_lists
    ADD CONSTRAINT sales_price_lists_pkey PRIMARY KEY (id);


--
-- Name: saved_reports saved_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_reports
    ADD CONSTRAINT saved_reports_pkey PRIMARY KEY (id);


--
-- Name: serial_numbers serial_numbers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.serial_numbers
    ADD CONSTRAINT serial_numbers_pkey PRIMARY KEY (id);


--
-- Name: stock_ledger_entries stock_ledger_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_ledger_entries
    ADD CONSTRAINT stock_ledger_entries_pkey PRIMARY KEY (id);


--
-- Name: stock_levels stock_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT stock_levels_pkey PRIMARY KEY (id);


--
-- Name: stock_reservations stock_reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_reservations
    ADD CONSTRAINT stock_reservations_pkey PRIMARY KEY (id);


--
-- Name: subcontract_material_issues subcontract_material_issues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_material_issues
    ADD CONSTRAINT subcontract_material_issues_pkey PRIMARY KEY (id);


--
-- Name: subcontract_number_sequences subcontract_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_number_sequences
    ADD CONSTRAINT subcontract_number_sequences_pkey PRIMARY KEY (tenant_id);


--
-- Name: subcontract_order_lines subcontract_order_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_order_lines
    ADD CONSTRAINT subcontract_order_lines_pkey PRIMARY KEY (id);


--
-- Name: subcontract_orders subcontract_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_orders
    ADD CONSTRAINT subcontract_orders_pkey PRIMARY KEY (id);


--
-- Name: supplier_invoices supplier_invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT supplier_invoices_pkey PRIMARY KEY (id);


--
-- Name: supplier_payments supplier_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_payments
    ADD CONSTRAINT supplier_payments_pkey PRIMARY KEY (id);


--
-- Name: supplier_price_history supplier_price_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_price_history
    ADD CONSTRAINT supplier_price_history_pkey PRIMARY KEY (id);


--
-- Name: supplier_quotations supplier_quotations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT supplier_quotations_pkey PRIMARY KEY (id);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (id);


--
-- Name: technical_documents technical_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_documents
    ADD CONSTRAINT technical_documents_pkey PRIMARY KEY (id);


--
-- Name: tenant_audit_logs tenant_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_audit_logs
    ADD CONSTRAINT tenant_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: tenant_finance_settings tenant_finance_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_finance_settings
    ADD CONSTRAINT tenant_finance_settings_pkey PRIMARY KEY (id);


--
-- Name: tenant_role_permissions tenant_role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_role_permissions
    ADD CONSTRAINT tenant_role_permissions_pkey PRIMARY KEY (id);


--
-- Name: tenant_roles tenant_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_roles
    ADD CONSTRAINT tenant_roles_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: workstations uix_workstation_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workstations
    ADD CONSTRAINT uix_workstation_tenant_code UNIQUE (tenant_id, code);


--
-- Name: units_of_measure units_of_measure_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.units_of_measure
    ADD CONSTRAINT units_of_measure_pkey PRIMARY KEY (id);


--
-- Name: uom_conversions uom_conversions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uom_conversions
    ADD CONSTRAINT uom_conversions_pkey PRIMARY KEY (id);


--
-- Name: batches uq_batch_tenant_material_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT uq_batch_tenant_material_number UNIQUE (tenant_id, material_id, batch_number);


--
-- Name: boms uq_bom_tenant_template_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boms
    ADD CONSTRAINT uq_bom_tenant_template_version UNIQUE (tenant_id, template_id, version);


--
-- Name: boms uq_bom_tenant_variant_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boms
    ADD CONSTRAINT uq_bom_tenant_variant_version UNIQUE (tenant_id, variant_id, version);


--
-- Name: client_notification_settings uq_client_notification_settings_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_notification_settings
    ADD CONSTRAINT uq_client_notification_settings_user UNIQUE (user_id);


--
-- Name: sales_clients uq_client_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_clients
    ADD CONSTRAINT uq_client_tenant_code UNIQUE (tenant_id, code);


--
-- Name: chart_of_accounts uq_coa_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT uq_coa_tenant_code UNIQUE (tenant_id, code);


--
-- Name: chart_of_accounts uq_coa_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT uq_coa_tenant_name UNIQUE (tenant_id, name);


--
-- Name: delivery_orders uq_delivery_order_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_orders
    ADD CONSTRAINT uq_delivery_order_tenant_number UNIQUE (tenant_id, delivery_number);


--
-- Name: document_revisions uq_doc_revision_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_revisions
    ADD CONSTRAINT uq_doc_revision_code UNIQUE (tenant_id, document_id, revision_code);


--
-- Name: invoices uq_invoice_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT uq_invoice_tenant_number UNIQUE (tenant_id, invoice_number);


--
-- Name: item_code_sequences uq_item_code_sequence_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_code_sequences
    ADD CONSTRAINT uq_item_code_sequence_scope UNIQUE (tenant_id, item_type, category_id);


--
-- Name: item_templates uq_item_template_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_templates
    ADD CONSTRAINT uq_item_template_tenant_code UNIQUE (tenant_id, code);


--
-- Name: item_variants uq_item_variant_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_variants
    ADD CONSTRAINT uq_item_variant_key UNIQUE (tenant_id, template_id, variant_key);


--
-- Name: item_variants uq_item_variant_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_variants
    ADD CONSTRAINT uq_item_variant_tenant_code UNIQUE (tenant_id, code);


--
-- Name: journal_entries uq_journal_entry_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_entries
    ADD CONSTRAINT uq_journal_entry_tenant_number UNIQUE (tenant_id, entry_number);


--
-- Name: locations uq_location_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT uq_location_tenant_name UNIQUE (tenant_id, name);


--
-- Name: material_categories uq_material_category_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_categories
    ADD CONSTRAINT uq_material_category_tenant_name UNIQUE (tenant_id, name);


--
-- Name: materials uq_material_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT uq_material_tenant_code UNIQUE (tenant_id, code);


--
-- Name: number_series_prefixes uq_ns_prefix_tenant_entity_subtype; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_prefixes
    ADD CONSTRAINT uq_ns_prefix_tenant_entity_subtype UNIQUE (tenant_id, entity_type, sub_type);


--
-- Name: number_series_sequences uq_ns_sequence_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_sequences
    ADD CONSTRAINT uq_ns_sequence_scope UNIQUE (tenant_id, entity_type, prefix);


--
-- Name: number_series_config uq_number_series_config_tenant_entity; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_config
    ADD CONSTRAINT uq_number_series_config_tenant_entity UNIQUE (tenant_id, entity_type);


--
-- Name: operations uq_operations_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operations
    ADD CONSTRAINT uq_operations_tenant_code UNIQUE (tenant_id, operation_code);


--
-- Name: password_reset_tokens uq_password_reset_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT uq_password_reset_token_hash UNIQUE (token_hash);


--
-- Name: payments uq_payment_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT uq_payment_tenant_number UNIQUE (tenant_id, payment_number);


--
-- Name: purchase_orders uq_po_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT uq_po_tenant_number UNIQUE (tenant_id, po_number);


--
-- Name: sales_orders uq_sales_order_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_orders
    ADD CONSTRAINT uq_sales_order_tenant_number UNIQUE (tenant_id, order_number);


--
-- Name: serial_numbers uq_serial_tenant_serial_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.serial_numbers
    ADD CONSTRAINT uq_serial_tenant_serial_number UNIQUE (tenant_id, serial_number);


--
-- Name: stock_levels uq_stock_levels_bucket; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT uq_stock_levels_bucket UNIQUE (tenant_id, material_id, location_id, stock_status);


--
-- Name: subcontract_orders uq_subco_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_orders
    ADD CONSTRAINT uq_subco_tenant_number UNIQUE (tenant_id, order_number);


--
-- Name: supplier_invoices uq_supplier_invoice_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT uq_supplier_invoice_tenant_number UNIQUE (tenant_id, invoice_number);


--
-- Name: supplier_payments uq_supplier_payment_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_payments
    ADD CONSTRAINT uq_supplier_payment_tenant_number UNIQUE (tenant_id, payment_number);


--
-- Name: suppliers uq_suppliers_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT uq_suppliers_tenant_code UNIQUE (tenant_id, code);


--
-- Name: technical_documents uq_technical_doc_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_documents
    ADD CONSTRAINT uq_technical_doc_tenant_number UNIQUE (tenant_id, document_number);


--
-- Name: tenant_finance_settings uq_tenant_finance_settings_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_finance_settings
    ADD CONSTRAINT uq_tenant_finance_settings_tenant UNIQUE (tenant_id);


--
-- Name: tenant_roles uq_tenant_role_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_roles
    ADD CONSTRAINT uq_tenant_role_name UNIQUE (tenant_id, name);


--
-- Name: tenant_role_permissions uq_tenant_role_permission; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_role_permissions
    ADD CONSTRAINT uq_tenant_role_permission UNIQUE (role_id, permission);


--
-- Name: uom_conversions uq_uom_conv_tenant_from_to; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uom_conversions
    ADD CONSTRAINT uq_uom_conv_tenant_from_to UNIQUE (tenant_id, from_uom_id, to_uom_id);


--
-- Name: units_of_measure uq_uom_tenant_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.units_of_measure
    ADD CONSTRAINT uq_uom_tenant_code UNIQUE (tenant_id, code);


--
-- Name: user_devices uq_user_device_fingerprint; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_devices
    ADD CONSTRAINT uq_user_device_fingerprint UNIQUE (user_id, device_fingerprint);


--
-- Name: work_orders uq_work_order_tenant_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT uq_work_order_tenant_number UNIQUE (tenant_id, wo_number);


--
-- Name: user_devices user_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_devices
    ADD CONSTRAINT user_devices_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: warehouse_zones warehouse_zones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_zones
    ADD CONSTRAINT warehouse_zones_pkey PRIMARY KEY (id);


--
-- Name: wo_number_sequences wo_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wo_number_sequences
    ADD CONSTRAINT wo_number_sequences_pkey PRIMARY KEY (tenant_id);


--
-- Name: work_order_materials work_order_materials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_materials
    ADD CONSTRAINT work_order_materials_pkey PRIMARY KEY (id);


--
-- Name: work_orders work_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT work_orders_pkey PRIMARY KEY (id);


--
-- Name: workstations workstations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workstations
    ADD CONSTRAINT workstations_pkey PRIMARY KEY (id);


--
-- Name: idx_error_logs_status_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_status_timestamp ON public.error_logs USING btree (status_code, "timestamp");


--
-- Name: idx_error_logs_tenant_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_tenant_timestamp ON public.error_logs USING btree (tenant_id, "timestamp");


--
-- Name: idx_error_logs_timestamp_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_timestamp_desc ON public.error_logs USING btree ("timestamp");


--
-- Name: idx_error_logs_trace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_trace_id ON public.error_logs USING btree (trace_id);


--
-- Name: idx_sales_orders_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sales_orders_tenant_status ON public.sales_orders USING btree (tenant_id, status);


--
-- Name: idx_tenant_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tenant_audit_logs_tenant_id ON public.tenant_audit_logs USING btree (tenant_id);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_correlation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_correlation_id ON public.audit_logs USING btree (correlation_id);


--
-- Name: ix_audit_logs_occurred_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_occurred_at ON public.audit_logs USING btree (occurred_at);


--
-- Name: ix_audit_logs_tenant_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_tenant_entity ON public.audit_logs USING btree (tenant_id, entity_type, entity_id, occurred_at);


--
-- Name: ix_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_tenant_id ON public.audit_logs USING btree (tenant_id);


--
-- Name: ix_background_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_background_jobs_status ON public.background_jobs USING btree (status);


--
-- Name: ix_background_jobs_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_background_jobs_type ON public.background_jobs USING btree (job_type);


--
-- Name: ix_batches_expiry_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batches_expiry_date ON public.batches USING btree (expiry_date);


--
-- Name: ix_batches_material_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batches_material_id ON public.batches USING btree (material_id);


--
-- Name: ix_batches_tenant_batch_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batches_tenant_batch_number ON public.batches USING btree (tenant_id, batch_number);


--
-- Name: ix_batches_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batches_tenant_id ON public.batches USING btree (tenant_id);


--
-- Name: ix_batches_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batches_tenant_material ON public.batches USING btree (tenant_id, material_id);


--
-- Name: ix_bom_line_tenant_bom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bom_line_tenant_bom ON public.bom_lines USING btree (tenant_id, bom_id);


--
-- Name: ix_bom_lines_bom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bom_lines_bom_id ON public.bom_lines USING btree (bom_id);


--
-- Name: ix_bom_operations_bom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bom_operations_bom_id ON public.bom_operations USING btree (bom_id);


--
-- Name: ix_bom_operations_operation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bom_operations_operation_id ON public.bom_operations USING btree (operation_id);


--
-- Name: ix_bom_operations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bom_operations_tenant_id ON public.bom_operations USING btree (tenant_id);


--
-- Name: ix_bom_tenant_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bom_tenant_product ON public.boms USING btree (tenant_id, template_id, variant_id);


--
-- Name: ix_client_addresses_client; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_addresses_client ON public.client_addresses USING btree (client_id);


--
-- Name: ix_client_addresses_default; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_addresses_default ON public.client_addresses USING btree (client_id, type, is_default);


--
-- Name: ix_client_addresses_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_addresses_tenant ON public.client_addresses USING btree (tenant_id);


--
-- Name: ix_client_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_is_active ON public.sales_clients USING btree (is_active);


--
-- Name: ix_client_is_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_is_deleted ON public.sales_clients USING btree (is_deleted);


--
-- Name: ix_client_notification_settings_client; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_notification_settings_client ON public.client_notification_settings USING btree (client_id);


--
-- Name: ix_client_notification_settings_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_notification_settings_tenant ON public.client_notification_settings USING btree (tenant_id);


--
-- Name: ix_client_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_tenant_id ON public.sales_clients USING btree (tenant_id);


--
-- Name: ix_coa_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coa_tenant ON public.chart_of_accounts USING btree (tenant_id);


--
-- Name: ix_coa_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coa_type ON public.chart_of_accounts USING btree (tenant_id, account_type);


--
-- Name: ix_dashboard_metrics_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dashboard_metrics_tenant_id ON public.dashboard_metrics USING btree (tenant_id);


--
-- Name: ix_delivery_lines_delivery; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_delivery_lines_delivery ON public.delivery_lines USING btree (delivery_order_id);


--
-- Name: ix_delivery_lines_sales_line; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_delivery_lines_sales_line ON public.delivery_lines USING btree (sales_order_line_id);


--
-- Name: ix_delivery_orders_sales_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_delivery_orders_sales_order ON public.delivery_orders USING btree (sales_order_id);


--
-- Name: ix_delivery_orders_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_delivery_orders_tenant_status ON public.delivery_orders USING btree (tenant_id, status);


--
-- Name: ix_document_associations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_associations_tenant_id ON public.document_associations USING btree (tenant_id);


--
-- Name: ix_document_revisions_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_revisions_tenant_id ON public.document_revisions USING btree (tenant_id);


--
-- Name: ix_documents_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_entity ON public.documents USING btree (document_type, entity_id);


--
-- Name: ix_documents_is_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_is_deleted ON public.documents USING btree (is_deleted);


--
-- Name: ix_documents_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_tenant_id ON public.documents USING btree (tenant_id);


--
-- Name: ix_error_logs_correlation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_logs_correlation_id ON public.error_logs USING btree (correlation_id);


--
-- Name: ix_error_logs_error_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_logs_error_code ON public.error_logs USING btree (error_code);


--
-- Name: ix_error_logs_status_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_logs_status_code ON public.error_logs USING btree (status_code);


--
-- Name: ix_error_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_logs_tenant_id ON public.error_logs USING btree (tenant_id);


--
-- Name: ix_error_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_logs_timestamp ON public.error_logs USING btree ("timestamp");


--
-- Name: ix_error_logs_trace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_logs_trace_id ON public.error_logs USING btree (trace_id);


--
-- Name: ix_failed_tasks_failed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_failed_tasks_failed_at ON public.failed_tasks USING btree (failed_at);


--
-- Name: ix_failed_tasks_task_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_failed_tasks_task_name ON public.failed_tasks USING btree (task_name);


--
-- Name: ix_failed_tasks_tenant_failed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_failed_tasks_tenant_failed_at ON public.failed_tasks USING btree (tenant_id, failed_at);


--
-- Name: ix_failed_tasks_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_failed_tasks_tenant_id ON public.failed_tasks USING btree (tenant_id);


--
-- Name: ix_file_attachments_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_file_attachments_tenant_id ON public.file_attachments USING btree (tenant_id);


--
-- Name: ix_financial_transactions_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_financial_transactions_date ON public.financial_transactions USING btree (created_at);


--
-- Name: ix_financial_transactions_reference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_financial_transactions_reference ON public.financial_transactions USING btree (reference_type, reference_id);


--
-- Name: ix_financial_transactions_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_financial_transactions_tenant ON public.financial_transactions USING btree (tenant_id);


--
-- Name: ix_grn_line_grn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_grn_line_grn ON public.grn_lines USING btree (grn_id);


--
-- Name: ix_grn_line_po_line; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_grn_line_po_line ON public.grn_lines USING btree (po_line_id);


--
-- Name: ix_grn_tenant_po; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_grn_tenant_po ON public.goods_receipt_notes USING btree (tenant_id, purchase_order_id);


--
-- Name: ix_grn_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_grn_tenant_status ON public.goods_receipt_notes USING btree (tenant_id, status);


--
-- Name: ix_grn_tenant_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_grn_tenant_supplier ON public.goods_receipt_notes USING btree (tenant_id, supplier_id);


--
-- Name: ix_import_session_rows_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_import_session_rows_session ON public.import_session_rows USING btree (session_id);


--
-- Name: ix_import_session_rows_valid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_import_session_rows_valid ON public.import_session_rows USING btree (is_valid);


--
-- Name: ix_import_sessions_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_import_sessions_expires ON public.import_sessions USING btree (expires_at);


--
-- Name: ix_import_sessions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_import_sessions_status ON public.import_sessions USING btree (status);


--
-- Name: ix_import_sessions_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_import_sessions_tenant ON public.import_sessions USING btree (tenant_id);


--
-- Name: ix_insp_det_inspection; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_insp_det_inspection ON public.inspection_details USING btree (inspection_id);


--
-- Name: ix_insp_tpl_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_insp_tpl_tenant ON public.inspection_templates USING btree (tenant_id);


--
-- Name: ix_inv_tx_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_tx_tenant_id ON public.inventory_transactions USING btree (tenant_id);


--
-- Name: ix_inv_tx_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_tx_tenant_material ON public.inventory_transactions USING btree (tenant_id, material_id);


--
-- Name: ix_inventory_transactions_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inventory_transactions_tenant_material ON public.inventory_transactions USING btree (tenant_id, material_id, created_at);


--
-- Name: ix_invoice_dispute_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_dispute_invoice ON public.invoice_disputes USING btree (supplier_invoice_id);


--
-- Name: ix_invoice_lines_invoice_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_lines_invoice_id ON public.invoice_lines USING btree (invoice_id);


--
-- Name: ix_invoice_lines_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_lines_tenant ON public.invoice_lines USING btree (tenant_id);


--
-- Name: ix_invoices_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoices_client_id ON public.invoices USING btree (client_id);


--
-- Name: ix_invoices_due_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoices_due_date ON public.invoices USING btree (due_date);


--
-- Name: ix_invoices_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoices_status ON public.invoices USING btree (status);


--
-- Name: ix_invoices_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoices_tenant_id ON public.invoices USING btree (tenant_id);


--
-- Name: ix_ir_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ir_status ON public.inventory_reservations USING btree (status);


--
-- Name: ix_ir_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ir_tenant_material ON public.inventory_reservations USING btree (tenant_id, material_id);


--
-- Name: ix_ir_tenant_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ir_tenant_ref ON public.inventory_reservations USING btree (tenant_id, reference_type, reference_id);


--
-- Name: ix_item_code_sequences_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_code_sequences_tenant ON public.item_code_sequences USING btree (tenant_id);


--
-- Name: ix_item_templates_tenant_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_templates_tenant_code ON public.item_templates USING btree (tenant_id, code);


--
-- Name: ix_item_templates_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_templates_tenant_id ON public.item_templates USING btree (tenant_id);


--
-- Name: ix_item_variants_material_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_variants_material_id ON public.item_variants USING btree (material_id);


--
-- Name: ix_item_variants_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_variants_template_id ON public.item_variants USING btree (template_id);


--
-- Name: ix_item_variants_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_variants_tenant_id ON public.item_variants USING btree (tenant_id);


--
-- Name: ix_item_variants_variant_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_variants_variant_key ON public.item_variants USING btree (tenant_id, template_id, variant_key);


--
-- Name: ix_job_cards_work_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_cards_work_order_id ON public.job_cards USING btree (work_order_id);


--
-- Name: ix_journal_entries_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_journal_entries_date ON public.journal_entries USING btree (tenant_id, entry_date);


--
-- Name: ix_journal_entries_reference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_journal_entries_reference ON public.journal_entries USING btree (tenant_id, reference_type, reference_id);


--
-- Name: ix_journal_entries_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_journal_entries_tenant ON public.journal_entries USING btree (tenant_id);


--
-- Name: ix_journal_lines_account; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_journal_lines_account ON public.journal_lines USING btree (account_id);


--
-- Name: ix_journal_lines_entry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_journal_lines_entry ON public.journal_lines USING btree (journal_entry_id);


--
-- Name: ix_ledger_tenant_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ledger_tenant_date ON public.stock_ledger_entries USING btree (tenant_id, transaction_date);


--
-- Name: ix_ledger_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ledger_tenant_material ON public.stock_ledger_entries USING btree (tenant_id, material_id);


--
-- Name: ix_location_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_location_tenant_id ON public.locations USING btree (tenant_id);


--
-- Name: ix_material_categories_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_material_categories_tenant_id ON public.material_categories USING btree (tenant_id);


--
-- Name: ix_material_consumption_records_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_material_consumption_records_tenant_id ON public.material_consumption_records USING btree (tenant_id);


--
-- Name: ix_material_import_mappings_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_material_import_mappings_tenant_id ON public.material_import_mappings USING btree (tenant_id);


--
-- Name: ix_material_onboarding_profiles_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_material_onboarding_profiles_tenant_id ON public.material_onboarding_profiles USING btree (tenant_id);


--
-- Name: ix_material_onboarding_rows_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_material_onboarding_rows_session_id ON public.material_onboarding_rows USING btree (session_id);


--
-- Name: ix_material_onboarding_rows_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_material_onboarding_rows_tenant_id ON public.material_onboarding_rows USING btree (tenant_id);


--
-- Name: ix_material_onboarding_sessions_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_material_onboarding_sessions_tenant_id ON public.material_onboarding_sessions USING btree (tenant_id);


--
-- Name: ix_materials_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_materials_category_id ON public.materials USING btree (category_id);


--
-- Name: ix_materials_is_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_materials_is_deleted ON public.materials USING btree (is_deleted);


--
-- Name: ix_materials_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_materials_tenant_id ON public.materials USING btree (tenant_id);


--
-- Name: ix_mcr_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mcr_material ON public.material_consumption_records USING btree (tenant_id, material_id);


--
-- Name: ix_mcr_tenant_wo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mcr_tenant_wo ON public.material_consumption_records USING btree (tenant_id, work_order_id);


--
-- Name: ix_mr_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mr_tenant_status ON public.material_requests USING btree (tenant_id, status);


--
-- Name: ix_mrp_suggestions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mrp_suggestions_created_at ON public.mrp_suggestions USING btree (tenant_id, created_at);


--
-- Name: ix_mrp_suggestions_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mrp_suggestions_tenant_material ON public.mrp_suggestions USING btree (tenant_id, material_id);


--
-- Name: ix_mrp_suggestions_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mrp_suggestions_tenant_status ON public.mrp_suggestions USING btree (tenant_id, status);


--
-- Name: ix_ms_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ms_status ON public.material_shortages USING btree (status);


--
-- Name: ix_ms_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ms_tenant_material ON public.material_shortages USING btree (tenant_id, material_id);


--
-- Name: ix_ms_tenant_wo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ms_tenant_wo ON public.material_shortages USING btree (tenant_id, work_order_id);


--
-- Name: ix_ncr_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ncr_tenant ON public.non_conformance_reports USING btree (tenant_id);


--
-- Name: ix_notifications_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_tenant ON public.notifications USING btree (tenant_id);


--
-- Name: ix_notifications_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user ON public.notifications USING btree (user_id, is_read);


--
-- Name: ix_ns_audit_log_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ns_audit_log_tenant ON public.number_series_audit_log USING btree (tenant_id);


--
-- Name: ix_ns_sequences_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ns_sequences_tenant ON public.number_series_sequences USING btree (tenant_id);


--
-- Name: ix_operations_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operations_code ON public.operations USING btree (operation_code) WHERE (is_deleted = false);


--
-- Name: ix_operations_tenant_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operations_tenant_active ON public.operations USING btree (tenant_id, is_deleted) WHERE (is_deleted = false);


--
-- Name: ix_operations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operations_tenant_id ON public.operations USING btree (tenant_id);


--
-- Name: ix_operations_tenant_sequence; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operations_tenant_sequence ON public.operations USING btree (tenant_id, default_sequence) WHERE (is_deleted = false);


--
-- Name: ix_operations_workstation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operations_workstation_id ON public.operations USING btree (workstation_id);


--
-- Name: ix_password_reset_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_reset_tenant ON public.password_reset_tokens USING btree (tenant_id);


--
-- Name: ix_password_reset_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_reset_user ON public.password_reset_tokens USING btree (user_id);


--
-- Name: ix_payments_client; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_client ON public.payments USING btree (client_id);


--
-- Name: ix_payments_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_invoice ON public.payments USING btree (invoice_id);


--
-- Name: ix_payments_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_tenant ON public.payments USING btree (tenant_id);


--
-- Name: ix_pick_lists_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pick_lists_tenant_id ON public.pick_lists USING btree (tenant_id);


--
-- Name: ix_po_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_po_status ON public.purchase_orders USING btree (tenant_id, status);


--
-- Name: ix_po_tenant_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_po_tenant_supplier ON public.purchase_orders USING btree (tenant_id, supplier_id);


--
-- Name: ix_pol_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pol_material ON public.purchase_order_lines USING btree (material_id);


--
-- Name: ix_pol_po; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pol_po ON public.purchase_order_lines USING btree (purchase_order_id);


--
-- Name: ix_price_list_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_price_list_is_active ON public.sales_price_lists USING btree (is_active);


--
-- Name: ix_price_list_is_default; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_price_list_is_default ON public.sales_price_lists USING btree (is_default);


--
-- Name: ix_price_list_is_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_price_list_is_deleted ON public.sales_price_lists USING btree (is_deleted);


--
-- Name: ix_price_list_line_price_list_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_price_list_line_price_list_id ON public.sales_price_list_lines USING btree (price_list_id);


--
-- Name: ix_price_list_line_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_price_list_line_product ON public.sales_price_list_lines USING btree (price_list_id, product_id, product_type);


--
-- Name: ix_price_list_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_price_list_tenant_id ON public.sales_price_lists USING btree (tenant_id);


--
-- Name: ix_price_list_valid_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_price_list_valid_from ON public.sales_price_lists USING btree (valid_from);


--
-- Name: ix_product_images_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_images_order ON public.product_images USING btree (template_id, variant_id, image_order);


--
-- Name: ix_product_images_tenant_template; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_images_tenant_template ON public.product_images USING btree (tenant_id, template_id);


--
-- Name: ix_product_images_tenant_variant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_images_tenant_variant ON public.product_images USING btree (tenant_id, variant_id);


--
-- Name: ix_production_records_work_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_production_records_work_order_id ON public.production_records USING btree (work_order_id);


--
-- Name: ix_purchase_requisitions_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_purchase_requisitions_tenant_id ON public.purchase_requisitions USING btree (tenant_id);


--
-- Name: ix_purchase_requisitions_tenant_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_purchase_requisitions_tenant_material ON public.purchase_requisitions USING btree (tenant_id, material_id);


--
-- Name: ix_purchase_requisitions_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_purchase_requisitions_tenant_status ON public.purchase_requisitions USING btree (tenant_id, status);


--
-- Name: ix_qi_tenant_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_qi_tenant_ref ON public.quality_inspections USING btree (tenant_id, reference_type, reference_id);


--
-- Name: ix_qr_ncr; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_qr_ncr ON public.quarantine_releases USING btree (ncr_id);


--
-- Name: ix_report_executions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_report_executions_created_at ON public.report_executions USING btree (created_at);


--
-- Name: ix_report_executions_report_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_report_executions_report_id ON public.report_executions USING btree (report_id);


--
-- Name: ix_report_executions_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_report_executions_tenant_id ON public.report_executions USING btree (tenant_id);


--
-- Name: ix_report_schedules_report_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_report_schedules_report_id ON public.report_schedules USING btree (report_id);


--
-- Name: ix_report_schedules_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_report_schedules_tenant_id ON public.report_schedules USING btree (tenant_id);


--
-- Name: ix_rfq_lines_rfq; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rfq_lines_rfq ON public.rfq_lines USING btree (rfq_id);


--
-- Name: ix_rfq_supplier_rfq; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rfq_supplier_rfq ON public.rfq_suppliers USING btree (rfq_id, supplier_id);


--
-- Name: ix_rfq_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rfq_tenant ON public.rfqs USING btree (tenant_id);


--
-- Name: ix_sales_clients_default_price_list_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_clients_default_price_list_id ON public.sales_clients USING btree (default_price_list_id);


--
-- Name: ix_sales_order_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_client_id ON public.sales_orders USING btree (client_id);


--
-- Name: ix_sales_order_delivery_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_delivery_date ON public.sales_orders USING btree (delivery_date);


--
-- Name: ix_sales_order_is_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_is_deleted ON public.sales_orders USING btree (is_deleted);


--
-- Name: ix_sales_order_line_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_line_order_id ON public.sales_order_lines USING btree (sales_order_id);


--
-- Name: ix_sales_order_line_product_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_line_product_id ON public.sales_order_lines USING btree (product_id);


--
-- Name: ix_sales_order_line_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_line_status ON public.sales_order_lines USING btree (status);


--
-- Name: ix_sales_order_lines_work_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_lines_work_order_id ON public.sales_order_lines USING btree (work_order_id);


--
-- Name: ix_sales_order_order_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_order_date ON public.sales_orders USING btree (order_date);


--
-- Name: ix_sales_order_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_status ON public.sales_orders USING btree (status);


--
-- Name: ix_sales_order_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_order_tenant_id ON public.sales_orders USING btree (tenant_id);


--
-- Name: ix_sales_orders_approver_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_orders_approver_id ON public.sales_orders USING btree (approver_id);


--
-- Name: ix_sales_orders_pending_approval; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_orders_pending_approval ON public.sales_orders USING btree (tenant_id, status, approver_id) WHERE (is_deleted = false);


--
-- Name: ix_sales_orders_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_orders_priority ON public.sales_orders USING btree (tenant_id, priority);


--
-- Name: ix_sales_orders_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_orders_tenant_status ON public.sales_orders USING btree (tenant_id, status, is_deleted);


--
-- Name: ix_saved_reports_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_saved_reports_tenant_id ON public.saved_reports USING btree (tenant_id);


--
-- Name: ix_sco_line_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sco_line_order ON public.subcontract_order_lines USING btree (subcontract_order_id);


--
-- Name: ix_sco_line_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sco_line_tenant ON public.subcontract_order_lines USING btree (tenant_id);


--
-- Name: ix_serial_numbers_material_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_serial_numbers_material_id ON public.serial_numbers USING btree (material_id);


--
-- Name: ix_serial_numbers_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_serial_numbers_status ON public.serial_numbers USING btree (status);


--
-- Name: ix_serial_numbers_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_serial_numbers_tenant_id ON public.serial_numbers USING btree (tenant_id);


--
-- Name: ix_serial_numbers_tenant_serial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_serial_numbers_tenant_serial ON public.serial_numbers USING btree (tenant_id, serial_number);


--
-- Name: ix_smi_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_smi_order ON public.subcontract_material_issues USING btree (subcontract_order_id);


--
-- Name: ix_sph_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sph_material ON public.supplier_price_history USING btree (material_id);


--
-- Name: ix_sph_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sph_supplier ON public.supplier_price_history USING btree (supplier_id);


--
-- Name: ix_sq_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sq_status ON public.supplier_quotations USING btree (status);


--
-- Name: ix_sq_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sq_supplier ON public.supplier_quotations USING btree (supplier_id);


--
-- Name: ix_stock_levels_loc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stock_levels_loc ON public.stock_levels USING btree (location_id);


--
-- Name: ix_stock_levels_tenant_mat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stock_levels_tenant_mat ON public.stock_levels USING btree (tenant_id, material_id);


--
-- Name: ix_stock_res_tenant_mat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stock_res_tenant_mat ON public.stock_reservations USING btree (tenant_id, material_id);


--
-- Name: ix_stock_res_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stock_res_tenant_status ON public.stock_reservations USING btree (tenant_id, status);


--
-- Name: ix_subco_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subco_supplier ON public.subcontract_orders USING btree (supplier_id);


--
-- Name: ix_supplier_invoices_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_invoices_status ON public.supplier_invoices USING btree (status);


--
-- Name: ix_supplier_invoices_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_invoices_supplier ON public.supplier_invoices USING btree (supplier_id);


--
-- Name: ix_supplier_invoices_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_invoices_tenant ON public.supplier_invoices USING btree (tenant_id);


--
-- Name: ix_supplier_payments_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_payments_supplier ON public.supplier_payments USING btree (supplier_id);


--
-- Name: ix_supplier_payments_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_payments_tenant ON public.supplier_payments USING btree (tenant_id);


--
-- Name: ix_supplier_price_history_material; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_price_history_material ON public.supplier_price_history USING btree (material_id);


--
-- Name: ix_supplier_price_history_tenant_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_supplier_price_history_tenant_supplier ON public.supplier_price_history USING btree (tenant_id, supplier_id);


--
-- Name: ix_suppliers_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_suppliers_active ON public.suppliers USING btree (tenant_id, is_active) WHERE (is_deleted = false);


--
-- Name: ix_suppliers_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_suppliers_tenant ON public.suppliers USING btree (tenant_id);


--
-- Name: ix_technical_documents_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_documents_tenant_id ON public.technical_documents USING btree (tenant_id);


--
-- Name: ix_tenant_finance_settings_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_finance_settings_tenant ON public.tenant_finance_settings USING btree (tenant_id);


--
-- Name: ix_tenant_role_permissions_permission; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_role_permissions_permission ON public.tenant_role_permissions USING btree (permission);


--
-- Name: ix_tenant_role_permissions_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_role_permissions_role_id ON public.tenant_role_permissions USING btree (role_id);


--
-- Name: ix_tenant_roles_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_roles_name ON public.tenant_roles USING btree (name);


--
-- Name: ix_tenant_roles_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_roles_tenant_id ON public.tenant_roles USING btree (tenant_id);


--
-- Name: ix_tenants_is_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenants_is_deleted ON public.tenants USING btree (is_deleted);


--
-- Name: ix_tenants_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_tenants_slug ON public.tenants USING btree (slug);


--
-- Name: ix_units_of_measure_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_units_of_measure_tenant_id ON public.units_of_measure USING btree (tenant_id);


--
-- Name: ix_uom_conversions_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uom_conversions_tenant_id ON public.uom_conversions USING btree (tenant_id);


--
-- Name: ix_user_devices_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_devices_tenant ON public.user_devices USING btree (tenant_id);


--
-- Name: ix_user_devices_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_devices_user ON public.user_devices USING btree (user_id);


--
-- Name: ix_users_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_client_id ON public.users USING btree (client_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_is_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_is_deleted ON public.users USING btree (is_deleted);


--
-- Name: ix_users_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_supplier ON public.users USING btree (supplier_id) WHERE (supplier_id IS NOT NULL);


--
-- Name: ix_users_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_tenant_id ON public.users USING btree (tenant_id);


--
-- Name: ix_wh_zone_tenant_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wh_zone_tenant_location ON public.warehouse_zones USING btree (tenant_id, warehouse_location_id);


--
-- Name: ix_wo_materials_work_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_wo_materials_work_order_id ON public.work_order_materials USING btree (work_order_id);


--
-- Name: ix_work_order_materials_work_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_work_order_materials_work_order_id ON public.work_order_materials USING btree (work_order_id);


--
-- Name: ix_work_orders_sales_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_work_orders_sales_order_id ON public.work_orders USING btree (sales_order_id);


--
-- Name: ix_work_orders_sales_order_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_work_orders_sales_order_line_id ON public.work_orders USING btree (sales_order_line_id);


--
-- Name: ix_work_orders_tenant_due; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_work_orders_tenant_due ON public.work_orders USING btree (tenant_id, due_date);


--
-- Name: ix_work_orders_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_work_orders_tenant_id ON public.work_orders USING btree (tenant_id);


--
-- Name: ix_work_orders_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_work_orders_tenant_status ON public.work_orders USING btree (tenant_id, status);


--
-- Name: ix_workstations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_workstations_tenant_id ON public.workstations USING btree (tenant_id);


--
-- Name: uq_locations_tenant_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_locations_tenant_code ON public.locations USING btree (tenant_id, code) WHERE ((code IS NOT NULL) AND (is_deleted = false));


--
-- Name: background_jobs background_jobs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.background_jobs
    ADD CONSTRAINT background_jobs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: batches batches_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id);


--
-- Name: batches batches_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id);


--
-- Name: bom_lines bom_lines_bom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_lines
    ADD CONSTRAINT bom_lines_bom_id_fkey FOREIGN KEY (bom_id) REFERENCES public.boms(id) ON DELETE CASCADE;


--
-- Name: bom_lines bom_lines_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_lines
    ADD CONSTRAINT bom_lines_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id);


--
-- Name: bom_lines bom_lines_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_lines
    ADD CONSTRAINT bom_lines_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.item_templates(id);


--
-- Name: bom_lines bom_lines_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_lines
    ADD CONSTRAINT bom_lines_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id);


--
-- Name: bom_lines bom_lines_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_lines
    ADD CONSTRAINT bom_lines_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.item_variants(id);


--
-- Name: bom_operations bom_operations_bom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_operations
    ADD CONSTRAINT bom_operations_bom_id_fkey FOREIGN KEY (bom_id) REFERENCES public.boms(id) ON DELETE CASCADE;


--
-- Name: bom_operations bom_operations_operation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bom_operations
    ADD CONSTRAINT bom_operations_operation_id_fkey FOREIGN KEY (operation_id) REFERENCES public.operations(id);


--
-- Name: boms boms_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boms
    ADD CONSTRAINT boms_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.item_templates(id);


--
-- Name: boms boms_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boms
    ADD CONSTRAINT boms_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.item_variants(id);


--
-- Name: chart_of_accounts chart_of_accounts_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chart_of_accounts
    ADD CONSTRAINT chart_of_accounts_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: client_addresses client_addresses_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_addresses
    ADD CONSTRAINT client_addresses_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.sales_clients(id) ON DELETE CASCADE;


--
-- Name: client_notification_settings client_notification_settings_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_notification_settings
    ADD CONSTRAINT client_notification_settings_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.sales_clients(id) ON DELETE CASCADE;


--
-- Name: client_notification_settings client_notification_settings_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_notification_settings
    ADD CONSTRAINT client_notification_settings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: client_notification_settings client_notification_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_notification_settings
    ADD CONSTRAINT client_notification_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: dashboard_metrics dashboard_metrics_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboard_metrics
    ADD CONSTRAINT dashboard_metrics_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: delivery_lines delivery_lines_delivery_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_lines
    ADD CONSTRAINT delivery_lines_delivery_order_id_fkey FOREIGN KEY (delivery_order_id) REFERENCES public.delivery_orders(id) ON DELETE CASCADE;


--
-- Name: delivery_lines delivery_lines_sales_order_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_lines
    ADD CONSTRAINT delivery_lines_sales_order_line_id_fkey FOREIGN KEY (sales_order_line_id) REFERENCES public.sales_order_lines(id) ON DELETE RESTRICT;


--
-- Name: delivery_lines delivery_lines_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_lines
    ADD CONSTRAINT delivery_lines_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: delivery_orders delivery_orders_cancelled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_orders
    ADD CONSTRAINT delivery_orders_cancelled_by_fkey FOREIGN KEY (cancelled_by) REFERENCES public.users(id);


--
-- Name: delivery_orders delivery_orders_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_orders
    ADD CONSTRAINT delivery_orders_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: delivery_orders delivery_orders_sales_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_orders
    ADD CONSTRAINT delivery_orders_sales_order_id_fkey FOREIGN KEY (sales_order_id) REFERENCES public.sales_orders(id) ON DELETE RESTRICT;


--
-- Name: delivery_orders delivery_orders_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delivery_orders
    ADD CONSTRAINT delivery_orders_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: document_associations document_associations_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_associations
    ADD CONSTRAINT document_associations_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.document_revisions(id) ON DELETE RESTRICT;


--
-- Name: document_associations document_associations_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_associations
    ADD CONSTRAINT document_associations_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.item_templates(id) ON DELETE CASCADE;


--
-- Name: document_associations document_associations_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_associations
    ADD CONSTRAINT document_associations_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.item_variants(id) ON DELETE CASCADE;


--
-- Name: document_associations document_associations_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_associations
    ADD CONSTRAINT document_associations_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE;


--
-- Name: document_revisions document_revisions_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_revisions
    ADD CONSTRAINT document_revisions_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: document_revisions document_revisions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_revisions
    ADD CONSTRAINT document_revisions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.technical_documents(id) ON DELETE CASCADE;


--
-- Name: document_revisions document_revisions_file_attachment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_revisions
    ADD CONSTRAINT document_revisions_file_attachment_id_fkey FOREIGN KEY (file_attachment_id) REFERENCES public.file_attachments(id) ON DELETE RESTRICT;


--
-- Name: documents documents_generated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_generated_by_fkey FOREIGN KEY (generated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: documents documents_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: failed_tasks failed_tasks_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_tasks
    ADD CONSTRAINT failed_tasks_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: file_attachments file_attachments_uploaded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_attachments
    ADD CONSTRAINT file_attachments_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id);


--
-- Name: financial_transactions financial_transactions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.financial_transactions
    ADD CONSTRAINT financial_transactions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: financial_transactions financial_transactions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.financial_transactions
    ADD CONSTRAINT financial_transactions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: materials fk_materials_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT fk_materials_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: materials fk_materials_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT fk_materials_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: sales_orders fk_sales_orders_approver_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_orders
    ADD CONSTRAINT fk_sales_orders_approver_id_users FOREIGN KEY (approver_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: suppliers fk_suppliers_created_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT fk_suppliers_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: suppliers fk_suppliers_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT fk_suppliers_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: users fk_users_client_id_sales_clients; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_client_id_sales_clients FOREIGN KEY (client_id) REFERENCES public.sales_clients(id) ON DELETE SET NULL;


--
-- Name: goods_receipt_notes goods_receipt_notes_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: goods_receipt_notes goods_receipt_notes_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES public.purchase_orders(id) ON DELETE RESTRICT;


--
-- Name: goods_receipt_notes goods_receipt_notes_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: goods_receipt_notes goods_receipt_notes_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: goods_receipt_notes goods_receipt_notes_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: goods_receipt_notes goods_receipt_notes_warehouse_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goods_receipt_notes
    ADD CONSTRAINT goods_receipt_notes_warehouse_location_id_fkey FOREIGN KEY (warehouse_location_id) REFERENCES public.locations(id) ON DELETE SET NULL;


--
-- Name: grn_lines grn_lines_grn_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grn_lines
    ADD CONSTRAINT grn_lines_grn_id_fkey FOREIGN KEY (grn_id) REFERENCES public.goods_receipt_notes(id) ON DELETE CASCADE;


--
-- Name: grn_lines grn_lines_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grn_lines
    ADD CONSTRAINT grn_lines_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: grn_lines grn_lines_po_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grn_lines
    ADD CONSTRAINT grn_lines_po_line_id_fkey FOREIGN KEY (po_line_id) REFERENCES public.purchase_order_lines(id) ON DELETE RESTRICT;


--
-- Name: grn_lines grn_lines_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grn_lines
    ADD CONSTRAINT grn_lines_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: import_session_rows import_session_rows_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_session_rows
    ADD CONSTRAINT import_session_rows_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.import_sessions(id) ON DELETE CASCADE;


--
-- Name: import_sessions import_sessions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_sessions
    ADD CONSTRAINT import_sessions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: import_sessions import_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_sessions
    ADD CONSTRAINT import_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: inspection_details inspection_details_inspection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspection_details
    ADD CONSTRAINT inspection_details_inspection_id_fkey FOREIGN KEY (inspection_id) REFERENCES public.quality_inspections(id) ON DELETE CASCADE;


--
-- Name: inspection_details inspection_details_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspection_details
    ADD CONSTRAINT inspection_details_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: inspection_templates inspection_templates_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspection_templates
    ADD CONSTRAINT inspection_templates_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: inventory_reservations inventory_reservations_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_reservations
    ADD CONSTRAINT inventory_reservations_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batches(id) ON DELETE SET NULL;


--
-- Name: inventory_reservations inventory_reservations_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_reservations
    ADD CONSTRAINT inventory_reservations_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: inventory_reservations inventory_reservations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_reservations
    ADD CONSTRAINT inventory_reservations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: inventory_reservations inventory_reservations_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_reservations
    ADD CONSTRAINT inventory_reservations_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id) ON DELETE SET NULL;


--
-- Name: inventory_transactions inventory_transactions_from_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_from_location_id_fkey FOREIGN KEY (from_location_id) REFERENCES public.locations(id);


--
-- Name: inventory_transactions inventory_transactions_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: inventory_transactions inventory_transactions_to_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_to_location_id_fkey FOREIGN KEY (to_location_id) REFERENCES public.locations(id);


--
-- Name: inventory_transactions inventory_transactions_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id);


--
-- Name: invoice_disputes invoice_disputes_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_disputes
    ADD CONSTRAINT invoice_disputes_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invoice_disputes invoice_disputes_supplier_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_disputes
    ADD CONSTRAINT invoice_disputes_supplier_invoice_id_fkey FOREIGN KEY (supplier_invoice_id) REFERENCES public.supplier_invoices(id) ON DELETE CASCADE;


--
-- Name: invoice_disputes invoice_disputes_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_disputes
    ADD CONSTRAINT invoice_disputes_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: invoice_lines invoice_lines_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_lines
    ADD CONSTRAINT invoice_lines_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE CASCADE;


--
-- Name: invoice_lines invoice_lines_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_lines
    ADD CONSTRAINT invoice_lines_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: invoices invoices_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.sales_clients(id) ON DELETE RESTRICT;


--
-- Name: invoices invoices_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: invoices invoices_sales_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_sales_order_id_fkey FOREIGN KEY (sales_order_id) REFERENCES public.sales_orders(id) ON DELETE RESTRICT;


--
-- Name: invoices invoices_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: item_code_sequences item_code_sequences_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_code_sequences
    ADD CONSTRAINT item_code_sequences_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.material_categories(id) ON DELETE CASCADE;


--
-- Name: item_variants item_variants_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_variants
    ADD CONSTRAINT item_variants_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE SET NULL;


--
-- Name: item_variants item_variants_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_variants
    ADD CONSTRAINT item_variants_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.item_templates(id) ON DELETE CASCADE;


--
-- Name: job_cards job_cards_operation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_cards
    ADD CONSTRAINT job_cards_operation_id_fkey FOREIGN KEY (operation_id) REFERENCES public.operations(id) ON DELETE RESTRICT;


--
-- Name: job_cards job_cards_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_cards
    ADD CONSTRAINT job_cards_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE;


--
-- Name: journal_entries journal_entries_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_entries
    ADD CONSTRAINT journal_entries_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: journal_entries journal_entries_reverses_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_entries
    ADD CONSTRAINT journal_entries_reverses_entry_id_fkey FOREIGN KEY (reverses_entry_id) REFERENCES public.journal_entries(id) ON DELETE SET NULL;


--
-- Name: journal_entries journal_entries_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_entries
    ADD CONSTRAINT journal_entries_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: journal_lines journal_lines_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_lines
    ADD CONSTRAINT journal_lines_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.chart_of_accounts(id) ON DELETE RESTRICT;


--
-- Name: journal_lines journal_lines_journal_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.journal_lines
    ADD CONSTRAINT journal_lines_journal_entry_id_fkey FOREIGN KEY (journal_entry_id) REFERENCES public.journal_entries(id) ON DELETE CASCADE;


--
-- Name: locations locations_parent_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_parent_location_id_fkey FOREIGN KEY (parent_location_id) REFERENCES public.locations(id);


--
-- Name: material_consumption_records material_consumption_records_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_consumption_records
    ADD CONSTRAINT material_consumption_records_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: material_consumption_records material_consumption_records_production_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_consumption_records
    ADD CONSTRAINT material_consumption_records_production_record_id_fkey FOREIGN KEY (production_record_id) REFERENCES public.production_records(id) ON DELETE SET NULL;


--
-- Name: material_consumption_records material_consumption_records_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_consumption_records
    ADD CONSTRAINT material_consumption_records_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE;


--
-- Name: material_onboarding_rows material_onboarding_rows_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_onboarding_rows
    ADD CONSTRAINT material_onboarding_rows_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.material_onboarding_sessions(id) ON DELETE CASCADE;


--
-- Name: material_requests material_requests_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: material_shortages material_shortages_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_shortages
    ADD CONSTRAINT material_shortages_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: material_shortages material_shortages_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_shortages
    ADD CONSTRAINT material_shortages_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: material_shortages material_shortages_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_shortages
    ADD CONSTRAINT material_shortages_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: material_shortages material_shortages_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_shortages
    ADD CONSTRAINT material_shortages_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE;


--
-- Name: materials materials_base_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_base_unit_id_fkey FOREIGN KEY (base_unit_id) REFERENCES public.units_of_measure(id);


--
-- Name: materials materials_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.material_categories(id);


--
-- Name: materials materials_inspection_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_inspection_template_id_fkey FOREIGN KEY (inspection_template_id) REFERENCES public.inspection_templates(id);


--
-- Name: materials materials_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id);


--
-- Name: mrp_suggestions mrp_suggestions_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mrp_suggestions
    ADD CONSTRAINT mrp_suggestions_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id);


--
-- Name: non_conformance_reports non_conformance_reports_inspection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_conformance_reports
    ADD CONSTRAINT non_conformance_reports_inspection_id_fkey FOREIGN KEY (inspection_id) REFERENCES public.quality_inspections(id) ON DELETE SET NULL;


--
-- Name: non_conformance_reports non_conformance_reports_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.non_conformance_reports
    ADD CONSTRAINT non_conformance_reports_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: number_series_config number_series_config_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_config
    ADD CONSTRAINT number_series_config_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: number_series_prefixes number_series_prefixes_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.number_series_prefixes
    ADD CONSTRAINT number_series_prefixes_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: operations operations_workstation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operations
    ADD CONSTRAINT operations_workstation_id_fkey FOREIGN KEY (workstation_id) REFERENCES public.workstations(id);


--
-- Name: password_reset_tokens password_reset_tokens_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payments payments_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.sales_clients(id) ON DELETE RESTRICT;


--
-- Name: payments payments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: payments payments_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE RESTRICT;


--
-- Name: payments payments_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: pick_list_lines pick_list_lines_pick_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_list_lines
    ADD CONSTRAINT pick_list_lines_pick_list_id_fkey FOREIGN KEY (pick_list_id) REFERENCES public.pick_lists(id) ON DELETE CASCADE;


--
-- Name: pick_lists pick_lists_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pick_lists
    ADD CONSTRAINT pick_lists_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE;


--
-- Name: po_number_sequences po_number_sequences_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.po_number_sequences
    ADD CONSTRAINT po_number_sequences_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: production_records production_records_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_records
    ADD CONSTRAINT production_records_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE;


--
-- Name: purchase_order_lines purchase_order_lines_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: purchase_order_lines purchase_order_lines_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES public.purchase_orders(id) ON DELETE CASCADE;


--
-- Name: purchase_order_lines purchase_order_lines_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: purchase_orders purchase_orders_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT purchase_orders_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: purchase_orders purchase_orders_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT purchase_orders_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: purchase_orders purchase_orders_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_orders
    ADD CONSTRAINT purchase_orders_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: purchase_requisitions purchase_requisitions_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: purchase_requisitions purchase_requisitions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: purchase_requisitions purchase_requisitions_linked_po_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_linked_po_id_fkey FOREIGN KEY (linked_po_id) REFERENCES public.purchase_orders(id) ON DELETE SET NULL;


--
-- Name: purchase_requisitions purchase_requisitions_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: purchase_requisitions purchase_requisitions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: purchase_requisitions purchase_requisitions_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_requisitions
    ADD CONSTRAINT purchase_requisitions_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE SET NULL;


--
-- Name: quality_inspections quality_inspections_inspector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_inspections
    ADD CONSTRAINT quality_inspections_inspector_id_fkey FOREIGN KEY (inspector_id) REFERENCES public.users(id);


--
-- Name: quality_inspections quality_inspections_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quality_inspections
    ADD CONSTRAINT quality_inspections_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: quarantine_releases quarantine_releases_ncr_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_ncr_id_fkey FOREIGN KEY (ncr_id) REFERENCES public.non_conformance_reports(id) ON DELETE CASCADE;


--
-- Name: quarantine_releases quarantine_releases_new_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_new_location_id_fkey FOREIGN KEY (new_location_id) REFERENCES public.locations(id);


--
-- Name: quarantine_releases quarantine_releases_released_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_released_by_fkey FOREIGN KEY (released_by) REFERENCES public.users(id);


--
-- Name: quarantine_releases quarantine_releases_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_releases
    ADD CONSTRAINT quarantine_releases_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: report_executions report_executions_executed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_executions
    ADD CONSTRAINT report_executions_executed_by_fkey FOREIGN KEY (executed_by) REFERENCES public.users(id);


--
-- Name: report_executions report_executions_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_executions
    ADD CONSTRAINT report_executions_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.saved_reports(id);


--
-- Name: report_executions report_executions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_executions
    ADD CONSTRAINT report_executions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: report_schedules report_schedules_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_schedules
    ADD CONSTRAINT report_schedules_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: report_schedules report_schedules_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_schedules
    ADD CONSTRAINT report_schedules_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.saved_reports(id);


--
-- Name: report_schedules report_schedules_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_schedules
    ADD CONSTRAINT report_schedules_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: rfq_lines rfq_lines_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_lines
    ADD CONSTRAINT rfq_lines_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: rfq_lines rfq_lines_rfq_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_lines
    ADD CONSTRAINT rfq_lines_rfq_id_fkey FOREIGN KEY (rfq_id) REFERENCES public.rfqs(id) ON DELETE CASCADE;


--
-- Name: rfq_lines rfq_lines_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_lines
    ADD CONSTRAINT rfq_lines_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: rfq_number_sequences rfq_number_sequences_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_number_sequences
    ADD CONSTRAINT rfq_number_sequences_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: rfq_suppliers rfq_suppliers_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.supplier_quotations(id) ON DELETE SET NULL;


--
-- Name: rfq_suppliers rfq_suppliers_rfq_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_rfq_id_fkey FOREIGN KEY (rfq_id) REFERENCES public.rfqs(id) ON DELETE CASCADE;


--
-- Name: rfq_suppliers rfq_suppliers_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE;


--
-- Name: rfq_suppliers rfq_suppliers_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfq_suppliers
    ADD CONSTRAINT rfq_suppliers_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: rfqs rfqs_awarded_po_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_awarded_po_id_fkey FOREIGN KEY (awarded_po_id) REFERENCES public.purchase_orders(id) ON DELETE SET NULL;


--
-- Name: rfqs rfqs_awarded_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_awarded_supplier_id_fkey FOREIGN KEY (awarded_supplier_id) REFERENCES public.suppliers(id) ON DELETE SET NULL;


--
-- Name: rfqs rfqs_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: rfqs rfqs_material_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_material_request_id_fkey FOREIGN KEY (material_request_id) REFERENCES public.material_requests(id) ON DELETE SET NULL;


--
-- Name: rfqs rfqs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfqs
    ADD CONSTRAINT rfqs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: sales_clients sales_clients_default_price_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_clients
    ADD CONSTRAINT sales_clients_default_price_list_id_fkey FOREIGN KEY (default_price_list_id) REFERENCES public.sales_price_lists(id) ON DELETE SET NULL;


--
-- Name: sales_order_lines sales_order_lines_sales_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_order_lines
    ADD CONSTRAINT sales_order_lines_sales_order_id_fkey FOREIGN KEY (sales_order_id) REFERENCES public.sales_orders(id) ON DELETE CASCADE;


--
-- Name: sales_orders sales_orders_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_orders
    ADD CONSTRAINT sales_orders_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.sales_clients(id) ON DELETE RESTRICT;


--
-- Name: sales_price_list_lines sales_price_list_lines_price_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_price_list_lines
    ADD CONSTRAINT sales_price_list_lines_price_list_id_fkey FOREIGN KEY (price_list_id) REFERENCES public.sales_price_lists(id) ON DELETE CASCADE;


--
-- Name: saved_reports saved_reports_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_reports
    ADD CONSTRAINT saved_reports_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: saved_reports saved_reports_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_reports
    ADD CONSTRAINT saved_reports_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: serial_numbers serial_numbers_current_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.serial_numbers
    ADD CONSTRAINT serial_numbers_current_location_id_fkey FOREIGN KEY (current_location_id) REFERENCES public.locations(id);


--
-- Name: serial_numbers serial_numbers_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.serial_numbers
    ADD CONSTRAINT serial_numbers_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id);


--
-- Name: stock_ledger_entries stock_ledger_entries_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_ledger_entries
    ADD CONSTRAINT stock_ledger_entries_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id);


--
-- Name: stock_ledger_entries stock_ledger_entries_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_ledger_entries
    ADD CONSTRAINT stock_ledger_entries_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id);


--
-- Name: stock_levels stock_levels_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT stock_levels_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE RESTRICT;


--
-- Name: stock_levels stock_levels_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT stock_levels_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE CASCADE;


--
-- Name: stock_levels stock_levels_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT stock_levels_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: stock_reservations stock_reservations_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_reservations
    ADD CONSTRAINT stock_reservations_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id);


--
-- Name: stock_reservations stock_reservations_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_reservations
    ADD CONSTRAINT stock_reservations_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id);


--
-- Name: subcontract_material_issues subcontract_material_issues_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_material_issues
    ADD CONSTRAINT subcontract_material_issues_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batches(id) ON DELETE SET NULL;


--
-- Name: subcontract_material_issues subcontract_material_issues_from_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_material_issues
    ADD CONSTRAINT subcontract_material_issues_from_location_id_fkey FOREIGN KEY (from_location_id) REFERENCES public.locations(id) ON DELETE SET NULL;


--
-- Name: subcontract_material_issues subcontract_material_issues_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_material_issues
    ADD CONSTRAINT subcontract_material_issues_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: subcontract_material_issues subcontract_material_issues_subcontract_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_material_issues
    ADD CONSTRAINT subcontract_material_issues_subcontract_order_id_fkey FOREIGN KEY (subcontract_order_id) REFERENCES public.subcontract_orders(id) ON DELETE CASCADE;


--
-- Name: subcontract_material_issues subcontract_material_issues_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_material_issues
    ADD CONSTRAINT subcontract_material_issues_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: subcontract_number_sequences subcontract_number_sequences_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_number_sequences
    ADD CONSTRAINT subcontract_number_sequences_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: subcontract_order_lines subcontract_order_lines_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_order_lines
    ADD CONSTRAINT subcontract_order_lines_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: subcontract_order_lines subcontract_order_lines_subcontract_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_order_lines
    ADD CONSTRAINT subcontract_order_lines_subcontract_order_id_fkey FOREIGN KEY (subcontract_order_id) REFERENCES public.subcontract_orders(id) ON DELETE CASCADE;


--
-- Name: subcontract_orders subcontract_orders_bom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_orders
    ADD CONSTRAINT subcontract_orders_bom_id_fkey FOREIGN KEY (bom_id) REFERENCES public.boms(id) ON DELETE SET NULL;


--
-- Name: subcontract_orders subcontract_orders_output_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_orders
    ADD CONSTRAINT subcontract_orders_output_batch_id_fkey FOREIGN KEY (output_batch_id) REFERENCES public.batches(id) ON DELETE SET NULL;


--
-- Name: subcontract_orders subcontract_orders_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_orders
    ADD CONSTRAINT subcontract_orders_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: subcontract_orders subcontract_orders_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subcontract_orders
    ADD CONSTRAINT subcontract_orders_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: supplier_invoices supplier_invoices_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT supplier_invoices_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: supplier_invoices supplier_invoices_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT supplier_invoices_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES public.purchase_orders(id) ON DELETE RESTRICT;


--
-- Name: supplier_invoices supplier_invoices_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT supplier_invoices_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: supplier_invoices supplier_invoices_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_invoices
    ADD CONSTRAINT supplier_invoices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: supplier_payments supplier_payments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_payments
    ADD CONSTRAINT supplier_payments_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: supplier_payments supplier_payments_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_payments
    ADD CONSTRAINT supplier_payments_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE RESTRICT;


--
-- Name: supplier_payments supplier_payments_supplier_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_payments
    ADD CONSTRAINT supplier_payments_supplier_invoice_id_fkey FOREIGN KEY (supplier_invoice_id) REFERENCES public.supplier_invoices(id) ON DELETE RESTRICT;


--
-- Name: supplier_payments supplier_payments_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_payments
    ADD CONSTRAINT supplier_payments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: supplier_price_history supplier_price_history_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_price_history
    ADD CONSTRAINT supplier_price_history_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE CASCADE;


--
-- Name: supplier_price_history supplier_price_history_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_price_history
    ADD CONSTRAINT supplier_price_history_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE;


--
-- Name: supplier_price_history supplier_price_history_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_price_history
    ADD CONSTRAINT supplier_price_history_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: supplier_quotations supplier_quotations_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT supplier_quotations_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: supplier_quotations supplier_quotations_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT supplier_quotations_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES public.purchase_orders(id) ON DELETE SET NULL;


--
-- Name: supplier_quotations supplier_quotations_rfq_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT supplier_quotations_rfq_id_fkey FOREIGN KEY (rfq_id) REFERENCES public.rfqs(id) ON DELETE SET NULL;


--
-- Name: supplier_quotations supplier_quotations_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT supplier_quotations_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE;


--
-- Name: supplier_quotations supplier_quotations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supplier_quotations
    ADD CONSTRAINT supplier_quotations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: suppliers suppliers_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: tenant_audit_logs tenant_audit_logs_acted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_audit_logs
    ADD CONSTRAINT tenant_audit_logs_acted_by_fkey FOREIGN KEY (acted_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: tenant_audit_logs tenant_audit_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_audit_logs
    ADD CONSTRAINT tenant_audit_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: tenant_finance_settings tenant_finance_settings_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_finance_settings
    ADD CONSTRAINT tenant_finance_settings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: tenant_role_permissions tenant_role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_role_permissions
    ADD CONSTRAINT tenant_role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.tenant_roles(id) ON DELETE CASCADE;


--
-- Name: tenant_roles tenant_roles_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_roles
    ADD CONSTRAINT tenant_roles_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: uom_conversions uom_conversions_from_uom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uom_conversions
    ADD CONSTRAINT uom_conversions_from_uom_id_fkey FOREIGN KEY (from_uom_id) REFERENCES public.units_of_measure(id);


--
-- Name: uom_conversions uom_conversions_to_uom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uom_conversions
    ADD CONSTRAINT uom_conversions_to_uom_id_fkey FOREIGN KEY (to_uom_id) REFERENCES public.units_of_measure(id);


--
-- Name: user_devices user_devices_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_devices
    ADD CONSTRAINT user_devices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: user_devices user_devices_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_devices
    ADD CONSTRAINT user_devices_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: users users_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE SET NULL;


--
-- Name: users users_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: warehouse_zones warehouse_zones_warehouse_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_zones
    ADD CONSTRAINT warehouse_zones_warehouse_location_id_fkey FOREIGN KEY (warehouse_location_id) REFERENCES public.locations(id);


--
-- Name: work_order_materials work_order_materials_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_materials
    ADD CONSTRAINT work_order_materials_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: work_order_materials work_order_materials_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_materials
    ADD CONSTRAINT work_order_materials_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units_of_measure(id);


--
-- Name: work_order_materials work_order_materials_work_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_materials
    ADD CONSTRAINT work_order_materials_work_order_id_fkey FOREIGN KEY (work_order_id) REFERENCES public.work_orders(id) ON DELETE CASCADE;


--
-- Name: work_orders work_orders_bom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT work_orders_bom_id_fkey FOREIGN KEY (bom_id) REFERENCES public.boms(id) ON DELETE RESTRICT;


--
-- Name: work_orders work_orders_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT work_orders_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.item_variants(id) ON DELETE RESTRICT;


--
-- Name: work_orders work_orders_sales_order_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT work_orders_sales_order_line_id_fkey FOREIGN KEY (sales_order_line_id) REFERENCES public.sales_order_lines(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

