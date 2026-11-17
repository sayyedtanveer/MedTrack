/**
 * Type-safe API client for procurement pricing endpoints.
 * 
 * Handles 6-level pricing suggestions, override tracking, and analytics.
 */

import { apiClient as api } from '@/services/api';
import type { MaterialCostHistory, ListMaterialCostHistoryResponse, PriceOverrideRecord, RecordPriceOverrideRequest, ListPriceOverridesResponse } from '../types/pricing';

export interface PricingSuggestion {
  material_id: string;
  supplier_id: string;
  suggested_price: number;
  pricing_source: string; // SUPPLIER_AGREEMENT, QUOTATION, PURCHASE_HISTORY, BENCHMARK_ANY_SUPPLIER, STANDARD_COST, MANUAL
  confidence_level: string; // HIGH, MEDIUM, LOW
  level_number: number; // 1-6
  rationale: string;
  currency_code?: string;
  source_id?: string;
  source_date?: string;
}

export interface PricingAnalysis {
  material_id: string;
  supplier_id: string;
  level_1_agreement_price?: number;
  level_1_agreement_status?: string;
  level_2_quotation_price?: number;
  level_2_quotation_status?: string;
  level_3_grn_price?: number;
  level_3_grn_date?: string;
  level_4_benchmark_price?: number;
  level_4_benchmark_supplier_id?: string;
  level_5_standard_cost?: number;
  level_5_standard_cost_status?: string;
  selected_price?: number;
  selected_source?: string;
  selected_confidence?: string;
  analysis_timestamp: string;
}

export interface OverrideRecord {
  id: string;
  material_id: string;
  supplier_id: string;
  original_suggested_price: number;
  override_price: number;
  variance_percent: number;
  override_reason?: string;
  override_source?: string;
  overridden_by: string;
  created_at: string;
}

export interface OverrideStatistics {
  material_id: string;
  supplier_id: string;
  total_overrides: number;
  average_override_price?: number;
  min_override_price?: number;
  max_override_price?: number;
  median_override_price?: number;
  std_dev?: number;
}

export interface OverrideTrend {
  material_id: string;
  supplier_id: string;
  trend_direction: string; // UPWARD, DOWNWARD, STABLE, INSUFFICIENT_DATA
  total_records_analyzed: number;
  time_period_days?: number;
  price_change_percent?: number;
  trend_confidence: string; // HIGH, MEDIUM, LOW
  analysis_timestamp: string;
}

/**
 * Get 6-level pricing suggestions for a material from a supplier.
 * 
 * Uses fallback logic:
 * 1. Active supplier agreement (HIGH confidence)
 * 2. Approved quotation (MEDIUM confidence)
 * 3. Latest purchase same supplier (MEDIUM confidence)
 * 4. Latest purchase any supplier - benchmarking (LOW confidence)
 * 5. Approved standard cost (LOW confidence)
 * 6. Manual (no suggestion)
 */
