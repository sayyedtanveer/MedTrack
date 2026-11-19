import apiClient from '@/services/api-client'

export interface ProductionCompletionItem {
  id: string
  wo_number: string
  product_id: string
  status: string
}

export interface ProductionCompletionResponse {
  items: ProductionCompletionItem[]
}

export const productionCompletion = {
  async get(orderId: string): Promise<ProductionCompletionResponse> {
    const { data } = await apiClient.get<ProductionCompletionResponse>(`/sales/orders/${orderId}/production-completion`)
    return data
  },
  async complete(orderId: string): Promise<ProductionCompletionResponse> {
    const { data } = await apiClient.post<ProductionCompletionResponse>(`/sales/orders/${orderId}/complete-production`)
    return data
  },
}
