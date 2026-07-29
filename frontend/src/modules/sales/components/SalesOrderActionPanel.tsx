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
import { AssistantButton } from '@/components/shared/assistant/AssistantButton';
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

import { AssistantGuidance } from '@/components/shared/assistant/AssistantTypes';

interface SalesOrderActionPanelProps {
  order: SalesOrder;
  actionLoading: boolean;
  confirmError: string | null;
  onAction: (action: string) => void;
  linkedWorkOrders?: Array<{ id: string; work_order_number: string; status: string }>;
  guidance?: AssistantGuidance | null;
}

const ACTION_ICONS: Record<string, React.ReactNode> = {
  submit: <Clock className="mr-2 h-4 w-4" />,
  approve: <CheckCircle className="mr-2 h-4 w-4" />,
  reject: <XCircle className="mr-2 h-4 w-4" />,
  confirm: <CheckCircle className="mr-2 h-4 w-4" />,
  create_delivery: <Truck className="mr-2 h-4 w-4" />,
  create_invoice: <CreditCard className="mr-2 h-4 w-4" />,
  record_payment: <CreditCard className="mr-2 h-4 w-4" />,
};

const ACTION_COLORS: Record<string, string> = {
  submit: 'bg-blue-600 hover:bg-blue-700',
  approve: 'bg-green-600 hover:bg-green-700',
  confirm: 'bg-indigo-600 hover:bg-indigo-700',
  create_delivery: 'bg-teal-600 hover:bg-teal-700',
  create_invoice: 'bg-emerald-600 hover:bg-emerald-700',
  record_payment: 'bg-cyan-600 hover:bg-cyan-700',
};