export const pricingApi = {
  async getSixLevelSuggestions(
    materialId: string,
    supplierId: string
  ): Promise<PricingSuggestion | null> {
    try {
      const response = await api.get<PricingSuggestion>(
        `/procurement/pricing/suggestions/six-level/${materialId}/${supplierId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get pricing suggestions:', error);
      return null;
    }
  },

  /**
   * Get detailed analysis of all 6 pricing levels.
   * Shows what's available at each level for transparency.
   */
  async getSixLevelAnalysis(
    materialId: string,
    supplierId: string
  ): Promise<PricingAnalysis | null> {
    try {
      const response = await api.get<PricingAnalysis>(
        `/procurement/pricing/analysis/six-level/${materialId}/${supplierId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get pricing analysis:', error);
      return null;
    }
  },

  /**
   * Record a price override for audit trail.
   * Called when user overrides the suggested price.
   */
  async recordOverride(
    materialId: string,
    supplierId: string,
    originalPrice: number,
    overridePrice: number,
    reason?: string,
    source?: string
  ): Promise<OverrideRecord | null> {
    try {
      const response = await api.post<OverrideRecord>(
        `/procurement/pricing/overrides/record-override/${materialId}/${supplierId}`,
        {
          original_suggested_price: originalPrice,
          override_price: overridePrice,
          override_reason: reason,
          override_source: source,
        }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to record price override:', error);
      throw error;
    }
  },

  /**
   * Get price override history for a material-supplier pair.
   * Shows all overrides in reverse chronological order.
   */
  async getOverrideHistory(
    materialId: string,
    supplierId: string
  ): Promise<OverrideRecord[]> {
    try {
      const response = await api.get<OverrideRecord[]>(
        `/procurement/pricing/overrides/history/${materialId}/${supplierId}`
      );
      return response.data || [];
    } catch (error) {
      console.error('Failed to get override history:', error);
      return [];
    }
  },

  /**
   * Get statistics on price overrides.
   * Useful for compliance audits and cost analysis.
   */
  async getOverrideStatistics(
    materialId: string,
    supplierId: string
  ): Promise<OverrideStatistics | null> {
    try {
      const response = await api.get<OverrideStatistics>(
        `/procurement/pricing/overrides/statistics/${materialId}/${supplierId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get override statistics:', error);
      return null;
    }
  },

  /**
   * Analyze price override trends over time.
   * Helps identify pricing patterns (e.g., consistent discounts).
   */
  async getOverrideTrends(
    materialId: string,
    supplierId: string
  ): Promise<OverrideTrend | null> {
    try {
      const response = await api.get<OverrideTrend>(
        `/procurement/pricing/overrides/trends/${materialId}/${supplierId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get override trends:', error);
      return null;
    }
  },
};

/**
 * Material Cost History API client
 */
type CostHistoryWire = Omit<MaterialCostHistory, 'old_cost' | 'new_cost'> & {
  old_cost: number | string | null;
  new_cost: number | string;
};

function normalizeCostHistory(row: CostHistoryWire): MaterialCostHistory {
  return { ...row, old_cost: row.old_cost == null ? null : Number(row.old_cost), new_cost: Number(row.new_cost) };
}

async function loadCostHistory(materialId: string, page: number, pageSize: number, changeType?: string): Promise<ListMaterialCostHistoryResponse> {
  // The existing endpoint returns an array with a limit, not server pagination.
  const { data } = await api.get<CostHistoryWire[]>(`/procurement/pricing/cost-history/${materialId}`, { params: { limit: 10000 } });
  const history = data.map(normalizeCostHistory).filter((row) => !changeType || row.change_type === changeType);
  return { history: history.slice((page - 1) * pageSize, page * pageSize), total: history.length, page, page_size: pageSize };
}

export const materialCostHistoryApi = {
  getHistory: (materialId: string, page = 1, pageSize = 20) => loadCostHistory(materialId, page, pageSize),
  getHistoryByChangeType: (materialId: string, changeType: string, page = 1, pageSize = 20) => loadCostHistory(materialId, page, pageSize, changeType),
};

/**
 * Price Override API client
 */
export const priceOverrideApi = {
  async list(materialId?: string, page = 1, pageSize = 20): Promise<ListPriceOverridesResponse> {
    const { data } = await api.get<Array<Omit<PriceOverrideRecord, 'suggested_price' | 'override_price' | 'variance_percent'> & { suggested_price: number | string; override_price: number | string; variance_percent: number | string | null }>>('/procurement/pricing/price-overrides', {
      params: { material_id: materialId, limit: 10000 },
    });
    return { overrides: data.slice((page - 1) * pageSize, page * pageSize).map((row) => ({ ...row, suggested_price: Number(row.suggested_price), override_price: Number(row.override_price), variance_percent: row.variance_percent == null ? null : Number(row.variance_percent) })), total: data.length, page, page_size: pageSize };
  },

  async record(body: RecordPriceOverrideRequest): Promise<PriceOverrideRecord> {
    const { data } = await api.post<{ override_id: string }>('/procurement/pricing/price-overrides', body);
    const result = await priceOverrideApi.list(body.material_id, 1, 10000);
    const record = result.overrides.find((row) => row.id === data.override_id);
    if (!record) throw new Error('Override saved but could not be reloaded. Refresh the history.');
    return record;
  },

  async recordOverride(
    materialId: string,
    supplierId: string,
    originalPrice: number,
    overridePrice: number,
    reason?: string,
    source?: string
  ): Promise<any> {
    try {
      const response = await api.post<any>(
        `/procurement/pricing/overrides/record-override/${materialId}/${supplierId}`,
        {
          original_suggested_price: originalPrice,
          override_price: overridePrice,
          override_reason: reason,
          override_source: source,
        }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to record price override:', error);
      throw error;
    }
  },

  async getHistory(materialId: string, supplierId: string): Promise<any[]> {
    try {
      const response = await api.get<any[]>(
        `/procurement/pricing/overrides/history/${materialId}/${supplierId}`
      );
      return response.data || [];
    } catch (error) {
      console.error('Failed to get override history:', error);
      return [];
    }
  },

  async getStatistics(materialId: string, supplierId: string): Promise<any | null> {
    try {
      const response = await api.get<any>(
        `/procurement/pricing/overrides/statistics/${materialId}/${supplierId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get override statistics:', error);
      return null;
    }
  },

  async getTrends(materialId: string, supplierId: string): Promise<any | null> {
    try {
      const response = await api.get<any>(
        `/procurement/pricing/overrides/trends/${materialId}/${supplierId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get override trends:', error);
      return null;
    }
  },
};
