import { apiClient } from './api-client'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface NumberSeriesConfig {
  id: string
  tenant_id: string
  entity_type: string
  auto_generate: boolean
  manual_override: 'never' | 'admin_only' | 'always'
  prefix: string
  include_abbreviation: boolean
  abbreviation_length: number
  sequence_length: number
  separator: string
  lock_after_save: boolean
  created_at: string
  updated_at: string
}

export interface NumberSeriesPrefix {
  id: string
  tenant_id: string
  entity_type: string
  sub_type: string
  prefix: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NumberSeriesAuditEntry {
  id: string
  tenant_id: string
  entity_type: string
  event_type: string
  entity_id: string | null
  generated_code: string | null
  old_value: string | null
  new_value: string | null
  user_id: string
  timestamp: string
  metadata_json: string | null
}

export interface AuditLogListResponse {
  items: NumberSeriesAuditEntry[]
  total: number
  page: number
  page_size: number
}

export interface CodePreviewResponse {
  preview: string
  format_pattern: string
}

// ── Service ───────────────────────────────────────────────────────────────────

export const numberSeriesService = {
  async listConfigs(): Promise<NumberSeriesConfig[]> {
    const { data } = await apiClient.get<NumberSeriesConfig[]>('/settings/number-series')
    return data
  },

  async getConfig(entityType: string): Promise<NumberSeriesConfig> {
    const { data } = await apiClient.get<NumberSeriesConfig>(`/settings/number-series/${entityType}`)
    return data
  },

  async updateConfig(entityType: string, payload: Partial<Omit<NumberSeriesConfig, 'id' | 'tenant_id' | 'entity_type' | 'created_at' | 'updated_at'>>): Promise<NumberSeriesConfig> {
    const { data } = await apiClient.put<NumberSeriesConfig>(`/settings/number-series/${entityType}`, payload)
    return data
  },

  async getPrefixes(entityType: string): Promise<NumberSeriesPrefix[]> {
    const { data } = await apiClient.get<NumberSeriesPrefix[]>(`/settings/number-series/${entityType}/prefixes`)
    return data
  },

  async updatePrefix(entityType: string, subType: string, prefix: string): Promise<NumberSeriesPrefix> {
    const { data } = await apiClient.put<NumberSeriesPrefix>(
      `/settings/number-series/${entityType}/prefixes/${subType}`,
      { prefix }
    )
    return data
  },

  async previewCode(entityType: string, subType?: string, entityName?: string): Promise<CodePreviewResponse> {
    const { data } = await apiClient.get<CodePreviewResponse>(`/settings/number-series/${entityType}/preview`, {
      params: { sub_type: subType, entity_name: entityName },
    })
    return data
  },

  async getAuditLog(params?: {
    entity_type?: string
    page?: number
    page_size?: number
  }): Promise<AuditLogListResponse> {
    const { data } = await apiClient.get<AuditLogListResponse>('/settings/number-series/audit-log', { params })
    return data
  },
}
