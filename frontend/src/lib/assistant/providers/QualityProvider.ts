import { AssistantGuidance, IAssistantProvider, AssistantAction, AssistantPriority } from '@/components/shared/assistant/AssistantTypes';
import { buildManufacturingProgress } from '../definitions/ManufacturingWorkflow';

export class QualityProvider implements IAssistantProvider<any> {
  canHandle(entity: any): boolean {
    return entity && entity.type === 'qc_batch';
  }

  getGuidance(batch: any): AssistantGuidance | null {
    if (!batch) return null;

    let priority: AssistantPriority = 'medium';
    let action = AssistantAction.VIEW_INSPECTIONS;
    let message = 'Batch is awaiting quality inspection.';
    let dueDateStr: string | null = batch.due_date || null;
    const warnings: string[] = [];

    // Calculate Rework/Scrap percentage
    const produced = Number(batch.produced_quantity) || 0;
    const scrapped = Number(batch.scrap_quantity) || 0;
    
    if (produced > 0 && (scrapped / produced) > 0.1) {
      priority = 'critical';
      warnings.push(`High Scrap Rate: ${((scrapped / produced) * 100).toFixed(1)}% of batch was scrapped.`);
      message = 'High scrap rate detected. Urgent inspection required.';
    }

    // Check aging (Aging rule: Overdue based on due date)
    if (batch.due_date) {
      const due = new Date(batch.due_date);
      const now = new Date();
      if (due < now) {
        priority = 'high';
        warnings.push('This batch is overdue for inspection.');
      }
    }

    if (batch.status === 'QC_REJECTED') {
      priority = 'high';
      message = 'Batch was rejected and needs disposition (Rework or Scrap).';
    }

    if (batch.status === 'REWORK') {
      priority = 'medium';
      message = 'Batch is currently flagged for rework.';
    }

    // Since QC is a queue, we guide the user to the QC Dashboard for this specific item if possible
    return {
      currentStage: 'Quality',
      completedStages: ['planning', 'materials', 'production'],
      recommendedAction: batch.status === 'QC_PENDING' ? 'Inspect Batch' : 'Review Disposition',
      reason: message,
      priority,
      warnings,
      progress: buildManufacturingProgress('quality', ['planning', 'materials', 'production']),
      actionId: action,
      route: { module: 'Quality', destination: 'Dashboard', id: batch.work_order_id },
      dueDate: dueDateStr,
      roles: ['admin', 'manager', 'qc']
    };
  }
}
