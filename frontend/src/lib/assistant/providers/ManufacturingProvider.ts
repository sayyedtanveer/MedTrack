import { AssistantGuidance, IAssistantProvider, AssistantAction, AssistantBlocker } from '@/components/shared/assistant/AssistantTypes';
import { buildManufacturingProgress } from '../definitions/ManufacturingWorkflow';

interface ManufacturingConditions {
  canAllocateMaterials: boolean;
  fgReceived: boolean;
  qcApproved: boolean;
  blockers: AssistantBlocker[];
}

export class ManufacturingProvider implements IAssistantProvider<any> {
  canHandle(entity: any): boolean {
    return entity && 'work_order_number' in entity && 'produced_quantity' in entity;
  }

  private evaluateConditions(workOrder: any): ManufacturingConditions {
    const blockers: AssistantBlocker[] = [];

    // Evaluate material allocation possibility
    // If all materials have available_quantity >= required_quantity
    const materials = workOrder.materials || [];
    const canAllocateMaterials = materials.every((m: any) => 
      (m.allocated_quantity || 0) >= m.required_quantity || 
      (m.available_quantity || 0) >= (m.required_quantity - (m.allocated_quantity || 0))
    );

    if (workOrder.status === 'RELEASED' && !canAllocateMaterials) {
      blockers.push({
        type: 'Material Shortage',
        reason: 'Insufficient stock to fulfill all BOM requirements.',
        severity: 'high'
      });
    }

    if (workOrder.status === 'PRODUCTION_HOLD') {
      blockers.push({
        type: 'Production Hold',
        reason: workOrder.hold_reason || 'Production has been manually paused.',
        severity: 'critical'
      });
    }

    if (workOrder.status === 'REWORK') {
      blockers.push({
        type: 'Quality Reject',
        reason: 'Failed QC inspection. Rework is required.',
        severity: 'high'
      });
    }

    return {
      canAllocateMaterials,
      fgReceived: workOrder.status === 'FG_RECEIVED' || workOrder.status === 'COMPLETED',
      qcApproved: workOrder.status === 'QC_APPROVED' || workOrder.status === 'FG_RECEIVED' || workOrder.status === 'COMPLETED',
      blockers
    };
  }

