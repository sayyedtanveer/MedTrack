import { apiClient as api } from "@/services/api-client";
import { Material } from "@/types/material.types";

export interface ListMaterialsRequest {
  page?: number;
  page_size?: number;
  query?: string;
  category?: string;
  material_type?: string;
  is_active?: boolean;
}

export interface ListMaterialsResponse {
  items: Material[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Material inventory API client
 * Handles material CRUD operations and queries
 */
export const materialApi = {
  /**
   * List all materials with optional filters
   * Includes cost_status in results for cost governance
   */
  async list(params?: ListMaterialsRequest): Promise<ListMaterialsResponse> {
    const response = await api.get<ListMaterialsResponse>(
      "/inventory/materials",
      {
        params: {
          page: params?.page || 1,
          page_size: params?.page_size || 20,
          query: params?.query,
          category: params?.category,
          material_type: params?.material_type,
          is_active: params?.is_active,
        },
      }
    );
    return response.data;
  },

  /**
   * Get a single material by ID
   */
  async get(materialId: string): Promise<Material> {
    const response = await api.get<Material>(
      `/inventory/materials/${materialId}`
    );
    return response.data;
  },

  /**
   * Create a new material
   */
  async create(data: any): Promise<Material> {
    const response = await api.post<Material>("/inventory/materials", data);
    return response.data;
  },

  /**
   * Update a material
   */
  async update(materialId: string, data: any): Promise<Material> {
    const response = await api.put<Material>(
      `/inventory/materials/${materialId}`,
      data
    );
    return response.data;
  },

  /**
   * Delete a material (soft delete)
   */
  async delete(materialId: string): Promise<void> {
    await api.delete(`/inventory/materials/${materialId}`);
  },
};
