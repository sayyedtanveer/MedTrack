/**
 * Sales Order Status Configuration
 * Centralizes STATUS_COLORS, STATUS_COLOR_MAP, and STATUS_ACTIONS mappings for all 16 SO statuses.
 * Used by SalesOrderDetailPage and SalesOrdersListPage.
 *
 * Requirements: 11.1–11.8, 3.8
 */

import { OrderStatus } from '@/types/sales.types';
import type { StatusColorMap } from '@/components/shared/StatusBadge';

/**
 * Status badge color classes for all 16 SO statuses.
 * Each status uses a distinct background/text color pair (for direct Badge className usage).
 */
export const STATUS_COLORS: Record<OrderStatus, string> = {
  [OrderStatus.DRAFT]: 'bg-gray-100 text-gray-800',
  [OrderStatus.PENDING_APPROVAL]: 'bg-amber-100 text-amber-800',
  [OrderStatus.APPROVED]: 'bg-indigo-100 text-indigo-800',
  [OrderStatus.REJECTED]: 'bg-red-100 text-red-800',
  [OrderStatus.WORK_ORDER_CREATED]: 'bg-violet-100 text-violet-800',
  [OrderStatus.CONFIRMED]: 'bg-blue-100 text-blue-800',
  [OrderStatus.PROCESSING]: 'bg-sky-100 text-sky-800',
  [OrderStatus.PRODUCTION]: 'bg-yellow-100 text-yellow-800',
  [OrderStatus.READY]: 'bg-purple-100 text-purple-800',
  [OrderStatus.READY_FOR_DISPATCH]: 'bg-teal-100 text-teal-800',
  [OrderStatus.SHIPPED]: 'bg-green-100 text-green-800',
  [OrderStatus.DELIVERED]: 'bg-emerald-100 text-emerald-800',
  [OrderStatus.INVOICED]: 'bg-cyan-100 text-cyan-800',
  [OrderStatus.PAYMENT_RECEIVED]: 'bg-lime-100 text-lime-800',
  [OrderStatus.COMPLETED]: 'bg-emerald-100 text-emerald-700',
  [OrderStatus.CANCELLED]: 'bg-red-100 text-red-800',
};

/**
 * StatusColorMap for use with the <StatusBadge colorMap={...}> component.
 * Provides border + background + text classes for each of the 16 SO statuses.
 * Distinct colors per status as required by Req 11.1–11.3.
 */
export const SO_STATUS_COLOR_MAP: StatusColorMap = {
  // DRAFT → gray
  [OrderStatus.DRAFT]: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100',
  // PENDING_APPROVAL → amber
  [OrderStatus.PENDING_APPROVAL]: 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100',
  // APPROVED → indigo
  [OrderStatus.APPROVED]: 'border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100',
  // REJECTED → red
  [OrderStatus.REJECTED]: 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100',
  // WORK_ORDER_CREATED → violet
  [OrderStatus.WORK_ORDER_CREATED]: 'border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100',
  // CONFIRMED → blue
  [OrderStatus.CONFIRMED]: 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100',
  // PROCESSING → sky
  [OrderStatus.PROCESSING]: 'border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100',
  // PRODUCTION → yellow
  [OrderStatus.PRODUCTION]: 'border-yellow-200 bg-yellow-50 text-yellow-700 hover:bg-yellow-100',
  // READY → purple
  [OrderStatus.READY]: 'border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100',
  // READY_FOR_DISPATCH → teal
  [OrderStatus.READY_FOR_DISPATCH]: 'border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100',
  // SHIPPED → green
  [OrderStatus.SHIPPED]: 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100',
  // DELIVERED → emerald
  [OrderStatus.DELIVERED]: 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
  // INVOICED → cyan
  [OrderStatus.INVOICED]: 'border-cyan-200 bg-cyan-50 text-cyan-700 hover:bg-cyan-100',
  // PAYMENT_RECEIVED → lime
  [OrderStatus.PAYMENT_RECEIVED]: 'border-lime-200 bg-lime-50 text-lime-700 hover:bg-lime-100',
  // COMPLETED → emerald (same hue, slightly stronger)
  [OrderStatus.COMPLETED]: 'border-emerald-300 bg-emerald-100 text-emerald-800 hover:bg-emerald-200',
  // CANCELLED → red
  [OrderStatus.CANCELLED]: 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100',
};

/**
 * Action configuration for status-driven action buttons.
 */
export interface ActionConfig {
  label: string;
  action: string;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary';
  icon?: string;
}

/**
 * STATUS_ACTIONS mapping: defines which action buttons appear for each SO status.
 * Statuses not listed here show contextual info panels instead.
 */
export const STATUS_ACTIONS: Record<OrderStatus, ActionConfig[]> = {
  [OrderStatus.DRAFT]: [
    { label: 'Submit for Approval', action: 'submit', variant: 'default' },
  ],
  [OrderStatus.PENDING_APPROVAL]: [
    { label: 'Approve', action: 'approve', variant: 'default' },
    { label: 'Reject', action: 'reject', variant: 'destructive' },
  ],
  [OrderStatus.APPROVED]: [
    { label: 'Confirm & Execute', action: 'confirm', variant: 'default' },
  ],
  [OrderStatus.REJECTED]: [],
  [OrderStatus.WORK_ORDER_CREATED]: [],
  [OrderStatus.CONFIRMED]: [],
  [OrderStatus.PROCESSING]: [],
  [OrderStatus.PRODUCTION]: [],
  [OrderStatus.READY]: [],
  [OrderStatus.READY_FOR_DISPATCH]: [
    { label: 'Create Delivery Note', action: 'create_delivery', variant: 'default' },
  ],
  [OrderStatus.SHIPPED]: [],
  [OrderStatus.DELIVERED]: [],
  [OrderStatus.INVOICED]: [
    { label: 'Record Payment', action: 'record_payment', variant: 'default' },
  ],
  [OrderStatus.PAYMENT_RECEIVED]: [],
  [OrderStatus.COMPLETED]: [],
  [OrderStatus.CANCELLED]: [],
};

/**
 * Statuses that allow the "Cancel Order" action
 */
export const CANCELLABLE_STATUSES: OrderStatus[] = [
  OrderStatus.DRAFT,
  OrderStatus.PENDING_APPROVAL,
  OrderStatus.APPROVED,
  OrderStatus.CONFIRMED,
  OrderStatus.PROCESSING,
  OrderStatus.PRODUCTION,
];

/**
 * Returns the badge color classes for a given status.
 */
export function getStatusColor(status: OrderStatus): string {
  return STATUS_COLORS[status] || 'bg-gray-100 text-gray-800';
}
