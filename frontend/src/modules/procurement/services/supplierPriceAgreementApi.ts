/**
 * Type-safe API client for supplier price agreement endpoints.
 * 
 * Handles supplier agreements, approvals, and pricing negotiations.
 */

import { apiClient as api } from '@/services/api';
import { SupplierPriceAgreement, CreateSupplierPriceAgreementRequest } from '@/modules/procurement/types/pricing';

export interface SupplierPriceAgreementResponse extends SupplierPriceAgreement {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface ListResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateSupplierPriceAgreementResponse {
  id: string;
  status: string;
}

type AgreementWire = Omit<SupplierPriceAgreementResponse, 'base_price' | 'minimum_order_quantity'> & {
  base_price: number | string;
  minimum_order_quantity: number | string | null;
};

export const normalizeSupplierAgreement = (value: AgreementWire): SupplierPriceAgreementResponse => {
  const basePrice = Number(value.base_price);
  const minimumOrder = value.minimum_order_quantity == null ? null : Number(value.minimum_order_quantity);
  if (!Number.isFinite(basePrice) || (minimumOrder !== null && !Number.isFinite(minimumOrder))) {
    throw new Error('Supplier agreement contains an invalid price or MOQ');
  }
  return { ...value, base_price: basePrice, minimum_order_quantity: minimumOrder };
};

/**
 * Supplier Price Agreement API client
 * Manages supplier agreements and price negotiations
 */
export const supplierPriceAgreementApi = {
  /**
   * Create a new supplier price agreement
   */
  async create(data: CreateSupplierPriceAgreementRequest): Promise<CreateSupplierPriceAgreementResponse> {
    try {
      const response = await api.post<CreateSupplierPriceAgreementResponse>(
        `/procurement/pricing/supplier-price-agreements`,
        data
      );
      return response.data;
    } catch (error) {
      console.error('Failed to create supplier price agreement:', error);
      throw error;
    }
  },

  /**
   * Get a specific supplier price agreement
   */
  async getById(agreementId: string): Promise<SupplierPriceAgreementResponse> {
    try {
      const response = await api.get<AgreementWire>(
        `/procurement/pricing/supplier-price-agreements/${agreementId}`
      );
      return normalizeSupplierAgreement(response.data);
    } catch (error) {
      console.error('Failed to fetch supplier price agreement:', error);
      throw error;
    }
  },

  /**
   * List all supplier price agreements with filters
   */
  async list(filters?: { supplier_id?: string; material_id?: string; status?: string; page?: number; page_size?: number }): Promise<ListResult<SupplierPriceAgreementResponse>> {
    try {
      const response = await api.get<ListResult<AgreementWire>>(
        `/procurement/pricing/supplier-price-agreements`,
        { params: filters }
      );
      return { ...response.data, items: response.data.items.map(normalizeSupplierAgreement) };
    } catch (error) {
      console.error('Failed to fetch supplier price agreements:', error);
      throw error;
    }
  },

  /**
   * Submit an agreement for approval (DRAFT → PENDING)
   */
  async submitForApproval(agreementId: string): Promise<SupplierPriceAgreementResponse> {
    try {
      const response = await api.post<SupplierPriceAgreementResponse>(
        `/procurement/pricing/supplier-price-agreements/${agreementId}/submit-for-approval`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to submit agreement for approval:', error);
      throw error;
    }
  },

  /**
   * Approve a pending agreement (PENDING → APPROVED)
   */
  async approve(agreementId: string): Promise<SupplierPriceAgreementResponse> {
    try {
      const response = await api.post<SupplierPriceAgreementResponse>(
        `/procurement/pricing/supplier-price-agreements/${agreementId}/approve`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to approve supplier price agreement:', error);
      throw error;
    }
  },

  /**
   * Activate an approved agreement (APPROVED → ACTIVE)
   */
  async activate(agreementId: string): Promise<SupplierPriceAgreementResponse> {
    try {
      const response = await api.post<SupplierPriceAgreementResponse>(
        `/procurement/pricing/supplier-price-agreements/${agreementId}/activate`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to activate supplier price agreement:', error);
      throw error;
    }
  },

  /**
   * Reject an agreement (PENDING → REJECTED or DRAFT)
   */
  async reject(agreementId: string, reason: string): Promise<SupplierPriceAgreementResponse> {
    try {
      const response = await api.post<SupplierPriceAgreementResponse>(
        `/procurement/pricing/supplier-price-agreements/${agreementId}/reject`,
        { rejection_reason: reason }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to reject supplier price agreement:', error);
      throw error;
    }
  },

  /**
   * Cancel an active agreement (ACTIVE → CANCELLED)
   */
  async cancel(agreementId: string, reason: string): Promise<SupplierPriceAgreementResponse> {
    try {
      const response = await api.post<SupplierPriceAgreementResponse>(
        `/procurement/pricing/supplier-price-agreements/${agreementId}/cancel`,
        { cancellation_reason: reason }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to cancel supplier price agreement:', error);
      throw error;
    }
  },

  /**
   * Get active price agreement for a material-supplier pair
   */
  async getActiveAgreement(materialId: string, supplierId: string): Promise<SupplierPriceAgreementResponse | null> {
    try {
      const response = await api.get<SupplierPriceAgreementResponse>(
        `/procurement/pricing/active-price-agreement`,
        { params: { material_id: materialId, supplier_id: supplierId } }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch active price agreement:', error);
      return null;
    }
  },
};
