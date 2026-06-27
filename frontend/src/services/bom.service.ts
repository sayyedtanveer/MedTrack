import { apiClient } from "./api-client";
import {
  BOM,
  BOMListResponse,
  BOMCostResponse,
  BOMTreeNode,
  CreateBOMInput,
  AttachOperationInput,
  ItemTemplate,
  ItemTemplateListResponse,
  ItemVariant,
  ItemVariantListResponse,
  Operation,
  Workstation,
} from "@/types/bom.types";
import { Material } from "@/types/material.types";

export const bomService = {
  // ── BOMs ───────────────────────────────────────────────────────────────────

  async getBOMsForProduct(
    productId: string,
    isTemplate: boolean,
    params: { page?: number; page_size?: number } = {}
  ): Promise<BOMListResponse> {
    const { data } = await apiClient.get(`/products/${productId}/boms`, {
      params: { is_template: isTemplate, page: 1, page_size: 50, ...params },
    });
    return data;
  },

  async getBOM(bomId: string): Promise<BOM> {
    const { data } = await apiClient.get(`/boms/${bomId}`);
    return data;
  },

  async createBOM(productId: string, payload: CreateBOMInput): Promise<BOM> {
    const { data } = await apiClient.post(`/products/${productId}/boms`, payload);
    return data;  },

  async updateBOM(bomId: string, payload: Partial<CreateBOMInput>): Promise<BOM> {
    const { data } = await apiClient.put(`/boms/${bomId}`, payload);
    return data;
  },

  async activateBOM(bomId: string): Promise<BOM> {
    const { data } = await apiClient.post(`/boms/${bomId}/activate`);
    return data;
  },

  async copyBOM(bomId: string, newVersion: string): Promise<BOM> {
    const { data } = await apiClient.post(`/boms/${bomId}/copy`, { new_version: newVersion });
    return data;
  },

  async deleteBOM(bomId: string): Promise<void> {
    await apiClient.delete(`/boms/${bomId}`);
  },

  // ── BOM Tree (lazy per node) ───────────────────────────────────────────────

  async getBOMTree(bomId: string, params: { max_depth?: number; parent_id?: string } = {}): Promise<BOMTreeNode> {
    const { data } = await apiClient.get(`/boms/${bomId}/tree`, {
      params: { max_depth: 20, ...params },
    });
    return data;
  },

  // ── BOM Cost ───────────────────────────────────────────────────────────────

  async getBOMCost(bomId: string, maxDepth = 20): Promise<BOMCostResponse> {
    const { data } = await apiClient.get(`/boms/${bomId}/cost`, {
      params: { max_depth: maxDepth },
    });
    return data;
  },

  // ── BOM Operations ─────────────────────────────────────────────────────────

  async attachOperation(bomId: string, payload: AttachOperationInput): Promise<string> {
    const { data } = await apiClient.post(`/boms/${bomId}/operations`, payload);
    return data;
  },

  async removeOperation(bomId: string, bomOperationId: string): Promise<void> {
    await apiClient.delete(`/boms/${bomId}/operations/${bomOperationId}`);
  },

  // ── Products ───────────────────────────────────────────────────────────────

  async getTemplates(params: {
    query?: string;
    page?: number;
    page_size?: number;
  }): Promise<ItemTemplateListResponse> {
    const { data } = await apiClient.get("/products/templates", {
      params: { page: 1, page_size: 20, ...params },
    });
    return data;
  },

  async getTemplate(templateId: string): Promise<ItemTemplate> {
    const { data } = await apiClient.get(`/products/templates/${templateId}`);
    return data;
  },

  async getVariants(
    templateId: string,
    params: { query?: string; page?: number; page_size?: number } = {}
  ): Promise<ItemVariantListResponse> {
    const { data } = await apiClient.get(
      `/products/templates/${templateId}/variants`,
      { params: { page: 1, page_size: 20, ...params } }
    );
    return data;
  },

  async getAllVariants(params: {
    query?: string;
    page?: number;
    page_size?: number;
  }): Promise<ItemVariantListResponse> {
    // Fetch up to 10 templates concurrently, then flatten variants
    const tplRes = await bomService.getTemplates({ page_size: 100 })
    const topTemplates = tplRes.items.slice(0, 10)
    // Batch all variant requests concurrently (no sequential loop)
    const variantResults = await Promise.allSettled(
      topTemplates.map((tpl) => bomService.getVariants(tpl.id, { page_size: 50 }))
    )
    const allVariants: ItemVariant[] = variantResults.flatMap((r) =>
      r.status === "fulfilled" ? r.value.items : []
    )
    // Client-side filter by query
    const q = (params.query || "").toLowerCase()
    const filtered = q
      ? allVariants.filter(
          (v) =>
            v.name.toLowerCase().includes(q) ||
            v.code.toLowerCase().includes(q)
        )
      : allVariants
    return {
      items: filtered.slice(0, params.page_size ?? 20),
      total: filtered.length,
      page: 1,
      page_size: params.page_size ?? 20,
    }
  },

  // ── Workstations & Operations ──────────────────────────────────────────────

  async getWorkstations(): Promise<Workstation[]> {
    const { data } = await apiClient.get("/workstations/");
    return data;
  },

  async getOperations(): Promise<Operation[]> {
    const { data } = await apiClient.get("/operations/");
    return data;
  },

  // ── Materials (for component selector) ────────────────────────────────────

  async getMaterials(params: {
    query?: string;
    material_type?: "raw" | "finished";
    page?: number;
    page_size?: number;
  }): Promise<{ items: Material[]; total: number }> {
    const { data } = await apiClient.get("/inventory/materials", {
      params: { page: 1, page_size: 20, ...params },
    });
    return data;
  },
};
