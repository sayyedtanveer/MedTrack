import { PurchaseOrder } from '@/services/supply-chain.service';
import { AssistantGuidance, IAssistantProvider, AssistantAction } from '@/components/shared/assistant/AssistantTypes';
import { buildProcurementProgress } from '../definitions/ProcurementWorkflow';

export class ProcurementProvider implements IAssistantProvider<PurchaseOrder> {
  canHandle(entity: any): boolean {
    return entity && 'po_number' in entity && 'supplier_id' in entity;
  }

  getGuidance(order: PurchaseOrder): AssistantGuidance | null {
    if (!order) return null;

    let guidance: AssistantGuidance | null = null;

    // Evaluate statuses
    switch (order.status) {
      case 'draft':
        guidance = {
          currentStage: 'Draft',
          completedStages: [],
          recommendedAction: `Send PO ${order.po_number || ''} to Supplier`,
          reason: `Purchase order ${order.po_number || ''} has been drafted but not yet sent to the supplier.`,
          priority: 'high',
          warnings: [],
          progress: buildProcurementProgress('draft', []),
          actionId: AssistantAction.SEND_PO,
          pulseActionId: 'send'
        };
        break;

      case 'sent':
        guidance = {
          currentStage: 'Sent to Supplier',
          completedStages: ['draft'],
          recommendedAction: `Acknowledge PO ${order.po_number || ''}`,
          reason: `Waiting for the supplier to confirm receipt of PO ${order.po_number || ''}.`,
          priority: 'high',
          warnings: [],
          progress: buildProcurementProgress('sent', ['draft']),
          actionId: AssistantAction.ACKNOWLEDGE_PO,
          pulseActionId: 'acknowledge'
        };
        break;

      case 'acknowledged':
        guidance = {
          currentStage: 'Acknowledged',
          completedStages: ['draft', 'sent'],
          recommendedAction: `Receive PO ${order.po_number || ''}`,
          reason: `The supplier has acknowledged PO ${order.po_number || ''}. Awaiting physical delivery to the warehouse.`,
          priority: 'high',
          warnings: [],
          progress: buildProcurementProgress('acknowledged', ['draft', 'sent']),
          actionId: AssistantAction.RECEIVE_PO,
          route: { module: 'Procurement', destination: 'grn_new', id: order.id }
        };
        break;

      case 'partial':
        guidance = {
          currentStage: 'Partially Received',
          completedStages: ['draft', 'sent', 'acknowledged'],
          recommendedAction: `Receive Remaining for ${order.po_number || ''}`,
          reason: `Some goods have arrived for PO ${order.po_number || ''}, but the order is incomplete. Await remaining delivery.`,
          priority: 'medium',
          warnings: [],
          progress: buildProcurementProgress('partial', ['draft', 'sent', 'acknowledged']),
          actionId: AssistantAction.RECEIVE_REMAINING,
          route: { module: 'Procurement', destination: 'grn_new', id: order.id }
        };
        break;

      case 'completed':
        guidance = {
          currentStage: 'Completed',
          completedStages: ['draft', 'sent', 'acknowledged', 'partial'],
          recommendedAction: `View Invoice for ${order.po_number || ''}`,
          reason: `All materials for PO ${order.po_number || ''} have been received.`,
          priority: 'low',
          warnings: [],
          progress: buildProcurementProgress('completed', ['draft', 'sent', 'acknowledged', 'partial']),
          actionId: AssistantAction.VIEW_INVOICE
        };
        break;

      default:
        guidance = {
          currentStage: 'Closed/Cancelled',
          completedStages: [],
          recommendedAction: 'Go Back',
          reason: 'This order is no longer active.',
          priority: 'low',
          warnings: [],
          progress: buildProcurementProgress('draft', []), // Reset visual
          actionId: AssistantAction.GO_BACK
        };
        break;
    }

    return guidance;
  }
}
