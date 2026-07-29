import { apiClient } from "./api-client";
import { 
  Material, 
  StockInfo, 
  InventoryTransaction, 
  Batch,
  CreateMaterialInput, 
  UpdateMaterialInput, 
  StockOperationInput,
  Category,
  Location,
  UnitOfMeasure,
  PurchaseHistoryPage,
} from "@/types/material.types";

export interface PaginatedMaterialsResponse {
  items: Material[];
  total: number;
  page: number;
  page_size: number;
}

export const materialService = {
  // ── Materials ───────────────────────────────────────────────────────────
  async getMaterials(params: {
    query?: string;
    category?: string;
    material_type?: "raw" | "finished";
    is_active?: boolean;
    page: number;
    page_size: number;
  }): Promise<PaginatedMaterialsResponse> {
    const { data } = await apiClient.get("/inventory/materials", { params });
    return data;
  },

  async getMaterial(id: string): Promise<Material> {
    const { data } = await apiClient.get(`/inventory/materials/${id}`);
    return data;
  },

  async createMaterial(payload: CreateMaterialInput): Promise<Material> {
    const { data } = await apiClient.post("/inventory/materials", payload);
    return data;
  },

  async updateMaterial(id: string, payload: UpdateMaterialInput): Promise<Material> {
    const { data } = await apiClient.put(`/inventory/materials/${id}`, payload);
    return data;
  },

  async deleteMaterial(id: string): Promise<void> {
    await apiClient.delete(`/inventory/materials/${id}`);
  },

  // ── Stock & Transactions ────────────────────────────────────────────────
  async getStockInfo(materialId: string): Promise<StockInfo> {
    const { data } = await apiClient.get(`/inventory/materials/${materialId}/stock`);
    return data;
  },

  async createTransaction(payload: StockOperationInput): Promise<Material> {
    const { data } = await apiClient.post("/inventory/transactions", payload);
    return data;
  },

  async getTransactions(params: {
    material_id?: string;
    page: number;
    page_size: number;
  }): Promise<InventoryTransaction[]> {
    const { data } = await apiClient.get("/inventory/transactions/history", { params });
    return data.items || [];
  },

  async getBatches(materialId: string): Promise<Batch[]> {
    const { data } = await apiClient.get("/inventory/batches", { params: { material_id: materialId } });
    return (data.items || []).map((batch: Batch) => ({
      ...batch,
      quantity: Number(batch.quantity ?? 0),
      remaining_quantity: Number(batch.remaining_quantity ?? 0),
      days_until_expiry: batch.days_until_expiry === null ? null : Number(batch.days_until_expiry),
    }));
  },

  async getExpiringBatches(days = 30): Promise<Batch[]> {
    const { data } = await apiClient.get("/inventory/batches/expiring", { params: { days } });
    return (data.items || []).map((batch: Batch) => ({
      ...batch,
      quantity: Number(batch.quantity ?? 0),
      remaining_quantity: Number(batch.remaining_quantity ?? 0),
      days_until_expiry: batch.days_until_expiry === null ? null : Number(batch.days_until_expiry),
    }));
  },

  // ── Master Data ─────────────────────────────────────────────────────────
  async getCategories(): Promise<Category[]> {
    const { data } = await apiClient.get("/inventory/master-data/categories");
    return data;
  },

  async getLocations(params?: { type?: string }): Promise<Location[]> {
    const { data } = await apiClient.get("/inventory/master-data/locations", { params });
    return data;
  },

  async createLocation(body: {
    name: string;
    type: string;
    code?: string | null;
    parent_id?: string | null;
    is_active?: boolean;
  }): Promise<Location> {
    const { data } = await apiClient.post("/inventory/master-data/locations", body);
    return data;
  },

  async updateLocation(
    id: string,
    body: {
      name?: string;
      code?: string | null;
      parent_id?: string | null;
      is_active?: boolean;
    }
  ): Promise<Location> {
    const { data } = await apiClient.put(`/inventory/master-data/locations/${id}`, body);
    return data;
  },

  async getUnits(): Promise<UnitOfMeasure[]> {
    const { data } = await apiClient.get("/inventory/master-data/units");
    return data;
  },

  async updateUnit(
    id: string,
    body: { name?: string; precision?: number; is_active?: boolean }
  ): Promise<UnitOfMeasure> {
    const { data } = await apiClient.put<UnitOfMeasure>(
      `/inventory/master-data/units/${id}`,
      body
    );
    return data;
  },

  async deleteUnit(id: string): Promise<void> {
    await apiClient.delete(`/inventory/master-data/units/${id}`);
  },

  async createCategory(body: {
    name: string;
    code_prefix: string;
    description?: string;
    is_active?: boolean;
  }): Promise<Category> {
    const { data } = await apiClient.post<Category>(
      "/inventory/master-data/categories",
      body
    );
    return data;
  },

  async updateCategory(
    id: string,
    body: {
      name?: string;
      code_prefix?: string;
      description?: string;
      is_active?: boolean;
    }
  ): Promise<Category> {
    const { data } = await apiClient.put<Category>(
      `/inventory/master-data/categories/${id}`,
      body
    );
    return data;
  },

  async deleteCategory(id: string): Promise<void> {
    await apiClient.delete(`/inventory/master-data/categories/${id}`);
  },

  async deleteLocation(id: string): Promise<void> {
    await apiClient.delete(`/inventory/master-data/locations/${id}`);
  },

  // ── Inventory Extended ──────────────────────────────────────────────────
  async getStockLedger(params?: { material_id?: string; limit?: number }) {
    const { data } = await apiClient.get("/inventory/ledger", { params });
    return data;
  },

  async getRealtimeStock() {
    const { data } = await apiClient.get("/inventory/realtime");
    return data;
  },

  async getWarehouseZones(params?: { warehouse_id?: string }) {
    const { data } = await apiClient.get("/inventory/zones", { params });
    return data;
  },

  async createWarehouseZone(payload: any) {
    const { data } = await apiClient.post("/inventory/zones", payload);
    return data;
  },

  async reserveStock(payload: { material_id: string; location_id?: string; quantity: number; notes?: string }) {
    const { data } = await apiClient.post("/inventory/reservations", payload);
    return data;
  },

  async consumeReservation(id: string) {
    const { data } = await apiClient.post(`/inventory/reservations/${id}/consume`);
    return data;
  },

  async cancelReservation(id: string) {
    const { data } = await apiClient.post(`/inventory/reservations/${id}/cancel`);
    return data;
  },

  // ── Purchase History ────────────────────────────────────────────────────
  async getPurchaseHistory(
    materialId: string,
    page = 1,
    pageSize = 25
  ): Promise<PurchaseHistoryPage> {
    const { data } = await apiClient.get(
      `/inventory/materials/${materialId}/purchase-history`,
      { params: { page, page_size: pageSize } }
    );
    return data;
  },
};
