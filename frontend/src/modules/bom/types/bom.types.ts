// ─── BOM Types ────────────────────────────────────────────────────────────────

export interface BOMLine {
  id: string;
  bom_id: string;
  material_id: string | null;
  template_id: string | null;
  variant_id: string | null;
  quantity: number;
  scrap_percentage: number;
  unit_id: string | null;
}

export interface BOM {
  id: string;
  tenant_id: string;
  version: string;
  is_active: boolean;
  valid_from: string | null;
  valid_to: string | null;
  created_by: string | null;
  approved_by: string | null;
  template_id: string | null;
  variant_id: string | null;
  created_at: string;
  updated_at: string;
  operations_count: number;
  lines: BOMLine[];
  operations?: BOMOperation[];
  // Outside making charge (Phase: semi-finished making cost)
  making_charge?: number | null;
  making_charge_basis?: string | null;
}

export interface BOMListResponse {
  items: BOM[];
  total: number;
  page: number;
  page_size: number;
}

// ─── BOM Tree (multi-level) ───────────────────────────────────────────────────

export interface BOMTreeNode {
  id: string;
  name: string;
  code?: string;
  type: "material" | "template" | "variant";
  material_type?: "raw_material" | "raw" | "semi_finished" | "finished_good" | "finished";
  quantity: number;
  unit?: string;
  unit_id?: string;
  scrap_percentage?: number;
  cost?: number | null;
  line_id?: string;
  bom_id?: string;
  is_complete?: boolean;
  reason?: string;
  message?: string;
  cost_basis?: "STANDARD_COST" | "CHILD_BOM" | "UNRESOLVED";
  unit_cost?: number;
  component_material_cost?: number;
  operation_cost?: number;
  making_cost?: number;
  currency_code?: string;
  currency_symbol?: string;
  missing_costs?: MissingCostDetail[];
  depth: number;
  children: BOMTreeNode[];
  has_more?: boolean; // for lazy loading indicator
}

// ─── BOM Cost ─────────────────────────────────────────────────────────────────

export interface MissingCostDetail {
  component_type: "material" | "operation" | "bom";
  component_id: string;
  name: string;
  code?: string;
  quantity?: number;
  unit?: string;
  reason?: string;
  message?: string;
}

export interface BOMCostResponse {
  bom_id: string;
  material_cost: number;
  operation_cost: number;
  making_cost: number;
  total_cost: number;
  currency_code?: string;
  currency_symbol?: string;
  // Phase 2B: Cost completeness fields
  is_complete?: boolean;
  missing_costs?: MissingCostDetail[];
}

// ─── Operations & Workstations ────────────────────────────────────────────────

export interface Workstation {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  capacity_hours_per_day: number;
  hourly_rate: number;
  is_active: boolean;
}

export interface Operation {
  id: string;
  tenant_id: string;
  name: string;
  workstation_id: string | null;
  setup_time: number;
  run_time: number;
  description?: string;
  is_active: boolean;
}

export interface BOMOperation {
  id: string;
  bom_id: string;
  operation_id: string;
  sequence: number;
  // computed / joined fields (may not be from API directly)
  operation?: Operation;
  workstation?: Workstation;
}

// ─── Products ─────────────────────────────────────────────────────────────────

export interface ItemTemplate {
  id: string;
  tenant_id: string;
  code: string;
  item_code: string;
  item_type: "RAW" | "FG" | "SF" | string;
  name: string;
  description?: string;
  category_id?: string;
  base_unit_id?: string;
  attributes: { key: string; label: string; values?: string[] }[];
  code_locked: boolean;
  is_active: boolean;
}

export interface ItemVariant {
  id: string;
  tenant_id: string;
  template_id: string;
  code: string;
  name: string;
  variant_key: string;
  attribute_values: Record<string, string>;
  base_unit_id?: string;
  material_id?: string | null;
  standard_cost: number;
  selling_price?: number;
  is_active: boolean;
}

export interface ItemTemplateListResponse {
  items: ItemTemplate[];
  total: number;
  page: number;
  page_size: number;
}

export interface ItemVariantListResponse {
  items: ItemVariant[];
  total: number;
  page: number;
  page_size: number;
}

/** Global variant search (subcontract FG picker) */
export interface ItemVariantSearchItem extends ItemVariant {
  base_unit_code?: string | null;
  stock_material_id?: string | null;
}

export interface ItemVariantSearchListResponse {
  items: ItemVariantSearchItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Form Inputs ──────────────────────────────────────────────────────────────

export type ComponentType = "material" | "template" | "variant";

export interface BOMLineInput {
  material_id?: string;
  template_id?: string;
  variant_id?: string;
  quantity: number;
  scrap_percentage?: number;
  unit_id?: string;
}

export interface CreateBOMInput {
  version: string;
  valid_from?: string;
  valid_to?: string;
  template_id?: string;
  variant_id?: string;
  lines: BOMLineInput[];
}

export interface AttachOperationInput {
  operation_id: string;
  sequence: number;
}
