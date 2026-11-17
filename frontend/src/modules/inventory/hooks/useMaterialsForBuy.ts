import { Material } from "@/types/material.types";
import { materialApi } from "@/modules/inventory/services/materialApi";
import { useApiList } from "@/modules/shared/hooks/useApiList";

export interface UseMaterialsForBuyReturn {
  // Data
  allMaterials: Material[];
  notConfiguredMaterials: Material[];
  pendingApprovalMaterials: Material[];
  configuredMaterials: Material[];

  // State
  loading: boolean;
  error: Error | null;

  // Actions
  refetch: () => Promise<void>;
}

/**
 * Custom hook for Material Buy workflow
 * Fetches materials with cost_status and groups by status
 */
export const useMaterialsForBuy = (): UseMaterialsForBuyReturn => {
  const { items: allMaterials, loading, error, refetch } = useApiList(
    (page, pageSize) =>
      materialApi.list({
        page,
        page_size: pageSize,
        is_active: true,
      }),
    { pageSize: 1000 } // Fetch all materials in one call
  );

  // Group materials by cost_status
  const notConfiguredMaterials = allMaterials.filter(
    (m) => m.cost_status === "NOT_CONFIGURED"
  );

  const pendingApprovalMaterials = allMaterials.filter(
    (m) => m.cost_status === "PENDING_APPROVAL"
  );

  const configuredMaterials = allMaterials.filter(
    (m) => m.cost_status === "CONFIGURED"
  );

  return {
    allMaterials,
    notConfiguredMaterials,
    pendingApprovalMaterials,
    configuredMaterials,
    loading,
    error,
    refetch,
  };
};
