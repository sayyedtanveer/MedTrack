/**
 * Sales Module Type Definitions
 * Defines all interfaces for Sales Order, Client, and Price List management
 */

/**
 * Sales Client Entity
 */
export interface SalesClient {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  gst_number?: string;
  credit_limit: number;
  credit_used: number;
  payment_terms_days: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateClientRequest {
  code: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  gst_number?: string;
  credit_limit: number;
  payment_terms_days: number;
}

export interface UpdateClientRequest {
  name?: string;
  email?: string;
  phone?: string;
  address?: string;
  gst_number?: string;
  credit_limit?: number;
  payment_terms_days?: number;
  is_active?: boolean;
}

/**
 * Sales Order Line Item
 */
export interface SalesOrderLine {
  id: string;
  sales_order_id: string;
  product_id: string;
  product_type: 'variant' | 'finished_product';
  product_name?: string | null;
  product_code?: string | null;
  quantity: number;
  uom_id: string;
  uom_code?: string | null;
  uom_name?: string | null;
  unit_price: number;
  tax_rate: number;
  allocated_qty: number;
  shipped_qty: number;
  backorder_qty: number;
  shortfall_quantity?: number;
  production_required?: boolean;
  subtotal: number;
  tax_amount: number;
  total: number;
  line_status: 'PENDING' | 'ALLOCATED' | 'PARTIAL' | 'SHORT_CLOSED' | 'BACKORDER' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED';
}

export interface CreateOrderLineRequest {
  product_id: string;
  product_type: 'variant' | 'finished_product';
  quantity: number;
  uom_id: string;
  tax_rate: number;
}

/**
 * Sales Order Status
 */
export enum OrderStatus {
  DRAFT = 'DRAFT',
  PENDING_APPROVAL = 'PENDING_APPROVAL',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  WORK_ORDER_CREATED = 'WORK_ORDER_CREATED',
  CONFIRMED = 'CONFIRMED',
  PROCESSING = 'PROCESSING',
  PRODUCTION = 'PRODUCTION',
  READY = 'READY',
  READY_FOR_DISPATCH = 'READY_FOR_DISPATCH',
  SHIPPED = 'SHIPPED',
  DELIVERED = 'DELIVERED',
  INVOICED = 'INVOICED',
  PAYMENT_RECEIVED = 'PAYMENT_RECEIVED',
  COMPLETED = 'COMPLETED',
  CANCELLED = 'CANCELLED',
}

export enum PaymentStatus {
  PENDING = 'PENDING',
  PARTIAL = 'PARTIAL',
  PAID = 'PAID',
  OVERDUE = 'OVERDUE',
}

/**
 * Sales Order Entity
 */
export interface SalesOrder {
  id: string;
  tenant_id: string;
  order_number: string;
  client_id: string;
  client_name?: string | null;
  client_code?: string | null;
  order_date: string;
  delivery_date: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  grand_total: number;
  notes?: string;
  created_by?: string;
  approver_id?: string | null;
  submitted_at?: string | null;
  approved_at?: string | null;
  rejected_at?: string | null;
  approval_notes?: string | null;
  item_count?: number;
  item_summary?: string | null;
  is_active: boolean;
  lines: SalesOrderLine[];
  created_at: string;
  updated_at: string;
}

export interface CreateOrderRequest {
  client_id: string;
  order_date: string;
  delivery_date: string;
  notes?: string;
  lines?: CreateOrderLineRequest[];
}

export interface UpdateOrderRequest {
  delivery_date?: string;
  notes?: string;
}

/**
 * Price List Entity
 */
export interface PriceListLine {
  id: string;
  price_list_id: string;
  product_id: string;
  product_type: 'variant' | 'finished_product';
  unit_price: number;
  effective_from: string;
  effective_to?: string;
}

export interface PriceList {
  id: string;
  tenant_id: string;
  name: string;
  is_default: boolean;
  is_active: boolean;
  valid_from: string;
  valid_to?: string;
  lines: PriceListLine[];
  created_at: string;
  updated_at: string;
}

export interface CreatePriceListRequest {
  name: string;
  is_default?: boolean;
  valid_from: string;
  valid_to?: string;
}

export interface CreatePriceListLineRequest {
  product_id: string;
  product_type: 'variant' | 'finished_product';
  unit_price: number;
  effective_from: string;
  effective_to?: string;
}

/**
 * API Response Types
 */
export interface SalesListResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface OrderStatistics {
  draft_count: number;
  pending_approval_count: number;
  approved_count: number;
  rejected_count: number;
  confirmed_count: number;
  processing_count: number;
  production_count: number;
  ready_count: number;
  shipped_count: number;
  delivered_count: number;
  completed_count: number;
  cancelled_count: number;
}

export interface ClientCreditInfo {
  client_id: string;
  credit_limit: number;
  credit_used: number;
  available_credit: number;
  usage_percent: number;
}
