import { WorkflowStage } from "@/components/shared/assistant/AssistantTypes";

/**
 * Visual stages for Manufacturing Workflow
 * Note: These do not map 1:1 with backend statuses.
 */
export const MANUFACTURING_WORKFLOW_STAGES = [
  { id: 'planning', label: 'Planning' },
  { id: 'materials', label: 'Materials Ready' },
  { id: 'production', label: 'Production' },
  { id: 'quality', label: 'Quality' },
  { id: 'finished_goods', label: 'Finished Goods' },
  { id: 'completed', label: 'Completed' }
] as const;

export function buildManufacturingProgress(
  currentStageId: typeof MANUFACTURING_WORKFLOW_STAGES[number]['id'],
  completedIds: string[]
): WorkflowStage[] {
  return MANUFACTURING_WORKFLOW_STAGES.map(stage => {
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
