import { WorkflowStage } from "@/components/shared/assistant/AssistantTypes";

/**
 * Standard Purchase Order Lifecycle
 */
export const PROCUREMENT_WORKFLOW_STAGES = [
  { id: 'draft', label: 'Draft' },
  { id: 'sent', label: 'Sent to Supplier' },
  { id: 'acknowledged', label: 'Acknowledged' },
  { id: 'partial', label: 'Partially Received' },
  { id: 'completed', label: 'Completed' }
] as const;

export function buildProcurementProgress(
  currentStageId: typeof PROCUREMENT_WORKFLOW_STAGES[number]['id'],
  completedIds: string[]
): WorkflowStage[] {
  return PROCUREMENT_WORKFLOW_STAGES.map(stage => {
    let status: 'completed' | 'current' | 'future' = 'future';
    
    if (completedIds.includes(stage.id)) {
      status = 'completed';
    }
    
    if (stage.id === currentStageId) {
      status = 'current';
    }

    return { ...stage, status };
  });
}
