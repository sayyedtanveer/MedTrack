/**
 * Work Order Status Configuration
 * Centralizes WO_STATUS_COLORS for all work order statuses.
 * Used by WorkOrderDetailPage and other WO-related components.
 *
 * Requirements: 10.1–10.7, 6.8
 */

export const WO_STATUS_COLORS: Record<string, string> = {
  PLANNED: 'bg-slate-100 text-slate-700',
  RELEASED: 'bg-blue-100 text-blue-700',
  MATERIAL_PENDING: 'bg-indigo-100 text-indigo-700',
  MATERIAL_RESERVED: 'bg-violet-100 text-violet-700',
  MATERIAL_ISSUED: 'bg-purple-100 text-purple-700',
  IN_PROGRESS: 'bg-amber-100 text-amber-700',
  IN_PRODUCTION: 'bg-yellow-100 text-yellow-700',
  QC_PENDING: 'bg-cyan-100 text-cyan-700',
  QC_APPROVED: 'bg-emerald-100 text-emerald-700',
  QC_REJECTED: 'bg-red-100 text-red-700',
  FG_RECEIVED: 'bg-teal-100 text-teal-700',
  COMPLETED: 'bg-green-100 text-green-700',
  CLOSED: 'bg-zinc-100 text-zinc-600',
  REWORK: 'bg-orange-100 text-orange-700',
  REJECTED: 'bg-red-100 text-red-700',
  PRODUCTION_HOLD: 'bg-rose-100 text-rose-700',
  CANCELLED: 'bg-gray-100 text-gray-600',
};

/**
 * Returns the badge color classes for a given WO status.
 */
export function getWOStatusColor(status: string): string {
  return WO_STATUS_COLORS[status] || 'bg-slate-100 text-slate-700';
}
