/**
 * Frontend service for Workstations API calls.
 */

import { apiClient } from "./api-client"

export interface Workstation {
  id: string
  code: string
  name: string
  capacity_hours_per_day: number
  hourly_rate: number
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface CreateWorkstationPayload {
  code: string
  name: string
  capacity_hours_per_day?: number
  hourly_rate?: number
}

export interface UpdateWorkstationPayload {
  code?: string
  name?: string
  capacity_hours_per_day?: number
  hourly_rate?: number
  is_active?: boolean
}

export const workstationsService = {
  /**
   * List all workstations for current tenant
   */
  async listWorkstations(): Promise<Workstation[]> {
    const { data } = await apiClient.get("/workstations")
    return data || []
  },

  /**
   * Get single workstation by ID
   */
  async getWorkstation(id: string): Promise<Workstation> {
    const { data } = await apiClient.get(`/workstations/${id}`)
    return data
  },

  /**
   * Create new workstation
   */
  async createWorkstation(payload: CreateWorkstationPayload): Promise<string> {
    const { data } = await apiClient.post("/workstations", payload)
    return data
  },

  /**
   * Update workstation
   */
  async updateWorkstation(id: string, payload: UpdateWorkstationPayload): Promise<Workstation> {
    const { data } = await apiClient.put(`/workstations/${id}`, payload)
    return data
  },

  /**
   * Delete workstation
   */
  async deleteWorkstation(id: string): Promise<void> {
    await apiClient.delete(`/workstations/${id}`)
  },
}
