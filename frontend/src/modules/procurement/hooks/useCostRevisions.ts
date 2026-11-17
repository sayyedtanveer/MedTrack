/**
 * Custom hook for managing standard cost revisions
 * Phase 2e Frontend Integration
 */

import { useState, useCallback } from "react";
import { StandardCostRevision, CreateStandardCostRevisionRequest } from "../types/pricing";
import {
  standardCostRevisionApi,
  CreateCostRevisionResponse,
} from "../services/standardCostRevisionApi";

interface UseCostRevisionsReturn {
  pendingRevisions: StandardCostRevision[];
  materialRevisions: StandardCostRevision[];
  loading: boolean;
  error: string | null;
  currentPage: number;
  totalPages: number;

  // Actions
  fetchPendingRevisions: (page?: number, pageSize?: number) => Promise<void>;
  fetchMaterialRevisions: (materialId: string, page?: number, pageSize?: number) => Promise<void>;
  createRevision: (data: CreateStandardCostRevisionRequest) => Promise<CreateCostRevisionResponse>;
  approveRevision: (revisionId: string) => Promise<void>;
  rejectRevision: (revisionId: string, reason: string) => Promise<void>;
  nextPage: () => Promise<void>;
  prevPage: () => Promise<void>;
}

export const useCostRevisions = (): UseCostRevisionsReturn => {
  const [pendingRevisions, setPendingRevisions] = useState<StandardCostRevision[]>([]);
  const [materialRevisions, setMaterialRevisions] = useState<StandardCostRevision[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [lastQuery, setLastQuery] = useState<{
    type: "pending" | "material";
    materialId?: string;
    page: number;
    pageSize: number;
  } | null>(null);

  const fetchPendingRevisions = useCallback(async (page: number = 1, pageSize: number = 20) => {
    setLoading(true);
    setError(null);
    try {
      const result = await standardCostRevisionApi.listPending(page, pageSize);
      setPendingRevisions(result.items);
      setTotalPages(Math.ceil(result.total / pageSize));
      setCurrentPage(page);
      setLastQuery({ type: "pending", page, pageSize });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch pending revisions";
      setError(message);
      console.error("Error fetching pending revisions:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchMaterialRevisions = useCallback(
    async (materialId: string, page: number = 1, pageSize: number = 20) => {
      setLoading(true);
      setError(null);
      try {
        const result = await standardCostRevisionApi.listByMaterial(materialId, page, pageSize);
        setMaterialRevisions(result.items);
        setTotalPages(Math.ceil(result.total / pageSize));
        setCurrentPage(page);
        setLastQuery({ type: "material", materialId, page, pageSize });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to fetch material revisions";
        setError(message);
        console.error("Error fetching material revisions:", err);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const createRevision = useCallback(
    async (data: CreateStandardCostRevisionRequest): Promise<CreateCostRevisionResponse> => {
      setLoading(true);
      setError(null);
      try {
        const revision = await standardCostRevisionApi.create(data);
        // Add to list if this matches current query
        if (lastQuery?.type === "material" && lastQuery.materialId === data.material_id) {
          await fetchMaterialRevisions(
            data.material_id,
            lastQuery.page,
            lastQuery.pageSize
          );
        }
        return revision;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create revision";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [fetchMaterialRevisions, lastQuery]
  );

  const approveRevision = useCallback(async (revisionId: string) => {
    setError(null);
    try {
      const updated = await standardCostRevisionApi.approve(revisionId);
      setPendingRevisions((prev) =>
        prev.map((r) => (r.id === revisionId ? updated : r))
      );
      setMaterialRevisions((prev) =>
        prev.map((r) => (r.id === revisionId ? updated : r))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to approve revision";
      setError(message);
      throw err;
    }
  }, []);

  const rejectRevision = useCallback(async (revisionId: string, reason: string) => {
    setError(null);
    try {
      const updated = await standardCostRevisionApi.reject({ revision_id: revisionId, rejection_reason: reason });
      setPendingRevisions((prev) =>
        prev.map((r) => (r.id === revisionId ? updated : r))
      );
      setMaterialRevisions((prev) =>
        prev.map((r) => (r.id === revisionId ? updated : r))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to reject revision";
      setError(message);
      throw err;
    }
  }, []);

  const nextPage = useCallback(async () => {
    if (currentPage < totalPages && lastQuery) {
      if (lastQuery.type === "pending") {
        await fetchPendingRevisions(currentPage + 1, lastQuery.pageSize);
      } else if (lastQuery.type === "material" && lastQuery.materialId) {
        await fetchMaterialRevisions(lastQuery.materialId, currentPage + 1, lastQuery.pageSize);
      }
    }
  }, [currentPage, totalPages, lastQuery, fetchPendingRevisions, fetchMaterialRevisions]);

  const prevPage = useCallback(async () => {
    if (currentPage > 1 && lastQuery) {
      if (lastQuery.type === "pending") {
        await fetchPendingRevisions(currentPage - 1, lastQuery.pageSize);
      } else if (lastQuery.type === "material" && lastQuery.materialId) {
        await fetchMaterialRevisions(lastQuery.materialId, currentPage - 1, lastQuery.pageSize);
      }
    }
  }, [currentPage, lastQuery, fetchPendingRevisions, fetchMaterialRevisions]);

  return {
    pendingRevisions,
    materialRevisions,
    loading,
    error,
    currentPage,
    totalPages,
    fetchPendingRevisions,
    fetchMaterialRevisions,
    createRevision,
    approveRevision,
    rejectRevision,
    nextPage,
    prevPage,
  };
};
