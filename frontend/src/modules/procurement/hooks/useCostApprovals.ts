import { useCallback, useEffect, useState } from "react";
import { standardCostRevisionApi } from "@/modules/procurement/services/standardCostRevisionApi";
import { StandardCostRevision } from "@/modules/procurement/types/pricing";

export interface UseCostApprovalsReturn {
  // Data
  pendingRevisions: StandardCostRevision[];
  totalPending: number;

  // State
  loading: boolean;
  error: Error | null;
  approvingId: string | null;
  rejectingId: string | null;

  // Actions
  refetch: () => Promise<void>;
  approve: (revisionId: string) => Promise<void>;
  reject: (revisionId: string, reason: string) => Promise<void>;
}

/**
 * Custom hook for managing cost approvals
 * Fetches pending cost revisions and handles approve/reject actions
 */
export const useCostApprovals = (page: number = 1, pageSize: number = 20): UseCostApprovalsReturn => {
  const [pendingRevisions, setPendingRevisions] = useState<StandardCostRevision[]>([]);
  const [totalPending, setTotalPending] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);

  const fetchPendingRevisions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await standardCostRevisionApi.listPending(page, pageSize);
      setPendingRevisions(result.items || []);
      setTotalPending(result.total || 0);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch pending cost revisions";
      setError(new Error(errorMessage));
      console.error("Error fetching cost approvals:", err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  // Initial fetch on mount
  useEffect(() => {
    fetchPendingRevisions();
  }, [fetchPendingRevisions]);

  const approve = useCallback(
    async (revisionId: string) => {
      setApprovingId(revisionId);
      try {
        await standardCostRevisionApi.approve(revisionId);
        // Refetch to update list
        await fetchPendingRevisions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to approve revision";
        setError(new Error(errorMessage));
        console.error("Error approving revision:", err);
      } finally {
        setApprovingId(null);
      }
    },
    [fetchPendingRevisions]
  );

  const reject = useCallback(
    async (revisionId: string, reason: string) => {
      setRejectingId(revisionId);
      try {
        await standardCostRevisionApi.reject({
          revision_id: revisionId,
          rejection_reason: reason,
        });
        // Refetch to update list
        await fetchPendingRevisions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to reject revision";
        setError(new Error(errorMessage));
        console.error("Error rejecting revision:", err);
      } finally {
        setRejectingId(null);
      }
    },
    [fetchPendingRevisions]
  );

  return {
    pendingRevisions,
    totalPending,
    loading,
    error,
    approvingId,
    rejectingId,
    refetch: fetchPendingRevisions,
    approve,
    reject,
  };
};
