/** Canonical work order statuses (aligned with backend domain WorkOrderStatus). */
export const WORK_ORDER_STATUSES = [
  'PLANNED',
  'RELEASED',
  'MATERIAL_PENDING',
  'MATERIAL_RESERVED',
  'MATERIAL_ISSUED',
  'IN_PRODUCTION',
  'QC_PENDING',
  'QC_APPROVED',
  'QC_REJECTED',
  'FG_RECEIVED',
  'COMPLETED',
  'CLOSED',
  'REWORK',
  'REJECTED',
  'PRODUCTION_HOLD',
  'CANCELLED',
] as const;

export type WorkOrderStatus = (typeof WORK_ORDER_STATUSES)[number];

/** Statuses visible on shop floor / active production views. */
export const SHOP_FLOOR_ACTIVE_STATUSES: WorkOrderStatus[] = [
  'MATERIAL_RESERVED',
  'MATERIAL_ISSUED',
  'IN_PRODUCTION',
  'REWORK',
];

/** @deprecated Use IN_PRODUCTION */
export const LEGACY_IN_PROGRESS = 'IN_PROGRESS';
