import { useCallback, useEffect, useState } from "react";
import { materialCostHistoryApi } from "../services/pricingApi";
import { MaterialCostHistory } from "@/modules/procurement/types/pricing";

export interface UseMaterialCostHistoryReturn {
  // Data
  history: MaterialCostHistory[];
  totalRecords: number;

  // State
  loading: boolean;
  error: Error | null;

  // Actions
  refetch: () => Promise<void>;
}

/**
 * Custom hook for material cost history
 * Fetches append-only audit log of cost changes
 */
export const useMaterialCostHistory = (
  materialId: string,
  page: number = 1,
  pageSize: number = 20
): UseMaterialCostHistoryReturn => {
  const [history, setHistory] = useState<MaterialCostHistory[]>([]);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchCostHistory = useCallback(async () => {
    if (!materialId) {
      setHistory([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await materialCostHistoryApi.getHistory(materialId, page, pageSize);
      setHistory(response.history);
      setTotalRecords(response.total);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch cost history";
      setError(new Error(errorMessage));
      console.error("Error fetching cost history:", err);
    } finally {
      setLoading(false);
    }
  }, [materialId, page, pageSize]);

  // Initial fetch on mount
  useEffect(() => {
    fetchCostHistory();
  }, [fetchCostHistory]);

  return {
    history,
    totalRecords,
    loading,
    error,
    refetch: fetchCostHistory,
  };
};
