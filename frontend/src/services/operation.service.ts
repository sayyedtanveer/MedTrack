// Frontend service for Operation Master API calls.

import { apiClient } from "./api-client"

export interface Operation {
  id: string
  operation_code: string
  name: string
  operation_type: string
  description?: string
  default_sequence: number
  estimated_time_minutes?: number
  qc_required: boolean
  is_active: boolean
  color?: string
  icon_code?: string
  workstation_id?: string
  setup_time?: number
  run_time?: number
  created_at?: string
  updated_at?: string
}

export interface CreateOperationPayload {
  operation_code?: string
  name: string
  operation_type?: string
  description?: string
  default_sequence?: number
  estimated_time_minutes?: number
  qc_required?: boolean
  color?: string
  icon_code?: string
  workstation_id?: string
  setup_time?: number
  run_time?: number
}

export interface UpdateOperationPayload {
  name?: string
  description?: string
  default_sequence?: number
  estimated_time_minutes?: number
  qc_required?: boolean
  color?: string
  icon_code?: string
  is_active?: boolean
}

export const operationService = {
  /**
   * List all operations with optional filtering
   */
  async listOperations(params?: {
    query?: string
    operation_type?: string
    include_inactive?: boolean
  }): Promise<{ items: Operation[]; total: number }> {
    const { data } = await apiClient.get("/manufacturing/operations/", { params })
    return data
  },

  /**
   * List operations available for BOM attachment (active only)
   */
  async listOperationsForBOM(): Promise<{ items: Operation[]; total: number }> {
    const { data } = await apiClient.get("/manufacturing/operations/for-bom/")
    return data
  },

  /**
   * Get single operation by ID
   */
  async getOperation(id: string): Promise<Operation> {
    const { data } = await apiClient.get(`/manufacturing/operations/${id}`)
    return data
  },

  /**
   * Create new operation
   */
  async createOperation(payload: CreateOperationPayload): Promise<Operation> {
    const { data } = await apiClient.post("/manufacturing/operations", payload)
    return data
  },

  /**
   * Update operation
   */
  async updateOperation(id: string, payload: UpdateOperationPayload): Promise<Operation> {
    const { data } = await apiClient.put(`/manufacturing/operations/${id}`, payload)
    return data
  },

  /**
   * Delete (soft delete) operation
   */
  async deleteOperation(id: string): Promise<void> {
    await apiClient.delete(`/manufacturing/operations/${id}`)
  },

  /**
   * Deactivate operation
   */
  async deactivateOperation(id: string): Promise<Operation> {
    const { data } = await apiClient.post(`/manufacturing/operations/${id}/deactivate`)
    return data
  },

  /**
   * Reactivate operation
   */
  async reactivateOperation(id: string): Promise<Operation> {
    const { data } = await apiClient.post(`/manufacturing/operations/${id}/reactivate`)
    return data
  },
}
