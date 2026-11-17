/**
 * Custom hook for managing supplier price agreements
 * Phase 2e Frontend Integration
 */

import { useState, useCallback } from "react";
import {
  SupplierPriceAgreement,
  CreateSupplierPriceAgreementRequest,
  PricingFilters,
} from "../types/pricing";
import {
  supplierPriceAgreementApi,
  CreateSupplierPriceAgreementResponse,
} from "../services/supplierPriceAgreementApi";

interface UsePricingAgreementsReturn {
  agreements: SupplierPriceAgreement[];
  loading: boolean;
  error: string | null;
  currentPage: number;
  totalPages: number;
  totalCount: number;

  // Actions
  fetchAgreements: (filters: Partial<PricingFilters>) => Promise<void>;
  createAgreement: (data: CreateSupplierPriceAgreementRequest) => Promise<CreateSupplierPriceAgreementResponse>;
  getAgreement: (id: string) => Promise<SupplierPriceAgreement>;
  submitForApproval: (id: string) => Promise<void>;
  approveAgreement: (id: string) => Promise<void>;
  rejectAgreement: (id: string, reason: string) => Promise<void>;
  activateAgreement: (id: string) => Promise<void>;
  cancelAgreement: (id: string, reason: string) => Promise<void>;
  nextPage: () => Promise<void>;
  prevPage: () => Promise<void>;
  goToPage: (page: number) => Promise<void>;
}

export const usePricingAgreements = (): UsePricingAgreementsReturn => {
  const [agreements, setAgreements] = useState<SupplierPriceAgreement[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [lastFilters, setLastFilters] = useState<Partial<PricingFilters>>({});

  const fetchAgreements = useCallback(async (filters: Partial<PricingFilters>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await supplierPriceAgreementApi.list({
        ...filters,
        page: filters.page || 1,
        page_size: filters.page_size || 20,
      });
      setAgreements(result.items);
      setTotalCount(result.total);
      setTotalPages(Math.max(1, Math.ceil(result.total / result.page_size)));
      setCurrentPage(result.page);
      setLastFilters(filters);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch agreements";
      setError(message);
      console.error("Error fetching agreements:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createAgreement = useCallback(
    async (data: CreateSupplierPriceAgreementRequest): Promise<CreateSupplierPriceAgreementResponse> => {
      setLoading(true);
      setError(null);
      try {
        const agreement = await supplierPriceAgreementApi.create(data);
        // Re-fetch list to include new agreement
        await fetchAgreements(lastFilters);
        return agreement;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create agreement";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [fetchAgreements, lastFilters]
  );

  const getAgreement = useCallback(async (id: string): Promise<SupplierPriceAgreement> => {
    setError(null);
    try {
      return await supplierPriceAgreementApi.getById(id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch agreement";
      setError(message);
      throw err;
    }
  }, []);

  const submitForApproval = useCallback(async (id: string) => {
    setError(null);
    try {
      const updated = await supplierPriceAgreementApi.submitForApproval(id);
      setAgreements((prev) =>
        prev.map((a) => (a.id === id ? updated : a))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit agreement";
      setError(message);
      throw err;
    }
  }, []);

  const approveAgreement = useCallback(async (id: string) => {
    setError(null);
    try {
      const updated = await supplierPriceAgreementApi.approve(id);
      setAgreements((prev) =>
        prev.map((a) => (a.id === id ? updated : a))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to approve agreement";
      setError(message);
      throw err;
    }
  }, []);

  const rejectAgreement = useCallback(async (id: string, reason: string) => {
    setError(null);
    try {
      const updated = await supplierPriceAgreementApi.reject(id, reason);
      setAgreements((prev) =>
        prev.map((a) => (a.id === id ? updated : a))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to reject agreement";
      setError(message);
      throw err;
    }
  }, []);

  const activateAgreement = useCallback(async (id: string) => {
    setError(null);
    try {
      const updated = await supplierPriceAgreementApi.activate(id);
      setAgreements((prev) =>
        prev.map((a) => (a.id === id ? updated : a))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to activate agreement";
      setError(message);
      throw err;
    }
  }, []);

  const cancelAgreement = useCallback(async (id: string, reason: string) => {
    setError(null);
    try {
      const updated = await supplierPriceAgreementApi.cancel(id, reason);
      setAgreements((prev) =>
        prev.map((a) => (a.id === id ? updated : a))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to cancel agreement";
      setError(message);
      throw err;
    }
  }, []);

  const nextPage = useCallback(async () => {
    if (currentPage < totalPages) {
      await fetchAgreements({
        ...lastFilters,
        page: currentPage + 1,
      });
    }
  }, [currentPage, totalPages, fetchAgreements, lastFilters]);

  const prevPage = useCallback(async () => {
    if (currentPage > 1) {
      await fetchAgreements({
        ...lastFilters,
        page: currentPage - 1,
      });
    }
  }, [currentPage, fetchAgreements, lastFilters]);

  const goToPage = useCallback(
    async (page: number) => {
      if (page >= 1 && page <= totalPages) {
        await fetchAgreements({
          ...lastFilters,
          page,
        });
      }
    },
    [totalPages, fetchAgreements, lastFilters]
  );

  return {
    agreements,
    loading,
    error,
    currentPage,
    totalPages,
    totalCount,
    fetchAgreements,
    createAgreement,
    getAgreement,
    submitForApproval,
    approveAgreement,
    rejectAgreement,
    activateAgreement,
    cancelAgreement,
    nextPage,
    prevPage,
    goToPage,
  };
};
