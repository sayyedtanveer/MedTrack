import { WorkflowStage } from '@/components/shared/assistant/AssistantTypes';

export const SalesWorkflowStages = [
  { id: 'draft', label: 'Draft', status: 'future' },
  { id: 'approved', label: 'Approved', status: 'future' },
  { id: 'confirmed', label: 'Confirmed', status: 'future' },
  { id: 'production', label: 'Production', status: 'future' },
  { id: 'dispatch', label: 'Dispatch', status: 'future' }
] as const;

export function buildSalesProgress(currentStageId: string, completedIds: string[]): WorkflowStage[] {
  return SalesWorkflowStages.map(stage => ({
    id: stage.id,
    label: stage.label,
    status: stage.id === currentStageId ? 'current' : completedIds.includes(stage.id) ? 'completed' : 'future'
  }));
}
