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

