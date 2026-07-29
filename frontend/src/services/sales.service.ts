/**
 * Sales API Service
 * Handles all API calls for Sales Orders, Clients, and Price Lists
 */

import { apiClient } from './api-client';
import {
  SalesClient,
  SalesOrder,
  PriceList,
  OrderStatus,
  PaymentStatus,
  CreateClientRequest,
  UpdateClientRequest,
  CreateOrderRequest,
  UpdateOrderRequest,
  CreateOrderLineRequest,
  CreatePriceListRequest,
  ClientCreditInfo,
  OrderStatistics,
  SalesListResponse,
} from '@/types/sales.types';

const BASE_URL = '/sales';

const unwrap = async <T>(request: Promise<{ data: T }>): Promise<T> => {
  const response = await request;
  return response.data;
};

const toNumber = (value: unknown): number => {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
};

const normalizeClient = (client: any): SalesClient => ({
  ...client,
  credit_limit: toNumber(client.credit_limit),
  credit_used: toNumber(client.credit_used),
  payment_terms_days: toNumber(client.payment_terms_days),
});

const normalizeOrderLine = (line: any) => {
  const quantity = toNumber(line.quantity);
  const unitPrice = toNumber(line.unit_price);
  const total = toNumber(line.total ?? line.line_total);

  return {
    ...line,
    product_name: line.product_name ?? null,
    product_code: line.product_code ?? null,
    uom_code: line.uom_code ?? null,
    uom_name: line.uom_name ?? null,
    quantity,
    unit_price: unitPrice,
    tax_rate: toNumber(line.tax_rate),
    allocated_qty: toNumber(line.allocated_qty ?? line.allocated_quantity),
    shipped_qty: toNumber(line.shipped_qty ?? line.shipped_quantity),
    backorder_qty: toNumber(line.backorder_qty ?? line.backorder_quantity),
    shortfall_quantity: toNumber(line.shortfall_quantity),
    production_required: Boolean(line.production_required),
    subtotal: toNumber(line.subtotal ?? quantity * unitPrice),
    tax_amount: toNumber(line.tax_amount),
    total,
    line_status: (line.line_status ?? line.status ?? 'PENDING').toString().toUpperCase(),
  };
};

const normalizeOrder = (order: any): SalesOrder => ({
  ...order,
  client_name: order.client_name ?? null,
  client_code: order.client_code ?? null,
  status: (order.status ?? OrderStatus.DRAFT).toString().toUpperCase() as OrderStatus,
  payment_status: (order.payment_status ?? PaymentStatus.PENDING).toString().toUpperCase() as PaymentStatus,
  subtotal: toNumber(order.subtotal),
  discount_amount: toNumber(order.discount_amount),
  tax_amount: toNumber(order.tax_amount),
  grand_total: toNumber(order.grand_total),
  item_count: toNumber(order.item_count ?? (Array.isArray(order.lines) ? order.lines.length : 0)),
  item_summary: order.item_summary ?? null,
  lines: Array.isArray(order.lines) ? order.lines.map(normalizeOrderLine) : [],
});

const normalizePriceList = (priceList: any): PriceList => ({
  ...priceList,
  lines: Array.isArray(priceList.lines)
    ? priceList.lines.map((line: any) => ({ ...line, unit_price: toNumber(line.unit_price) }))
    : [],
});

const normalizeStatistics = (stats: any): OrderStatistics => ({
  draft_count: toNumber(stats.draft_count ?? stats.DRAFT),
  pending_approval_count: toNumber(stats.pending_approval_count ?? stats.PENDING_APPROVAL),
  approved_count: toNumber(stats.approved_count ?? stats.APPROVED),
  rejected_count: toNumber(stats.rejected_count ?? stats.REJECTED),
  confirmed_count: toNumber(stats.confirmed_count ?? stats.CONFIRMED),
  processing_count: toNumber(stats.processing_count ?? stats.PROCESSING),
  production_count: toNumber(stats.production_count ?? stats.PRODUCTION),
  ready_count: toNumber(stats.ready_count ?? stats.READY),
  shipped_count: toNumber(stats.shipped_count ?? stats.SHIPPED) + 
                 toNumber(stats.delivered_count ?? stats.DELIVERED) + 
                 toNumber(stats.completed_count ?? stats.COMPLETED),
  delivered_count: toNumber(stats.delivered_count ?? stats.DELIVERED),
  completed_count: toNumber(stats.completed_count ?? stats.COMPLETED),
  cancelled_count: toNumber(stats.cancelled_count ?? stats.CANCELLED),
});

