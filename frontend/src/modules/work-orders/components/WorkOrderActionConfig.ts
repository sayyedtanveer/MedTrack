/**
 * Work Order Action Configuration
 * Defines the lifecycle action buttons for each work order status.
 *
 * This configuration maps work order statuses to their available actions,
 * implementing the requirements from Manufacturing ERP Audit spec.
 *
 * Requirements: 6.1-6.8, 7.1-7.8, 8.1-8.7, 9.1-9.8, 10.1-10.7, 12.1-12.6, 13.1-13.6
 */

export interface WorkOrderAction {
  label: string;
  actionKey: string;
  color: string;
  variant?: 'primary' | 'secondary' | 'danger';
}

/**
 * Maps work order statuses to their available lifecycle actions.
 *
 * Action button mapping per requirement 10.1:
 * - PLANNED → "Release Work Order"
 * - RELEASED/MATERIAL_RESERVED → (no action buttons, show materials table)
 * - MATERIAL_ISSUED → "Start Production"
 * - IN_PRODUCTION → (show Record Production form)
 * - QC_PENDING → "Approve QC", "Reject QC"
 * - QC_APPROVED → "Receive FG"
 * - QC_REJECTED → "Send to Rework", "Scrap Batch"
 * - REWORK → "Start Rework Production"
 * - FG_RECEIVED → "Complete"
 * - PRODUCTION_HOLD → "Resume Production"
 */
export const WO_STATUS_ACTIONS: Record<string, WorkOrderAction[]> = {
  PLANNED: [
    {
      label: 'Release Work Order',
      actionKey: 'release',
      color: 'bg-blue-600 hover:bg-blue-700 text-white',
      variant: 'primary',
    },
  ],
  RELEASED: [],
  MATERIAL_PENDING: [],
  MATERIAL_RESERVED: [], // Materials table with Issue buttons per line
  MATERIAL_ISSUED: [
    {
      label: 'Start Production',
      actionKey: 'start',
      color: 'bg-purple-600 hover:bg-purple-700 text-white',
      variant: 'primary',
    },
  ],
  IN_PRODUCTION: [], // Record Production form shown instead
  QC_PENDING: [
    {
      label: 'Approve QC',
      actionKey: 'qc_approve',
      color: 'bg-green-600 hover:bg-green-700 text-white',
      variant: 'primary',
    },
    {
      label: 'Reject QC',
      actionKey: 'qc_reject',
      color: 'bg-red-600 hover:bg-red-700 text-white',
      variant: 'danger',
    },
  ],
  QC_APPROVED: [
    {
      label: 'Receive FG',
      actionKey: 'receive_fg',
      color: 'bg-emerald-600 hover:bg-emerald-700 text-white',
      variant: 'primary',
    },
  ],
  QC_REJECTED: [
    {
      label: 'Send to Rework',
      actionKey: 'send_to_rework',
      color: 'bg-orange-600 hover:bg-orange-700 text-white',
      variant: 'secondary',
    },
    {
      label: 'Scrap Batch',
      actionKey: 'scrap',
      color: 'bg-red-600 hover:bg-red-700 text-white',
      variant: 'danger',
    },
  ],
  REWORK: [
    {
      label: 'Start Rework Production',
      actionKey: 'start_rework',
      color: 'bg-orange-600 hover:bg-orange-700 text-white',
      variant: 'primary',
    },
  ],
  FG_RECEIVED: [
    {
      label: 'Complete',
      actionKey: 'complete',
      color: 'bg-teal-600 hover:bg-teal-700 text-white',
      variant: 'primary',
    },
  ],
  COMPLETED: [],
  CLOSED: [],
  REJECTED: [],
  PRODUCTION_HOLD: [
    {
      label: 'Resume Production',
      actionKey: 'resume',
      color: 'bg-blue-600 hover:bg-blue-700 text-white',
      variant: 'primary',
    },
  ],
};

/**
 * Returns the available actions for a given work order status.
 */
export function getWOStatusActions(status: string): WorkOrderAction[] {
  return WO_STATUS_ACTIONS[status] || [];
}
