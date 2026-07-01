import { apiClient } from './api-client'

export type OnboardingPreviewRow = {
  id: string
  row_number: number
  classification: string
  status: string
  data: Record<string, any>
  issues: Array<{ field: string; severity: string; message: string }>
  protected_changes: Array<{ field: string; from: string; to: string }>
}

export type OnboardingPreview = {
  summary: Record<string, number>
  rows: OnboardingPreviewRow[]
}

export const rawMaterialOnboardingColumns = [
  'item_code', 'material_name', 'material_category', 'material_type', 'uom',
  'batch_tracking_enabled', 'shelf_life', 'expiry_tracking', 'warehouse', 'zone', 'rack_bin',
  'min_stock', 'max_stock', 'reorder_level', 'reorder_quantity', 'opening_stock', 'barcode', 'traceability_enabled',
  'qc_required', 'approved_supplier', 'supplier_item_code', 'purchase_uom', 'lead_time', 'moq',
  'length_uom', 'cuttable_inventory', 'remaining_quantity_tracking', 'decimal_precision', 'reusable_remainder',
]

function csvTemplateUrl() {
  const csv = `${rawMaterialOnboardingColumns.join(',')}\n`
  return `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`
}

export const materialOnboardingService = {
  templateUrl: (format: 'csv' | 'xlsx') =>
    format === 'csv' ? csvTemplateUrl() : `/api/v1/inventory/material-onboarding/template?format=${format}`,
  backendRoutesAvailable: async () => {
    try {
      const response = await fetch('/api/v1/inventory/material-onboarding/template?format=xlsx', { method: 'GET' })
      return response.ok
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
    apiClient.post(`/inventory/material-onboarding/sessions/${sessionId}/execute`, { dry_run: dryRun }),
  updateRow: (rowId: string, data: Record<string, any>) =>
    apiClient.patch(`/inventory/material-onboarding/rows/${rowId}`, data),
  validationReport: (sessionId: string) =>
    apiClient.get(`/inventory/material-onboarding/sessions/${sessionId}/validation-report`, { responseType: 'blob' }),
}
