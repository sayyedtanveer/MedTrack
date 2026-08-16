import { SalesOrder, OrderStatus } from '@/types/sales.types';
import { AssistantGuidance, IAssistantProvider, AssistantAction } from '@/components/shared/assistant/AssistantTypes';
import { buildSalesProgress } from '../definitions/SalesWorkflow';

export class SalesProvider implements IAssistantProvider<SalesOrder> {
  canHandle(entity: any): boolean {
    return entity && 'order_number' in entity && 'client_id' in entity;
  }

  getGuidance(order: SalesOrder): AssistantGuidance | null {
    if (!order) return null;

    let guidance: Partial<AssistantGuidance> = { warnings: [] };

    switch (order.status) {
      case OrderStatus.DRAFT:
        const hasMissingPrices = order.lines.some(l => l.unit_price <= 0);
        if (hasMissingPrices) {
          guidance.warnings!.push('One or more items have a price of 0. Please check the price list.');
        }

        guidance = {
          ...guidance,
          currentStage: 'Draft',
          completedStages: [],
          recommendedAction: `Submit SO ${order.order_number || ''}`,
          reason: `Sales Order ${order.order_number || ''} is drafted and requires managerial approval before it can be confirmed.`,
          priority: 'high',
          progress: buildSalesProgress('draft', []),
          actionId: AssistantAction.SUBMIT_FOR_APPROVAL,
          pulseActionId: 'submit',
        };
        break;

      case OrderStatus.PENDING_APPROVAL:
        guidance = {
          ...guidance,
          currentStage: 'Pending Approval',
          completedStages: ['draft'],
          recommendedAction: `Approve SO ${order.order_number || ''}`,
          reason: `Waiting for an authorized user to review and approve the commercial terms for ${order.order_number || ''}.`,
          priority: 'high',
          progress: buildSalesProgress('approved', ['draft']),
          actionId: AssistantAction.APPROVE_ORDER,
          pulseActionId: 'approve'
        };
        break;

      case OrderStatus.APPROVED:
        guidance = {
          ...guidance,
          currentStage: 'Approved',
          completedStages: ['draft', 'approved'],
          recommendedAction: `Confirm SO ${order.order_number || ''}`,
          reason: `Sales Order ${order.order_number || ''} is approved. Confirm it to lock the details and initiate fulfillment or manufacturing.`,
          priority: 'high',
          progress: buildSalesProgress('confirmed', ['draft', 'approved']),
          actionId: AssistantAction.CONFIRM_ORDER,
          pulseActionId: 'confirm'
        };
        break;

      case OrderStatus.REJECTED:
        guidance = {
          ...guidance,
          currentStage: 'Rejected',
          completedStages: [],
          recommendedAction: `Review Rejection for ${order.order_number || ''}`,
          reason: `Sales Order ${order.order_number || ''} was rejected. Review the notes and edit the draft to resubmit.`,
          priority: 'high',
          progress: buildSalesProgress('draft', []),
          actionId: AssistantAction.EDIT_ORDER
        };
        break;

      case OrderStatus.CONFIRMED:
      case OrderStatus.PROCESSING:
        const requiresProduction = order.lines.some(l => l.production_required);
        
        if (requiresProduction) {
          guidance = {
            ...guidance,
            currentStage: 'Confirmed',
            completedStages: ['draft', 'approved', 'confirmed'],
            recommendedAction: `Create WO for ${order.order_number || ''}`,
            reason: `Sales Order ${order.order_number || ''} requires manufacturing. Generate a Work Order to send it to the shop floor.`,
            priority: 'high',
            progress: buildSalesProgress('production', ['draft', 'approved', 'confirmed']),
            actionId: AssistantAction.CREATE_WORK_ORDER,
            pulseActionId: 'create_work_order'
          };
        } else {
          guidance = {
            ...guidance,
            currentStage: 'Confirmed',
            completedStages: ['draft', 'approved', 'confirmed'],
            recommendedAction: `Allocate Stock for ${order.order_number || ''}`,
            reason: `Items for ${order.order_number || ''} are available in inventory. Allocate stock to prepare for dispatch.`,
            priority: 'medium',
            progress: buildSalesProgress('production', ['draft', 'approved', 'confirmed']),
            actionId: AssistantAction.ALLOCATE_STOCK
          };
        }
        break;
        
      case OrderStatus.WORK_ORDER_CREATED:
      case OrderStatus.PRODUCTION:
        guidance = {
          ...guidance,
          currentStage: 'In Production',
          completedStages: ['draft', 'approved', 'confirmed'],
          recommendedAction: `Monitor Production for ${order.order_number || ''}`,
          reason: `Work orders for ${order.order_number || ''} have been created. Wait for the shop floor to complete production.`,
          priority: 'low',
          progress: buildSalesProgress('production', ['draft', 'approved', 'confirmed']),
          actionId: AssistantAction.VIEW_WORK_ORDERS,
          route: { module: 'Manufacturing', destination: 'WorkOrders' }
        };
        break;

      case OrderStatus.READY:
      case OrderStatus.READY_FOR_DISPATCH:
        guidance = {
          ...guidance,
          currentStage: 'Ready for Dispatch',
          completedStages: ['draft', 'approved', 'confirmed', 'production'],
          recommendedAction: `Dispatch SO ${order.order_number || ''}`,
          reason: `Goods for ${order.order_number || ''} are ready. Go to the Dispatch Queue to generate delivery notes and ship the order.`,
          priority: 'high',
          progress: buildSalesProgress('dispatch', ['draft', 'approved', 'confirmed', 'production']),
          actionId: AssistantAction.GO_TO_DISPATCH,
          route: { module: 'Sales', destination: 'DispatchQueue' }
        };
        break;

      case OrderStatus.SHIPPED:
      case OrderStatus.DELIVERED:
        guidance = {
          ...guidance,
          currentStage: 'Delivered',
          completedStages: ['draft', 'approved', 'confirmed', 'production', 'dispatch'],
          recommendedAction: `Generate Invoice for SO ${order.order_number || ''}`,
          reason: `Goods have been delivered. Generate an invoice to bill the client.`,
          priority: 'high',
          progress: buildSalesProgress('completed', ['draft', 'approved', 'confirmed', 'production', 'dispatch']),
          actionId: AssistantAction.CREATE_INVOICE,
          pulseActionId: 'create_invoice'
        };
        break;

      case OrderStatus.INVOICED:
        guidance = {
          ...guidance,
          currentStage: 'Invoiced',
          completedStages: ['draft', 'approved', 'confirmed', 'production', 'dispatch'],
          recommendedAction: `Record Payment for SO ${order.order_number || ''}`,
          reason: `Invoice generated. Record payment once received from the client.`,
          priority: 'medium',
          progress: buildSalesProgress('completed', ['draft', 'approved', 'confirmed', 'production', 'dispatch']),
          actionId: AssistantAction.RECORD_PAYMENT,
          pulseActionId: 'record_payment',
          route: { module: 'Sales', destination: 'SalesOrderDetail', id: order.id }
        };
        break;

      case OrderStatus.PAYMENT_RECEIVED:
      case OrderStatus.COMPLETED:
        guidance = {
          ...guidance,
          currentStage: 'Completed',
          completedStages: ['draft', 'approved', 'confirmed', 'production', 'dispatch'],
          recommendedAction: 'View Invoice',
          reason: 'The order has been fulfilled successfully.',
          priority: 'low',
          progress: buildSalesProgress('completed', ['draft', 'approved', 'confirmed', 'production', 'dispatch']),
          actionId: AssistantAction.VIEW_INVOICE
        };
        break;
        
      case OrderStatus.CANCELLED:
        guidance = {
          ...guidance,
          currentStage: 'Cancelled',
          completedStages: [],
          recommendedAction: 'None',
          reason: 'This order has been cancelled and requires no further action.',
          priority: 'low',
          progress: buildSalesProgress('draft', []), // Reset visual
          actionId: AssistantAction.GO_BACK
        };
        break;

      default:
        return null;
    }

    return guidance as AssistantGuidance;
  }
}