export default function SalesOrderActionPanel({
  order,
  actionLoading,
  confirmError,
  onAction,
  linkedWorkOrders = [],
  guidance,
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
          <div className="rounded-md border border-violet-200 bg-violet-50 px-4 py-3 space-y-3">
            <div className="flex items-start gap-2 text-violet-800">
              <Info className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">Work Orders Created — Production Planning in Progress</p>
                <p className="text-sm mt-1">
                  Insufficient finished goods stock was found at confirmation. Work orders have been
                  created to manufacture the required quantities. This order will move to{' '}
                  <strong>Ready for Dispatch</strong> automatically once production is complete and QC approved.
                </p>
              </div>
            </div>

            {/* Per-line shortfall breakdown */}
            {order.lines.some(l => (l.shortfall_quantity ?? 0) > 0) && (
              <div className="rounded border border-violet-200 bg-white overflow-hidden text-sm">
                <table className="w-full">
                  <thead className="bg-violet-100 text-violet-700">
                    <tr>
                      <th className="px-3 py-1.5 text-left font-medium">Product</th>
                      <th className="px-3 py-1.5 text-right font-medium">Ordered</th>
                      <th className="px-3 py-1.5 text-right font-medium">In Stock</th>
                      <th className="px-3 py-1.5 text-right font-medium text-amber-700">To Produce</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.lines.filter(l => (l.shortfall_quantity ?? 0) > 0).map(l => (
                      <tr key={l.id} className="border-t border-violet-100">
                        <td className="px-3 py-1.5 text-gray-800">
                          {l.product_name || l.product_code || l.product_id}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums">{l.quantity}</td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-green-700">
                          {l.quantity - (l.shortfall_quantity ?? 0)}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums font-semibold text-amber-700">
                          {l.shortfall_quantity}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* WO links */}
            {linkedWorkOrders.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {linkedWorkOrders.map((wo) => (
                  <a
                    key={wo.id}
                    href={`/work-orders/${wo.id}`}
                    className="inline-flex items-center gap-1 text-sm text-violet-700 hover:text-violet-900 underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    {wo.work_order_number}
                    <Badge variant="outline" className="ml-1 text-[10px] py-0">{wo.status}</Badge>
                  </a>
                ))}
              </div>
            )}
            {linkedWorkOrders.length === 0 && (
              <p className="text-sm text-violet-600 italic">
                Go to <strong>Manufacturing → Work Orders</strong> to release and track production.
              </p>
            )}
          </div>
        )}

        {/* Contextual info panel for PRODUCTION / CONFIRMED-with-shortage status */}
        {(order.status === OrderStatus.PRODUCTION || order.status === OrderStatus.CONFIRMED) && (
          <div className="rounded-md border border-yellow-200 bg-yellow-50 px-4 py-3 space-y-3">
            <div className="flex items-start gap-2 text-yellow-800">
              <Info className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">Production Required — Waiting for Manufacturing</p>
                <p className="text-sm mt-1">
                  This order cannot be dispatched yet. The following quantities are pending production.
                  Once work orders are completed and QC approved, finished goods will be received into
                  inventory and this order will move to <strong>Ready for Dispatch</strong> automatically.
                </p>
              </div>
            </div>

            {/* Per-line shortfall breakdown */}
            {order.lines.some(l => (l.shortfall_quantity ?? 0) > 0 || l.production_required) && (
              <div className="rounded border border-yellow-200 bg-white overflow-hidden text-sm">
                <table className="w-full">
                  <thead className="bg-yellow-100 text-yellow-800">
                    <tr>
                      <th className="px-3 py-1.5 text-left font-medium">Product</th>
                      <th className="px-3 py-1.5 text-right font-medium">Ordered</th>
                      <th className="px-3 py-1.5 text-right font-medium">Available</th>
                      <th className="px-3 py-1.5 text-right font-medium">Reserved</th>
                      <th className="px-3 py-1.5 text-right font-medium text-red-700">Shortfall</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.lines.map(l => {
                      const shortfall = l.shortfall_quantity ?? 0
                      const allocated = l.allocated_qty ?? 0
                      const available = allocated  // what was reserved from existing stock
                      return (
                        <tr key={l.id} className="border-t border-yellow-100">
                          <td className="px-3 py-1.5 text-gray-800">
                            {l.product_name || l.product_code || l.product_id}
                          </td>
                          <td className="px-3 py-1.5 text-right tabular-nums">{l.quantity}</td>
                          <td className="px-3 py-1.5 text-right tabular-nums text-green-700">{available}</td>
                          <td className="px-3 py-1.5 text-right tabular-nums text-blue-700">{allocated}</td>
                          <td className={`px-3 py-1.5 text-right tabular-nums font-semibold ${shortfall > 0 ? 'text-red-700' : 'text-green-700'}`}>
                            {shortfall > 0 ? shortfall : '✓'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Next step guidance */}
            <div className="text-sm text-yellow-800 bg-yellow-100 rounded px-3 py-2">
              <strong>Next step:</strong> Go to{' '}
              <a href="/work-orders" className="underline font-medium text-yellow-900 hover:text-yellow-700">
                Manufacturing → Work Orders
              </a>{' '}
              to release the work order, issue materials to the storekeeper, run production, and submit for QC.
            </div>

            {linkedWorkOrders.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {linkedWorkOrders.map((wo) => (
                  <a
                    key={wo.id}
                    href={`/work-orders/${wo.id}`}
                    className="inline-flex items-center gap-1 text-sm text-yellow-800 hover:text-yellow-900 underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    {wo.work_order_number}
                    <Badge variant="outline" className="ml-1 text-[10px] py-0">{wo.status}</Badge>
                  </a>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action buttons */}
        {!isCompleted && !isCancelled && actions.length > 0 && (
          <div className="flex gap-3 flex-wrap">
            {actions.map((actionConfig) => (
              <AssistantButton
                key={actionConfig.action}
                onClick={() => onAction(actionConfig.action)}
                disabled={actionLoading}
                pulse={guidance?.pulseActionId === actionConfig.action}
                variant={actionConfig.variant === 'destructive' ? 'destructive' : undefined}
                className={
                  actionConfig.variant !== 'destructive'
                    ? ACTION_COLORS[actionConfig.action] || ''
                    : ''
                }
              >
                {ACTION_ICONS[actionConfig.action]}
                {actionConfig.label}
              </AssistantButton>
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
