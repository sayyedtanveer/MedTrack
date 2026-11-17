/**
 * Procurement Pricing Module TypeScript Definitions
 * Phase 2e Frontend Integration
 */

/**
 * Supplier Price Agreement domain model
 */
export interface SupplierPriceAgreement {
  id: string;
  supplier_id: string;
  material_id: string;
  status: 'DRAFT' | 'PENDING' | 'APPROVED' | 'ACTIVE' | 'EXPIRED' | 'CANCELLED';
  base_price: number;
  currency_code: string;
  quantity_tiers: QuantityTier[] | null;
  purchase_uom_id: string | null;
  minimum_order_quantity: number | null;
  effective_from: string;
  effective_to: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Quantity tier pricing (for volume discounts)
 */
export interface QuantityTier {
  min_qty: number;
  max_qty: number | null;
  discount_percent: number;
}

/**
 * Standard Cost Revision (for material costing changes)
 */
export interface StandardCostRevision {
  id: string;
  material_id: string;
  requested_by: string;
  requested_cost: number;
  current_cost: number;
  variance_percent: number | null;
  reason: string;
  notes: string | null;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
}

/**
 * Material Cost History entry (append-only audit log)
 */
export interface MaterialCostHistory {
  id: string;
  material_id: string;
  old_cost: number | null;
  new_cost: number;
  change_type:
    | 'GRN_RECEIPT'
    | 'GRN_REVERSAL'
    | 'COST_REVISION_APPROVED'
    | 'COST_REVISION_REJECTED'
    | 'MANUAL_OVERRIDE'
    | 'INITIAL_SETUP'
    | 'DIRECT_REVISION';
  source_type: 'GRN' | 'PO_RECEIPT' | 'SUPPLIER_AGREEMENT' | 'MANUAL' | 'STANDARD_COST_REVISION';
  source_id: string | null;
  approved_by: string | null;
  notes: string | null;
  created_at: string;
}

/**
 * Price Override Record (when actual price differs from suggested price)
 */
export interface PriceOverrideRecord {
  id: string;
  material_id: string;
  grn_id: string | null;
  suggested_price: number;
  override_price: number;
  variance_percent: number | null;
  override_reason: 'QUALITY_ISSUE' | 'RUSH_ORDER' | 'BULK_DISCOUNT' | 'VENDOR_PREFERENCE' | 'OTHER';
  override_by: string;
  notes: string | null;
  created_at: string;
}

/**
 * Price Suggestion (algorithm-generated price recommendations)
 */
export interface PriceSuggestion {
  material_id: string;
  active_supplier_agreements: SupplierPriceAgreement[];
  weighted_average_price: number;
  moving_average_price: number;
  variance_from_grn: number;
  recommended_price: number;
  confidence_score: number;
  last_updated: string;
}

/**
 * Request DTOs for API
 */

export interface CreateSupplierPriceAgreementRequest {
  supplier_id: string;
  material_id: string;
  base_price: number;
  currency_code: string;
  quantity_tiers?: QuantityTier[];
  purchase_uom_id?: string;
  minimum_order_quantity?: number;
  effective_from: string;
  effective_to?: string | null;
  notes?: string;
}

export interface UpdateSupplierPriceAgreementRequest {
  base_price?: number;
  currency_code?: string;
  quantity_tiers?: QuantityTier[];
  purchase_uom_id?: string;
  minimum_order_quantity?: number;
  effective_to?: string | null;
  notes?: string;
}

export interface CreateStandardCostRevisionRequest {
  material_id: string;
  requested_cost: number;
  reason: 'GRN_VARIANCE' | 'SUPPLIER_AGREEMENT' | 'VARIANCE_THRESHOLD' | 'MANUAL_ADJUSTMENT';
  notes?: string;
}

export interface ApproveStandardCostRevisionRequest {
  revision_id: string;
}

export interface RejectStandardCostRevisionRequest {
  revision_id: string;
  rejection_reason: string;
}

export interface RecordPriceOverrideRequest {
  material_id: string;
  grn_id?: string;
  suggested_price: number;
  override_price: number;
  override_reason: 'QUALITY_ISSUE' | 'RUSH_ORDER' | 'BULK_DISCOUNT' | 'VENDOR_PREFERENCE' | 'OTHER';
  notes?: string;
}

/**
 * List/Query response types
 */

export interface ListSupplierPriceAgreementsResponse {
  items: SupplierPriceAgreement[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListPendingCostRevisionsResponse {
  items: StandardCostRevision[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListMaterialCostHistoryResponse {
  history: MaterialCostHistory[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListPriceOverridesResponse {
  overrides: PriceOverrideRecord[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * UI state types
 */

export interface PricingFilters {
  supplier_id?: string;
  material_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  page: number;
  page_size: number;
}

export interface PricingUIState {
  loading: boolean;
  error: string | null;
  selectedAgreement: SupplierPriceAgreement | null;
  selectedRevision: StandardCostRevision | null;
  showAgreementForm: boolean;
  showRevisionForm: boolean;
  showCostHistory: boolean;
}
