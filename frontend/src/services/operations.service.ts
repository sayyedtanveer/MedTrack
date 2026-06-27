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

export interface CreateOperationInput {
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

export interface UpdateOperationInput extends Partial<CreateOperationInput> {}

export const operationsService = {
  /**
   * List all operations with optional filtering
   */
  async listOperations(): Promise<Operation[]> {
    const { data } = await apiClient.get("/manufacturing/operations")
    return data?.items || []
  },

  /**
   * Create new operation
   */
  async createOperation(payload: CreateOperationInput): Promise<Operation> {
    const { data } = await apiClient.post("/manufacturing/operations", payload)
    return data
  },

  /**
   * Update operation
   */
  async updateOperation(id: string, payload: UpdateOperationInput): Promise<Operation> {
    const { data } = await apiClient.put(`/manufacturing/operations/${id}`, payload)
    return data
  },

  /**
   * Delete operation
   */
  async deleteOperation(id: string): Promise<void> {
    await apiClient.delete(`/manufacturing/operations/${id}`)
  },
}
