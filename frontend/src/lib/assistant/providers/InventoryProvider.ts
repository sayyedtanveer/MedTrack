import { AssistantGuidance, IAssistantProvider, AssistantAction, AssistantPriority, WorkflowStage } from '@/components/shared/assistant/AssistantTypes';

export class InventoryProvider implements IAssistantProvider<any> {
  canHandle(entity: any): boolean {
    return entity && entity.type === 'inventory_receipt';
  }

  getGuidance(po: any): AssistantGuidance | null {
    if (!po) return null;

    let priority: AssistantPriority = 'medium';
    let warnings: string[] = [];

    // Evaluate aging / due date
    if (po.expected_date) {
      const due = new Date(po.expected_date);
      const now = new Date();
      if (due < now) {
        priority = 'high';
        warnings.push('This receipt is overdue.');
      }
    }

    const progress: WorkflowStage[] = [
      { id: 'approved', label: 'Approved', status: 'completed' },
      { id: 'receive', label: 'Receive Goods', status: 'current' },
      { id: 'stocked', label: 'Stocked', status: 'future' }
    ];

    if (['sent', 'acknowledged', 'partial'].includes(po.status?.toLowerCase())) {
      return {
        currentStage: 'Receive Goods',
        completedStages: ['approved'],
        recommendedAction: `Receive PO ${po.po_number || 'Goods'}`,
        reason: `Purchase order ${po.po_number || ''} is acknowledged and goods are expected. Process the Goods Receipt Note (GRN).`,
        priority,
        warnings,
        progress,
        actionId: AssistantAction.RECEIVE_GOODS,
        pulseActionId: 'receive_goods',
        route: { module: 'Procurement', destination: 'GRN_New', id: po.po_number },
        dueDate: po.expected_date,
        roles: ['admin', 'manager', 'storekeeper']
      };
    }

    return null;
  }
}
