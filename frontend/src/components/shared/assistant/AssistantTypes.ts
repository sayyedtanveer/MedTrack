export type AssistantPriority = 'critical' | 'high' | 'medium' | 'low' | 'info';

export enum AssistantAction {
  SUBMIT_FOR_APPROVAL = 'SUBMIT_FOR_APPROVAL',
  APPROVE_ORDER = 'APPROVE_ORDER',
  CONFIRM_ORDER = 'CONFIRM_ORDER',
  EDIT_ORDER = 'EDIT_ORDER',
  CREATE_WORK_ORDER = 'CREATE_WORK_ORDER',
  ALLOCATE_STOCK = 'ALLOCATE_STOCK',
  VIEW_WORK_ORDERS = 'VIEW_WORK_ORDERS',
  GO_TO_DISPATCH = 'GO_TO_DISPATCH',
  VIEW_INVOICE = 'VIEW_INVOICE',
  CREATE_INVOICE = 'CREATE_INVOICE',
  RECORD_PAYMENT = 'RECORD_PAYMENT',
  GO_BACK = 'GO_BACK',
  SEND_PO = 'SEND_PO',
  ACKNOWLEDGE_PO = 'ACKNOWLEDGE_PO',
  RECEIVE_PO = 'RECEIVE_PO',
  RECEIVE_REMAINING = 'RECEIVE_REMAINING',
  
  // Manufacturing Phase 3
  RELEASE_WO = 'RELEASE_WO',
  ALLOCATE_MATERIALS = 'ALLOCATE_MATERIALS',
  REVIEW_MATERIAL_SHORTAGE = 'REVIEW_MATERIAL_SHORTAGE',
  START_PRODUCTION = 'START_PRODUCTION',
  COMPLETE_PRODUCTION = 'COMPLETE_PRODUCTION',
  REVIEW_BLOCKERS = 'REVIEW_BLOCKERS',
  GO_TO_QUALITY = 'GO_TO_QUALITY',
  RECEIVE_FG = 'RECEIVE_FG',
  COMPLETE_WO = 'COMPLETE_WO',
  RESUME_PRODUCTION = 'RESUME_PRODUCTION',

  // Phase 4
  VIEW_INSPECTIONS = 'VIEW_INSPECTIONS',
  RECEIVE_GOODS = 'RECEIVE_GOODS',
  DISPATCH_ORDERS = 'DISPATCH_ORDERS'
}

export interface WorkflowStage {
  id: string;
  label: string;
  status: 'completed' | 'current' | 'future';
}

import { NavigationDestination } from '../../../lib/assistant/NavigationRegistry';

export interface AssistantBlocker {
  type: string;
  reason: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

export interface AssistantGuidance {
  currentStage: string;
  completedStages: string[];
  recommendedAction: string;
  reason: string;
  priority: AssistantPriority;
  estimatedTime?: string;
  warnings: string[];
  blockers?: AssistantBlocker[];
  confidence?: number;
  progress: WorkflowStage[];
  actionId?: AssistantAction;
  route?: NavigationDestination;
  pulseActionId?: string; // Links action back to UI mapped string
  dueDate?: string | null; // For inbox priority sorting (Overdue, Due Today)
  roles?: string[]; // E.g., ['admin', 'manager', 'storekeeper'] for filtering in Inbox
}

export interface IAssistantProvider<T = any> {
  canHandle(entity: any): boolean;
  getGuidance(document: T): AssistantGuidance | null;
}