const normalizeCredit = (credit: any): ClientCreditInfo => {
  const creditLimit = credit.credit_limit === null ? 0 : toNumber(credit.credit_limit);
  const creditUsed = toNumber(credit.credit_used);
  const availableCredit = credit.available_credit === null ? 0 : toNumber(credit.available_credit);

  return {
    ...credit,
    credit_limit: creditLimit,
    credit_used: creditUsed,
    available_credit: availableCredit,
    usage_percent: creditLimit && creditLimit > 0 ? (creditUsed / creditLimit) * 100 : 0,
  };
};

/**
 * ============================================================================
 * CLIENTS API
 * ============================================================================
 */

export const clientsApi = {
  /**
   * Create a new sales client
   */
  create: async (data: CreateClientRequest): Promise<SalesClient> => {
    return normalizeClient(await unwrap(apiClient.post(`${BASE_URL}/clients`, data)));
  },

  /**
   * Get client by ID
   */
  get: async (clientId: string): Promise<SalesClient> => {
    return normalizeClient(await unwrap(apiClient.get(`${BASE_URL}/clients/${clientId}`)));
  },

  /**
   * List all clients with pagination and filtering
   */
  list: async (
    limit?: number,
    offset?: number,
    search?: string,
    is_active?: boolean
  ): Promise<SalesListResponse<SalesClient>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    if (search) params.append('search', search);
    if (is_active !== undefined) params.append('is_active', is_active.toString());

    const query = params.toString();
    const response = await unwrap<SalesListResponse<SalesClient>>(
      apiClient.get(`${BASE_URL}/clients${query ? `?${query}` : ''}`)
    );
    return { ...response, items: response.items.map(normalizeClient) };
  },

  /**
   * Update client
   */
  update: async (clientId: string, data: UpdateClientRequest): Promise<SalesClient> => {
    return normalizeClient(await unwrap(apiClient.patch(`${BASE_URL}/clients/${clientId}`, data)));
  },

  /**
   * Deactivate (soft delete) client
   */
  deactivate: async (clientId: string): Promise<void> => {
    await apiClient.delete(`${BASE_URL}/clients/${clientId}`);
  },

  /**
   * Get client credit information
   */
  getCredit: async (clientId: string): Promise<ClientCreditInfo> => {
    return normalizeCredit(await unwrap(apiClient.get(`${BASE_URL}/clients/${clientId}/credit`)));
  },
};

/**
 * ============================================================================
 * SALES ORDERS API
 * ============================================================================
 */

