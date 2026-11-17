import { apiClient } from '@/services/api-client'

export type OnboardingPreviewRow = {
  id: string
  row_number: number
  classification: string
  status: string
  data: Record<string, string>
  issues: Array<{ field: string; severity: string; message: string }>
  protected_changes: Array<{ field: string; from: string; to: string }>
}

export type OnboardingPreview = {
  summary: {
    total_rows: number; new: number; update: number; skip: number; errors: number; warnings: number
    supplier_pricing: { supplier_agreements_draft: number; cost_revisions_pending: number; standard_costs_initialized: number }
  }
  warnings: string[]
  error_messages: string[]
  cost_outcomes: OnboardingCostOutcome[]
  rows: OnboardingPreviewRow[]
}

export interface OnboardingCostOutcome {
  material_id: string
  material_name: string
  status: 'CONFIGURED' | 'NOT_CONFIGURED'
  standard_cost: string | null
  message: string
}

export interface OnboardingExecution {
  dry_run: boolean
  created: number
  updated: number
  skipped: number
  rejected: number
  errors: number
  error_messages: string[]
  warnings: string[]
  cost_outcomes: OnboardingCostOutcome[]
  skip_details: Array<{ row: number; material_name: string; item_code: string; supplier_name?: string; reason: string; details?: string }>
  supplier_pricing_created: { supplier_agreements_draft: number; cost_revisions_pending: number; standard_costs_initialized: number }
}

export const rawMaterialOnboardingColumns = [
  'item_code', 'material_name', 'material_category', 'material_type', 'uom',
  'batch_tracking_enabled', 'shelf_life', 'expiry_tracking', 'storage_location', 'zone', 'rack_bin',
  'min_stock', 'max_stock', 'reorder_level', 'reorder_quantity', 'opening_stock', 'barcode', 'traceability_enabled',
  'qc_required', 'approved_supplier', 'supplier_item_code', 'purchase_uom', 'lead_time', 'moq',
  'length_uom', 'cuttable_inventory', 'remaining_quantity_tracking', 'decimal_precision', 'reusable_remainder',
  // === SUPPLIER PRICING FIELDS (Phase 2) ===
  'supplier_name', 'supplier_price', 'supplier_currency', 'supplier_moq', 'supplier_uom',
  'effective_from_date', 'effective_to_date', 'proposed_initial_cost',
]

export const friendlyColumnNames: Record<string, string> = {
  item_code: 'Item Code',
  material_name: 'Material Name',
  material_category: 'Category',
  material_type: 'Material Type',
  uom: 'Base Unit',
  barcode: 'Barcode',
  storage_location: 'Storage Location',
  zone: 'Zone',
  rack_bin: 'Rack / Bin',
  opening_stock: 'Opening Stock',
  min_stock: 'Minimum Stock',
  max_stock: 'Maximum Stock',
  reorder_level: 'Reorder Level',
  reorder_quantity: 'Reorder Quantity',
  batch_tracking_enabled: 'Track by Batch?',
  expiry_tracking: 'Track Expiry?',
  shelf_life: 'Shelf Life',
  traceability_enabled: 'Track Traceability?',
  qc_required: 'Quality Check Required?',
  approved_supplier: 'Preferred Supplier',
  supplier_item_code: 'Supplier Item Code',
  purchase_uom: 'Purchase Unit',
  lead_time: 'Lead Time (Days)',
  moq: 'Minimum Order Quantity',
  length_uom: 'Length Unit',
  cuttable_inventory: 'Can Be Cut?',
  remaining_quantity_tracking: 'Track Remaining Quantity?',
  decimal_precision: 'Decimal Places',
  reusable_remainder: 'Reuse Remaining Material?',
  // === SUPPLIER PRICING FIELDS (Phase 2) ===
  supplier_name: 'Supplier Name',
  supplier_price: 'Supplier Price',
  supplier_currency: 'Supplier Currency',
  supplier_moq: 'Supplier MOQ',
  supplier_uom: 'Supplier UOM',
  effective_from_date: 'Effective From',
  effective_to_date: 'Effective To',
  proposed_initial_cost: 'Proposed Initial Cost',
}


export const materialOnboardingService = {
  downloadTemplate: async (format: 'csv' | 'xlsx') => {
    const res = await apiClient.get(`/inventory/material-onboarding/template?format=${format}`, {
      responseType: 'blob'
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `material-onboarding-template.${format}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  backendRoutesAvailable: async () => {
    try {
      await apiClient.get('/inventory/material-onboarding/template?format=csv', { responseType: 'blob' })
      return true
    } catch {
      return false
    }
  },
  upload: (file: File) => {
    console.log('[Material Onboarding] Starting upload', {
      fileName: file.name,
      fileSize: file.size,
      timestamp: new Date().toISOString(),
    })

    const body = new FormData()
    body.append('file', file)
    return apiClient.post<{ session_id: string; headers: string[]; mapping: string }>('/inventory/material-onboarding/sessions', body)
  },
  validate: (sessionId: string, mapping: Record<string, string>) =>
    apiClient.post(`/inventory/material-onboarding/sessions/${sessionId}/validate`, { mapping }),
  preview: (sessionId: string) =>
    apiClient.get<OnboardingPreview>(`/inventory/material-onboarding/sessions/${sessionId}/preview`),
  confirmProtected: (sessionId: string) =>
    apiClient.post(`/inventory/material-onboarding/sessions/${sessionId}/confirm-protected`, {}),
  execute: (sessionId: string, dryRun: boolean) =>
    apiClient.post<OnboardingExecution>(`/inventory/material-onboarding/sessions/${sessionId}/execute`, { dry_run: dryRun }),
  updateRow: (rowId: string, data: Record<string, string>) =>
    apiClient.patch(`/inventory/material-onboarding/rows/${rowId}`, data),
  validationReport: (sessionId: string) =>
    apiClient.get(`/inventory/material-onboarding/sessions/${sessionId}/validation-report`, { responseType: 'blob' }),
}
