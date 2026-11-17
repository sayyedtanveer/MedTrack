/**
 * Type-safe API client for standard cost revision endpoints.
 * 
 * Handles cost revision approval workflows, proposals, and tracking.
 * Consolidates both inventory and procurement cost governance endpoints.
 */

import { apiClient as api } from '@/services/api';
import {
  StandardCostRevision,
  CreateStandardCostRevisionRequest,
} from '@/modules/procurement/types/pricing';

export interface CreateCostRevisionResponse extends StandardCostRevision {
  revision_id: string;
}

export interface RejectRevisionRequest {
  revision_id: string;
  rejection_reason: string;
}

export interface ListResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProposeCostRequest {
  requested_cost: number;
  reason: string;
  notes?: string;
}

export interface CostStatusDetail {
  material_id: string;
  has_approved_cost: boolean;
  cost_status: "CONFIGURED" | "NOT_CONFIGURED" | "PENDING_APPROVAL" | "LEGACY";
  approved_cost: number | string | null;
  current_cost?: number | string | null;
  pending_revision_id: string | null;
  currency_code: string;
}

/**
 * Standard Cost Revision API client
 * Manages approval workflows for cost updates
 * 
 * Endpoints support both:
 * - /inventory/materials/{id}/cost-revisions (Material Buy workflow)
 * - /procurement/pricing/cost-revisions (Procurement workflow)
 */
export const standardCostRevisionApi = {
  /**
   * List pending revisions (awaiting approval)
   */
  async listPending(page: number = 1, pageSize: number = 20): Promise<ListResult<StandardCostRevision>> {
    try {
      const response = await api.get<ListResult<StandardCostRevision>>(
        `/procurement/pricing/cost-revisions`,
        { params: { page, page_size: pageSize } }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch pending revisions:', error);
      throw error;
    }
  },

  /**
   * List all revisions for a material
   */
  async listByMaterial(materialId: string, page: number = 1, pageSize: number = 20): Promise<ListResult<StandardCostRevision>> {
    try {
      const response = await api.get<ListResult<StandardCostRevision>>(
        `/procurement/pricing/cost-revisions`,
        { params: { material_id: materialId, page, page_size: pageSize } }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch material revisions:', error);
      throw error;
    }
  },

  /**
   * Create a new cost revision proposal
   */
  async create(data: CreateStandardCostRevisionRequest): Promise<CreateCostRevisionResponse> {
    try {
      const response = await api.post<CreateCostRevisionResponse>(
        `/procurement/pricing/cost-revisions`,
        data
      );
      return response.data;
    } catch (error) {
      console.error('Failed to create cost revision:', error);
      throw error;
    }
  },

  /**
   * Propose a new standard cost for a material (Material Buy workflow)
   * Creates a StandardCostRevision in PENDING status
   */
  async proposeCost(
    materialId: string,
    data: ProposeCostRequest
  ): Promise<CreateCostRevisionResponse> {
    try {
      const response = await api.post<CreateCostRevisionResponse>(
        `/inventory/materials/${materialId}/cost-revisions`,
        data
      );
      return response.data;
    } catch (error) {
      console.error('Failed to propose cost:', error);
      throw error;
    }
  },

  /**
   * Get material cost status detail
   * Returns cost_status classification (CONFIGURED, NOT_CONFIGURED, PENDING_APPROVAL, LEGACY)
   */
  async getCostStatus(materialId: string): Promise<CostStatusDetail> {
    try {
      const response = await api.get<CostStatusDetail>(
        `/inventory/materials/${materialId}/cost-status`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch cost status:', error);
      throw error;
    }
  },

  /**
   * Approve a pending revision
   */
  async approve(revisionId: string): Promise<StandardCostRevision> {
    try {
      const response = await api.post<StandardCostRevision>(
        `/procurement/pricing/cost-revisions/${revisionId}/approve`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to approve revision:', error);
      throw error;
    }
  },

  /**
   * Reject a pending revision
   */
  async reject(data: RejectRevisionRequest): Promise<StandardCostRevision> {
    try {
      const response = await api.post<StandardCostRevision>(
        `/procurement/pricing/cost-revisions/${data.revision_id}/reject`,
        { rejection_reason: data.rejection_reason }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to reject revision:', error);
      throw error;
    }
  },
};

/**
 * Alias for backward compatibility with inventory module
 * @deprecated Use standardCostRevisionApi directly
 */
export const materialCostApi = standardCostRevisionApi;
