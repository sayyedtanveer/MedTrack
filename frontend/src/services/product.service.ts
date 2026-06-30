import { apiClient } from "./api-client";
import {
  ItemTemplate,
  ItemTemplateListResponse,
  ItemVariant,
  ItemVariantListResponse,
  ItemVariantSearchListResponse,
} from "@/types/bom.types";

export interface CreateTemplateInput {
  code?: string | null;
  item_code?: string | null;
  name: string;
  description?: string;
  category_id: string;
  base_unit_id?: string;
  attributes: { key: string; label: string; values?: string[] }[];
}

export interface UpdateTemplateInput extends Partial<CreateTemplateInput> {
  is_active?: boolean;
}

export interface CreateVariantInput {
  attribute_values: Record<string, string>;
  base_unit_id?: string;
  standard_cost: number;
  selling_price?: number;
}

export interface UpdateVariantInput {
  standard_cost?: number;
  selling_price?: number;
  is_active?: boolean;
}

export interface VariantImportTemplate {
  csv_content: string;
  file_name: string;
}

export interface VariantImportError {
  row_number: number;
  field: string;
  message: string;
}

export interface VariantImportResult {
  success_count: number;
  error_count: number;
  errors: VariantImportError[];
  variant_ids: string[];
  message: string;
}

export interface BulkOperationResult {
  success_count: number;
  message: string;
}

export interface ProductImageListResponse {
  items: {
    id: string;
    file_name: string;
    file_path: string;
    is_primary: boolean;
  }[];
  primary_image?: unknown;
}

export const productService = {
  // ── Templates ─────────────────────────────────────────────────────────────

  async getTemplates(params: {
    query?: string;
    category_id?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<ItemTemplateListResponse> {
    const { data } = await apiClient.get("/products/templates", { params });
    return data;
  },

  async getTemplate(id: string): Promise<ItemTemplate> {
    const { data } = await apiClient.get(`/products/templates/${id}`);
    return data;
  },

  async createTemplate(payload: CreateTemplateInput): Promise<ItemTemplate> {
    const { data } = await apiClient.post("/products/templates", payload);
    return data;
  },

  async updateTemplate(id: string, payload: UpdateTemplateInput): Promise<ItemTemplate> {
    const { data } = await apiClient.put(`/products/templates/${id}`, payload);
    return data;
  },

  // ── Variants ──────────────────────────────────────────────────────────────

  async getVariants(
    templateId: string,
    params: {
      query?: string;
      is_active?: boolean;
      page?: number;
      page_size?: number;
    }
  ): Promise<ItemVariantListResponse> {
    const { data } = await apiClient.get(`/products/templates/${templateId}/variants`, { params });
    return data;
  },

  async getVariant(id: string): Promise<ItemVariant> {
    const { data } = await apiClient.get(`/products/variants/${id}`);
    return data;
  },

  async createVariant(templateId: string, payload: CreateVariantInput): Promise<ItemVariant> {
    const { data } = await apiClient.post(`/products/templates/${templateId}/variants`, payload);
    return data;
  },

  async updateVariant(id: string, payload: UpdateVariantInput): Promise<ItemVariant> {
    const { data } = await apiClient.put(`/products/variants/${id}`, payload);
    return data;
  },

  async getTemplateImages(templateId: string): Promise<ProductImageListResponse> {
    const { data } = await apiClient.get(`/products/templates/${templateId}/images`);
    return data;
  },

  async uploadTemplateImage(templateId: string, file: File): Promise<{ message: string; image_id: string }> {
    const formData = new FormData()
    formData.append("file", file)
    const { data } = await apiClient.post(
      `/products/templates/${templateId}/images`,
      formData
    )
    return data
  },

  async uploadVariantImage(templateId: string, variantId: string, file: File): Promise<{ message: string; image_id: string }> {
    const formData = new FormData()
    formData.append("file", file)
    const { data } = await apiClient.post(
      `/products/variants/${variantId}/images`,
      formData,
      { params: { template_id: templateId } }
    )
    return data
  },

  async getImportTemplate(templateId: string): Promise<VariantImportTemplate> {
    const { data } = await apiClient.get(`/products/templates/${templateId}/variants/import-template`);
    return data;
  },

  async bulkImportVariants(
    templateId: string,
    payload: { csv_data: string }
  ): Promise<VariantImportResult> {
    const { data } = await apiClient.post(`/products/templates/${templateId}/variants/bulk-import`, payload);
    return data;
  },

  async bulkActivateVariants(templateId: string, variantIds: string[]): Promise<BulkOperationResult> {
    const { data } = await apiClient.post(`/products/templates/${templateId}/variants/bulk-activate`, {
      variant_ids: variantIds,
    });
    return data;
  },

  async bulkDeactivateVariants(templateId: string, variantIds: string[]): Promise<BulkOperationResult> {
    const { data } = await apiClient.post(`/products/templates/${templateId}/variants/bulk-deactivate`, {
      variant_ids: variantIds,
    });
    return data;
  },

  /** Tenant-wide variant search (for subcontract receive / FG selection) */
  async searchVariants(params: {
    search?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<ItemVariantSearchListResponse> {
    const { data } = await apiClient.get("/products/variants", { params });
    return data;
  },
};