export const ordersApi = {
  /**
   * Create a new sales order
   */
  create: async (data: CreateOrderRequest): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders`, data)));
  },

  /**
   * Get sales order by ID (with full details)
   */
  get: async (orderId: string): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.get(`${BASE_URL}/orders/${orderId}`)));
  },

  /**
   * Get sales order by order number
   */
  getByNumber: async (orderNumber: string): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.get(`${BASE_URL}/orders/number/${orderNumber}`)));
  },

  /**
   * List all sales orders with filtering
   */
  list: async (
    limit?: number,
    offset?: number,
    clientId?: string,
    status?: OrderStatus,
    startDate?: string,
    endDate?: string
  ): Promise<SalesListResponse<SalesOrder>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    if (clientId) params.append('client_id', clientId);
    if (status) params.append('status', status);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const query = params.toString();
    const response = await unwrap<SalesListResponse<SalesOrder>>(
      apiClient.get(`${BASE_URL}/orders${query ? `?${query}` : ''}`)
    );
    return { ...response, items: response.items.map(normalizeOrder) };
  },

  /**
   * Update sales order (before confirmation)
   */
  update: async (orderId: string, data: UpdateOrderRequest): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.patch(`${BASE_URL}/orders/${orderId}`, data)));
  },

  /**
   * List draft orders waiting for confirmation
   */
  listDraft: async (limit?: number): Promise<SalesListResponse<SalesOrder>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    const query = params.toString();
    const response = await unwrap<SalesListResponse<SalesOrder>>(
      apiClient.get(`${BASE_URL}/orders/draft${query ? `?${query}` : ''}`)
    );
    return { ...response, items: response.items.map(normalizeOrder) };
  },

  /**
   * Add line item to order
   */
  addLine: async (orderId: string, line: CreateOrderLineRequest): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/lines`, line)));
  },

  /**
   * Remove line item from order
   */
  removeLine: async (orderId: string, lineId: string): Promise<SalesOrder> => {
    return unwrap(apiClient.delete(`${BASE_URL}/orders/${orderId}/lines/${lineId}`));
  },

  /**
   * Update line item (for status updates like SHORT_CLOSED)
   */
  updateLine: async (orderId: string, lineId: string, data: { line_status?: string }): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.patch(`${BASE_URL}/orders/${orderId}/lines/${lineId}`, data)));
  },

  /**
   * Apply discount to order
   */
  applyDiscount: async (orderId: string, discountAmount: number): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/discount`, {
      discount_amount: discountAmount,
    })));
  },

  /**
   * Confirm order (move from DRAFT to CONFIRMED)
   */
  confirm: async (orderId: string): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/confirm`, {
      confirmed_by: 'admin',
    })));
  },

  /**
   * Submit order for manager approval
   */
  submitForApproval: async (orderId: string, notes?: string): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/submit-approval`, { notes })));
  },

  /**
   * Approve order and start execution
   */
  approve: async (orderId: string, notes?: string): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/approve`, { notes })));
  },

  /**
   * Reject order
   */
  reject: async (orderId: string, notes?: string): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/reject`, { notes })));
  },

  /**
   * Record shipment (move to SHIPPED)
   */
  ship: async (orderId: string, shipmentData?: any): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/ship`, {
      line_shipments: shipmentData?.line_shipments ?? {},
      shipped_by: shipmentData?.shipped_by ?? 'admin',
    })));
  },

  /**
   * Record delivery (move to DELIVERED)
   */
  deliver: async (orderId: string, deliveryData?: any): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/deliver`, deliveryData || {})));
  },

  /**
   * Cancel order
   */
  cancel: async (orderId: string, reason?: string): Promise<SalesOrder> => {
    return normalizeOrder(await unwrap(apiClient.post(`${BASE_URL}/orders/${orderId}/cancel`, { reason })));
  },

  /**
   * Get order statistics (count by status)
   */
  getStatistics: async (): Promise<OrderStatistics> => {
    return normalizeStatistics(await unwrap(apiClient.get(`${BASE_URL}/orders/stats/by-status`)));
  },
};

/**
 * ============================================================================
 * PRICE LISTS API
 * ============================================================================
 */

export const priceListsApi = {
  /**
   * Create a new price list
   */
  create: async (data: CreatePriceListRequest): Promise<PriceList> => {
    return normalizePriceList(await unwrap(apiClient.post(`${BASE_URL}/price-lists`, data)));
  },

  /**
   * Get price list by ID
   */
  get: async (priceListId: string): Promise<PriceList> => {
    return normalizePriceList(await unwrap(apiClient.get(`${BASE_URL}/price-lists/${priceListId}`)));
  },

  /**
   * List all price lists
   */
  list: async (limit?: number, offset?: number): Promise<SalesListResponse<PriceList>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());

    const query = params.toString();
    const response = await unwrap<SalesListResponse<PriceList>>(
      apiClient.get(`${BASE_URL}/price-lists${query ? `?${query}` : ''}`)
    );
    return { ...response, items: response.items.map(normalizePriceList) };
  },

  /**
   * Update price list
   */
  update: async (
    priceListId: string,
    data: Partial<CreatePriceListRequest>
  ): Promise<PriceList> => {
    return normalizePriceList(await unwrap(apiClient.patch(`${BASE_URL}/price-lists/${priceListId}`, data)));
  },

  /**
   * Add line to price list
   */
  addLine: async (priceListId: string, lineData: any): Promise<PriceList> => {
    return normalizePriceList(await unwrap(apiClient.post(`${BASE_URL}/price-lists/${priceListId}/lines`, lineData)));
  },

  /**
   * Update price list line
   */
  updateLine: async (priceListId: string, lineData: any): Promise<PriceList> => {
    return normalizePriceList(await unwrap(apiClient.patch(`${BASE_URL}/price-lists/${priceListId}/lines`, lineData)));
  },

  /**
   * Remove line from price list
   */
  removeLine: async (priceListId: string, lineId: string): Promise<PriceList> => {
    return unwrap(apiClient.delete(`${BASE_URL}/price-lists/${priceListId}/lines/${lineId}`));
  },
};

/**
 * Export all sales API methods
 */
export const salesApi = {
  clients: clientsApi,
  orders: ordersApi,
  priceLists: priceListsApi,
};

export default salesApi;
