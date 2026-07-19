/**
 * Tenant profile types — corresponds to TenantResponse and UpdateTenantRequest
 * in backend/app/interfaces/api/v1/schemas/tenant_schemas.py
 */

export interface TenantProfile {
  /** Tenant UUID (read-only) */
  id: string;
  /** Internal tenant name / slug label (read-only) */
  name: string;
  /** URL-safe slug (read-only) */
  slug: string;
  /** Subscription plan (read-only) */
  plan: string;
  /** Whether the tenant account is active (read-only) */
  is_active: boolean;

  // ── Editable profile fields (all optional / nullable) ─────────────────────
  /** Legal company name shown on invoices and documents */
  company_name?: string | null;
  /** GST registration number */
  gst_number?: string | null;
  /** Company mailing / registered address */
  address?: string | null;
  /** Primary contact phone number */
  phone?: string | null;
  /** Primary contact email address */
  email?: string | null;
  /** URL to the company logo used on printed documents */
  logo_url?: string | null;
  /** Footer text printed at the bottom of invoices and delivery notes */
  footer_text?: string | null;
  /** ISO 4217 currency code (e.g. "INR", "USD") */
  currency_code?: string | null;
  /** Currency symbol displayed in the UI (e.g. "₹", "$") */
  currency_symbol?: string | null;
  /** IANA timezone identifier (e.g. "Asia/Kolkata") */
  timezone?: string | null;
  /** Default warehouse / storage location name */
  default_warehouse_name?: string | null;
}

/** Partial update payload — mirrors UpdateTenantRequest on the backend */
export type UpdateTenantPayload = Omit<TenantProfile, 'id' | 'name' | 'slug' | 'plan' | 'is_active'>;
