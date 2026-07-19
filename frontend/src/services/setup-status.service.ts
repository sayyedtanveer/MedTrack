import { apiClient } from "./api-client"

export interface CompanySetupStatusResponse {
  company: boolean
  numberSeries: boolean
  supplier: boolean
  customer: boolean
  material: boolean
  product: boolean
  bom: boolean
  openingStock: boolean
  progress: number
  units: boolean
  categories: boolean
  locations: boolean
  users: boolean
  readyToStart: boolean
}

export const setupStatusService = {
  async getStatus(): Promise<CompanySetupStatusResponse> {
    const response = await apiClient.get<CompanySetupStatusResponse>("/company/setup-status")
    return response.data
  },
}
