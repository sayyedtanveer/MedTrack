/**
 * SalesOrderActionPanel
 * Renders status-driven action buttons and contextual info panels for a Sales Order.
 * 
 * - DRAFT → Submit for Approval
 * - PENDING_APPROVAL → Approve / Reject
 * - APPROVED → Confirm & Execute (with inline error for credit/inventory failures)
 * - READY_FOR_DISPATCH → Create Delivery Note
 * - INVOICED → Record Payment
 * - PRODUCTION / WORK_ORDER_CREATED → Contextual info panels with WO links
 * - COMPLETED → "Completed" badge, actions disabled
 *
 * Requirements: 11.1–11.8, 3.8
 */

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SalesOrder, OrderStatus } from '@/types/sales.types';
import { STATUS_ACTIONS, CANCELLABLE_STATUSES } from './SalesOrderStatusConfig';
import {
  Clock,
  CheckCircle,
  XCircle,
  Truck,
  CreditCard,
  AlertCircle,
  ExternalLink,
  Info,
} from 'lucide-react';

interface SalesOrderActionPanelProps {
  order: SalesOrder;
  actionLoading: boolean;
  confirmError: string | null;
  onAction: (action: string) => void;
  linkedWorkOrders?: Array<{ id: string; work_order_number: string; status: string }>;
}

const ACTION_ICONS: Record<string, React.ReactNode> = {
  submit: <Clock className="mr-2 h-4 w-4" />,
  approve: <CheckCircle className="mr-2 h-4 w-4" />,
  reject: <XCircle className="mr-2 h-4 w-4" />,
  confirm: <CheckCircle className="mr-2 h-4 w-4" />,
  create_delivery: <Truck className="mr-2 h-4 w-4" />,
  record_payment: <CreditCard className="mr-2 h-4 w-4" />,
};

const ACTION_COLORS: Record<string, string> = {
  submit: 'bg-blue-600 hover:bg-blue-700',
  approve: 'bg-green-600 hover:bg-green-700',
  confirm: 'bg-indigo-600 hover:bg-indigo-700',
  create_delivery: 'bg-teal-600 hover:bg-teal-700',
  record_payment: 'bg-cyan-600 hover:bg-cyan-700',
};

export default function SalesOrderActionPanel({
  order,
  actionLoading,
  confirmError,
  onAction,
  linkedWorkOrders = [],
}: SalesOrderActionPanelProps) {
  const actions = STATUS_ACTIONS[order.status] || [];
  const isCancellable = CANCELLABLE_STATUSES.includes(order.status);
  const isCompleted = order.status === OrderStatus.COMPLETED;
  const isCancelled = order.status === OrderStatus.CANCELLED;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Order Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Completed badge */}
        {isCompleted && (
          <div className="flex items-center gap-2">
            <Badge className="bg-emerald-100 text-emerald-700 text-sm px-3 py-1">
              <CheckCircle className="mr-1 h-4 w-4" />
              Completed
            </Badge>
            <span className="text-sm text-gray-500">All actions are disabled for completed orders.</span>
          </div>
        )}

        {/* Cancelled badge — all actions disabled (Req 18.5) */}
        {isCancelled && (
          <div className="flex items-center gap-2">
            <Badge className="bg-red-100 text-red-700 text-sm px-3 py-1">
              <XCircle className="mr-1 h-4 w-4" />
              Cancelled
            </Badge>
            <span className="text-sm text-gray-500">This order has been cancelled. All actions are disabled.</span>
          </div>
        )}

        {/* Inline error for confirmation flow failures (credit/inventory) */}
        {confirmError && order.status === OrderStatus.APPROVED && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Confirmation failed</p>
              <p className="text-sm mt-1">{confirmError}</p>
            </div>
          </div>
        )}

        {/* Contextual info panel for WORK_ORDER_CREATED status */}
        {order.status === OrderStatus.WORK_ORDER_CREATED && (
          <div className="flex items-start gap-2 bg-violet-50 border border-violet-200 text-violet-800 px-4 py-3 rounded">
            <Info className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Manufacturing is being planned</p>
              <p className="text-sm mt-1">
                Work orders have been created for this sales order. Production planning is in progress.
              </p>
              {linkedWorkOrders.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {linkedWorkOrders.map((wo) => (
                    <a
                      key={wo.id}
                      href={`/manufacturing/work-orders/${wo.id}`}
                      className="inline-flex items-center gap-1 text-sm text-violet-700 hover:text-violet-900 underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                      {wo.work_order_number}
                    </a>
                  ))}
                </div>
              )}
              {linkedWorkOrders.length === 0 && (
                <p className="text-sm mt-1 text-violet-600 italic">No work order links available.</p>
              )}
            </div>
          </div>
        )}

        {/* Contextual info panel for PRODUCTION status */}
        {order.status === OrderStatus.PRODUCTION && (
          <div className="flex items-start gap-2 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded">
            <Info className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Waiting for manufacturing to complete</p>
              <p className="text-sm mt-1">
                Production is currently in progress for linked work orders.
              </p>
              {linkedWorkOrders.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {linkedWorkOrders.map((wo) => (
                    <a
                      key={wo.id}
                      href={`/manufacturing/work-orders/${wo.id}`}
                      className="inline-flex items-center gap-1 text-sm text-yellow-700 hover:text-yellow-900 underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                      {wo.work_order_number}
                    </a>
                  ))}
                </div>
              )}
              {linkedWorkOrders.length === 0 && (
                <p className="text-sm mt-1 text-yellow-600 italic">No work order links available.</p>
              )}
            </div>
          </div>
        )}

        {/* Action buttons */}
        {!isCompleted && !isCancelled && actions.length > 0 && (
          <div className="flex gap-3 flex-wrap">
            {actions.map((actionConfig) => (
              <Button
                key={actionConfig.action}
                onClick={() => onAction(actionConfig.action)}
                disabled={actionLoading}
                variant={actionConfig.variant === 'destructive' ? 'destructive' : undefined}
                className={
                  actionConfig.variant !== 'destructive'
                    ? ACTION_COLORS[actionConfig.action] || ''
                    : ''
                }
              >
                {ACTION_ICONS[actionConfig.action]}
                {actionConfig.label}
              </Button>
            ))}
          </div>
        )}

        {/* Cancel button for cancellable statuses (Req 18.5) */}
        {!isCompleted && !isCancelled && isCancellable && (
          <div className="pt-2 border-t">
            <Button
              variant="outline"
              onClick={() => onAction('cancel')}
              disabled={actionLoading}
            >
              Cancel Order
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