  getGuidance(workOrder: any): AssistantGuidance | null {
    if (!workOrder) return null;

    const conditions = this.evaluateConditions(workOrder);
    let guidance: Partial<AssistantGuidance> | null = null;

    switch (workOrder.status) {
      case 'PLANNED':
        guidance = {
          currentStage: 'Planning',
          completedStages: [],
          recommendedAction: `Release Work Order ${workOrder.work_order_number || ''}`,
          reason: `Work Order ${workOrder.work_order_number || ''} is planned. Release it to request materials from the warehouse.`,
          priority: 'high',
          progress: buildManufacturingProgress('planning', []),
          actionId: AssistantAction.RELEASE_WO,
          pulseActionId: 'release',
          route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
        };
        break;

      case 'RELEASED':
      case 'MATERIAL_PENDING':
        if (conditions.canAllocateMaterials) {
          guidance = {
            currentStage: 'Materials Ready',
            completedStages: ['planning'],
            recommendedAction: `Allocate Materials for ${workOrder.work_order_number || ''}`,
            reason: `All required materials for ${workOrder.work_order_number || ''} are available in inventory. Allocate them to reserve the stock.`,
            priority: 'high',
            progress: buildManufacturingProgress('materials', ['planning']),
            actionId: AssistantAction.ALLOCATE_MATERIALS,
            pulseActionId: 'allocate_materials',
            route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
          };
        } else {
          guidance = {
            currentStage: 'Materials Ready',
            completedStages: ['planning'],
            recommendedAction: `Review Shortage for ${workOrder.work_order_number || ''}`,
            reason: `Materials for ${workOrder.work_order_number || ''} cannot be allocated due to insufficient inventory.`,
            priority: 'medium',
            progress: buildManufacturingProgress('materials', ['planning']),
            actionId: AssistantAction.REVIEW_MATERIAL_SHORTAGE,
            route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
          };
        }
        break;

      case 'MATERIAL_RESERVED':
      case 'MATERIAL_ISSUED':
        guidance = {
          currentStage: 'Materials Ready',
          completedStages: ['planning'],
          recommendedAction: `Start Production on ${workOrder.work_order_number || ''}`,
          reason: `Materials have been issued for ${workOrder.work_order_number || ''}. The shop floor can begin manufacturing.`,
          priority: 'high',
          progress: buildManufacturingProgress('materials', ['planning']),
          actionId: AssistantAction.START_PRODUCTION,
          pulseActionId: 'start',
          route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
        };
        break;

      case 'IN_PRODUCTION':
      case 'IN_PROGRESS':
        if (conditions.blockers.length === 0) {
          guidance = {
            currentStage: 'Production',
            completedStages: ['planning', 'materials'],
            recommendedAction: `Complete Production for ${workOrder.work_order_number || ''}`,
            reason: `Production of ${workOrder.work_order_number || ''} is running smoothly. Log your output when finished to trigger QC.`,
            priority: 'medium',
            progress: buildManufacturingProgress('production', ['planning', 'materials']),
            actionId: AssistantAction.COMPLETE_PRODUCTION,
            pulseActionId: 'complete',
            route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
          };
        } else {
          guidance = {
            currentStage: 'Production',
            completedStages: ['planning', 'materials'],
            recommendedAction: `Review Blockers for ${workOrder.work_order_number || ''}`,
            reason: `Production of ${workOrder.work_order_number || ''} cannot continue due to active blockers.`,
            priority: 'critical',
            progress: buildManufacturingProgress('production', ['planning', 'materials']),
            actionId: AssistantAction.REVIEW_BLOCKERS,
            route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
          };
        }
        break;

      case 'PRODUCTION_HOLD':
      case 'REWORK':
        guidance = {
          currentStage: 'Production',
          completedStages: ['planning', 'materials'],
          recommendedAction: `Resume Production on ${workOrder.work_order_number || ''}`,
          reason: `Resolve the blockers on ${workOrder.work_order_number || ''} to resume normal operations.`,
          priority: 'high',
          progress: buildManufacturingProgress('production', ['planning', 'materials']),
          actionId: AssistantAction.RESUME_PRODUCTION,
          route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
        };
        break;

      case 'QC_PENDING':
        guidance = {
          currentStage: 'Quality',
          completedStages: ['planning', 'materials', 'production'],
          recommendedAction: `Go to QC for ${workOrder.work_order_number || ''}`,
          reason: `Production is finished for ${workOrder.work_order_number || ''}. Awaiting quality inspection before goods can be received.`,
          priority: 'medium',
          progress: buildManufacturingProgress('quality', ['planning', 'materials', 'production']),
          actionId: AssistantAction.GO_TO_QUALITY,
          route: { module: 'Quality', destination: 'Dashboard', id: workOrder.id }
        };
        break;

      case 'QC_APPROVED':
        guidance = {
          currentStage: 'Quality',
          completedStages: ['planning', 'materials', 'production'],
          recommendedAction: `Receive FG for ${workOrder.work_order_number || ''}`,
          reason: `Quality has been approved for ${workOrder.work_order_number || ''}. Receive the items into the warehouse.`,
          priority: 'high',
          progress: buildManufacturingProgress('quality', ['planning', 'materials', 'production']),
          actionId: AssistantAction.RECEIVE_FG,
          pulseActionId: 'receive_fg',
          route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
        };
        break;

      case 'FG_RECEIVED':
        if (conditions.fgReceived) {
          guidance = {
            currentStage: 'Done',
            completedStages: ['planning', 'materials', 'production', 'quality'],
            recommendedAction: `Complete Work Order ${workOrder.work_order_number || ''}`,
            reason: `Finished Goods for ${workOrder.work_order_number || ''} are in the warehouse. Mark the Work Order as completed.`,
            priority: 'medium',
            progress: buildManufacturingProgress('completed', ['planning', 'materials', 'production', 'quality']),
            actionId: AssistantAction.COMPLETE_WO,
            pulseActionId: 'complete',
            route: { module: 'Manufacturing', destination: 'WorkOrderDetail', id: workOrder.id }
          };
        } else {
          guidance = {
            currentStage: 'Quality',
            completedStages: ['planning', 'materials', 'production'],
            recommendedAction: 'Receive Finished Goods',
            reason: 'System state inconsistency: Goods not fully received yet.',
            priority: 'high',
            progress: buildManufacturingProgress('quality', ['planning', 'materials', 'production']),
            actionId: AssistantAction.RECEIVE_FG,
            pulseActionId: 'receive_fg'
          };
        }
        break;

      case 'COMPLETED':
      case 'CLOSED':
        guidance = {
          currentStage: 'Completed',
          completedStages: ['planning', 'materials', 'production', 'quality', 'finished_goods'],
          recommendedAction: 'Go Back',
          reason: 'This work order is closed and fully costed.',
          priority: 'info',
          progress: buildManufacturingProgress('completed', ['planning', 'materials', 'production', 'quality', 'finished_goods']),
          actionId: AssistantAction.GO_BACK
        };
        break;

      case 'CANCELLED':
      case 'REJECTED':
        guidance = {
          currentStage: 'Closed/Cancelled',
          completedStages: [],
          recommendedAction: 'Go Back',
          reason: 'This order has been cancelled or permanently rejected.',
          priority: 'info',
          progress: buildManufacturingProgress('planning', []),
          actionId: AssistantAction.GO_BACK
        };
        break;
    }

    if (guidance) {
      guidance.warnings = []; // Initialize to empty
      if (conditions.blockers.length > 0) {
        guidance.blockers = conditions.blockers;
        // Also map critical blockers to legacy warnings array for compatibility
        guidance.warnings = conditions.blockers.map(b => `${b.type}: ${b.reason}`);
      }
      guidance.confidence = 1.0;
    }

    return guidance as AssistantGuidance;
  }
}
