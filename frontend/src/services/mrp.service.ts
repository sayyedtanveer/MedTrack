import { apiClient } from "./api-client"

// ── Types ──────────────────────────────────────────────────────────────────

export type WorkstationLoad = {
  workstation_id: string
  workstation_code: string
  workstation_name: string
  capacity_hours: number
  scheduled_hours: number
  load_pct: number
  status: "ok" | "warning" | "critical"
}

export type Bottleneck = WorkstationLoad & {
  overtime_hours_needed: number
  suggestion: string
  alert_level: "warning" | "critical"
}

export type GanttEntry = {
  id: string
  wo_number: string
  status: string
  priority: string
  start_date: string
  due_date: string
  planned_quantity: number
  produced_quantity: number
  progress_pct: number
}

export type MRPRunResult = {
  run_at: string
  suggestions_count: number
}

export type MRPSuggestion = {
  id: string
  material_id: string
  material_code: string
  material_name: string
  gross_requirement: number
  current_stock: number
  open_po_qty: number
  reserved_stock: number
  net_requirement: number
  suggested_qty: number
  lead_time_days: number
  order_by_date: string
  need_by_date: string
  supplier_id: string | null
  supplier_name: string
  status: "pending" | "approved" | "rejected" | "converted"
  created_at: string
  po_id?: string
}

export type CreatedPO = {
  po_id: string
  po_number: string
  lines: number
}

// Material request (purchase requisition) created from WO shortages
export type MaterialRequest = {
  id: string
  material_id: string
  material_code: string
  material_name: string
  required_quantity: number
  fulfilled_quantity: number
  shortage_quantity: number
  required_by: string | null
  status: "open" | "fulfilled" | "cancelled"
  source_ref_type: string | null
  source_ref_id: string | null
  created_at: string
}

// ── API ────────────────────────────────────────────────────────────────────

export const mrpApi = {
  // Capacity
  getLoadChart: (start?: string, end?: string) => {
    const params = new URLSearchParams()
    if (start) params.set("start", start)
    if (end) params.set("end", end)
    const qs = params.toString()
    return apiClient.get<WorkstationLoad[]>(`/capacity/load-chart${qs ? `?${qs}` : ""}`).then(res => res.data)
  },

  getBottlenecks: (threshold?: number) => {
    const qs = threshold !== undefined ? `?threshold=${threshold}` : ""
    return apiClient.get<Bottleneck[]>(`/capacity/bottlenecks${qs}`).then(res => res.data)
  },

  getSchedule: (start?: string, end?: string) => {
    const params = new URLSearchParams()
    if (start) params.set("start", start)
    if (end) params.set("end", end)
    const qs = params.toString()
    return apiClient.get<GanttEntry[]>(`/capacity/schedule${qs ? `?${qs}` : ""}`).then(res => res.data)
  },

  reschedule: (body: {
    work_order_id: string
    new_start: string
    new_due: string
    direction?: "forward" | "backward"
  }) => apiClient.post<GanttEntry>(`/capacity/schedule`, body).then(res => res.data),

  // MRP
  runMRP: () => apiClient.post<MRPRunResult>(`/mrp/run`, {}).then(res => res.data),

  getSuggestions: (status?: string) => {
    const qs = status ? `?status=${status}` : ""
    return apiClient.get<MRPSuggestion[]>(`/mrp/suggestions${qs}`).then(res => res.data)
  },

  approveSuggestion: (id: string) =>
    apiClient.post<MRPSuggestion>(`/mrp/suggestions/${id}/approve`, {}).then(res => res.data),

  rejectSuggestion: (id: string) =>
    apiClient.post<MRPSuggestion>(`/mrp/suggestions/${id}/reject`, {}).then(res => res.data),

  bulkApprove: (suggestion_ids: string[]) =>
    apiClient.post<{ approved: number }>(`/mrp/suggestions/bulk-approve`, { suggestion_ids }).then(res => res.data),

  convertToPO: (suggestion_ids?: string[]) =>
    apiClient.post<{ purchase_orders: CreatedPO[] }>(`/mrp/suggestions/convert-to-po`, {
      suggestion_ids: suggestion_ids ?? null,
    }).then(res => res.data),

  // Material Requests (purchase requisitions from WO shortages)
  getMaterialRequests: (status?: string) => {
    const qs = status ? `?status=${status}` : ""
    return apiClient.get<MaterialRequest[]>(`/mrp/material-requests${qs}`).then(res => res.data)
  },
}
