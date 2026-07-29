import { AssistantGuidance, IAssistantProvider, AssistantAction, AssistantPriority, WorkflowStage } from '@/components/shared/assistant/AssistantTypes';

export class DispatchProvider implements IAssistantProvider<any> {
  canHandle(entity: any): boolean {
    return entity && entity.type === 'dispatch_order';
  }

  getGuidance(order: any): AssistantGuidance | null {
    if (!order) return null;

    let priority: AssistantPriority = 'medium';
    let warnings: string[] = [];
    
    // Evaluate aging / due date
    if (order.due_date) {
      const due = new Date(order.due_date);
      const now = new Date();
      if (due < now) {
        priority = 'high';
        warnings.push('This order is overdue for dispatch.');
      } else if (due.toDateString() === now.toDateString()) {
        priority = 'high';
      }
    }

    const progress: WorkflowStage[] = [
      { id: 'confirmed', label: 'Confirmed', status: 'completed' },
      { id: 'dispatch', label: 'Dispatch', status: 'current' },
      { id: 'delivered', label: 'Delivered', status: 'future' }
    ];

    if (order.status === 'CONFIRMED' || order.status === 'PARTIAL_DISPATCH') {
      return {
        currentStage: 'Dispatch',
        completedStages: ['confirmed'],
        recommendedAction: 'Dispatch Orders',
        reason: 'Order is ready for dispatch to the customer.',
        priority,
        warnings,
        progress,
        actionId: AssistantAction.DISPATCH_ORDERS,
        route: { module: 'Delivery', destination: 'DispatchQueue' },
        dueDate: order.due_date,
        roles: ['admin', 'manager', 'storekeeper']
      };
    }

    return null;
  }
}
