/**
 * DispatchPanel Component
 *
 * Embedded in SalesOrderDetailPage for orders in READY_FOR_DISPATCH status.
 * Handles:
 * - Creating a delivery note (POST /deliveries) with partial-dispatch support
 * - Displaying all delivery notes for the SO with their statuses
 * - "Mark as Shipped" for DRAFT deliveries
 * - "Mark as Delivered" for SHIPPED deliveries
 * - No action buttons for DELIVERED deliveries
 * - Per-line quantity inputs with validation (≤ allocated - dispatched)
 * - API error handling via toast notification, retaining button state
 *
 * Requirements: 1.1–1.8, 20.1–20.7
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { StatusBadge } from '@/components/shared';
import { toast } from '@/hooks/use-toast';
import { apiClient } from '@/services/api-client';
import { deliveryService, type Delivery } from '@/services/delivery.service';
import type { SalesOrder, SalesOrderLine } from '@/types/sales.types';
import {
  Truck,
  Package,
  Plus,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Types ──────────────────────────────────────────────────────────────────

interface DispatchPanelProps {
  order: SalesOrder;
  /** Called when order status changes (e.g. after Mark as Delivered) */
  onOrderUpdate?: () => void;
}

/** Per-line dispatch quantity state for the create-delivery form */
type LineQuantities = Record<string, number>;

// ─── Delivery status color map ───────────────────────────────────────────────

const DELIVERY_STATUS_COLORS: Record<string, string> = {
  DRAFT: 'border-gray-200 bg-gray-50 text-gray-700',
  PACKING: 'border-amber-200 bg-amber-50 text-amber-700',
  SHIPPED: 'border-blue-200 bg-blue-50 text-blue-700',
  DELIVERED: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  CANCELLED: 'border-red-200 bg-red-50 text-red-700',
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Max dispatchable quantity for a line = allocated - dispatched */
function maxDispatchable(line: SalesOrderLine): number {
  const allocated = Number(line.allocated_qty ?? 0);
  const dispatched = Number(line.shipped_qty ?? 0);
  return Math.max(0, allocated - dispatched);
}

/** Default per-line quantities: fill with max dispatchable */
function defaultLineQuantities(lines: SalesOrderLine[]): LineQuantities {
  return Object.fromEntries(
    lines.map((l) => [l.id, maxDispatchable(l)])
  );
}

/** Build the POST /deliveries payload from the order and chosen quantities */
function buildCreateDeliveryPayload(
  order: SalesOrder,
  lineQuantities: LineQuantities
): object {
  const lines = order.lines
    .filter((l) => {
      const qty = lineQuantities[l.id] ?? 0;
      return qty > 0;
    })
    .map((l) => ({
      sales_order_line_id: l.id,
      quantity: lineQuantities[l.id] ?? 0,
    }));

  return {
    sales_order_id: order.id,
    lines,
  };
}

// ─── API hooks ───────────────────────────────────────────────────────────────

function useDeliveries(salesOrderId: string) {
  return useQuery<Delivery[]>({
    queryKey: ['deliveries', salesOrderId],
    queryFn: () => deliveryService.list({ sales_order_id: salesOrderId }),
    enabled: Boolean(salesOrderId),
    staleTime: 15_000,
  });
}

function useCreateDelivery(onSuccess: (d: Delivery) => void) {
  return useMutation<Delivery, Error, object>({
    mutationFn: async (payload: object) => {
      const { data } = await apiClient.post<Delivery>('/deliveries', payload);
      return data;
    },
    onSuccess,
  });
}

function useShipDelivery(salesOrderId: string) {
  const queryClient = useQueryClient();
  return useMutation<Delivery, Error, { deliveryId: string; carrier?: string; trackingNumber?: string }>({
    mutationFn: ({ deliveryId, carrier, trackingNumber }) =>
      deliveryService.ship(deliveryId, {
        carrier: carrier ?? undefined,
        tracking_number: trackingNumber ?? undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['deliveries', salesOrderId] });
    },
  });
}

function useDeliverDelivery(salesOrderId: string, onOrderUpdate?: () => void) {
  const queryClient = useQueryClient();
  return useMutation<Delivery, Error, string>({
    mutationFn: (deliveryId) => deliveryService.deliver(deliveryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['deliveries', salesOrderId] });
      onOrderUpdate?.();
    },
  });
}

// ─── CreateDeliveryForm ──────────────────────────────────────────────────────

interface CreateDeliveryFormProps {
  order: SalesOrder;
  onCreated: (delivery: Delivery) => void;
}

function CreateDeliveryForm({ order, onCreated }: CreateDeliveryFormProps) {
  const [expanded, setExpanded] = useState(false);
  const [lineQtys, setLineQtys] = useState<LineQuantities>(() =>
    defaultLineQuantities(order.lines)
  );
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const createMutation = useCreateDelivery((delivery) => {
    onCreated(delivery);
    toast({ title: 'Delivery note created', description: `Delivery ${delivery.delivery_number} created.` });
    setExpanded(false);
  });

  const handleQtyChange = useCallback(
    (lineId: string, value: string) => {
      const num = parseInt(value, 10);
      const line = order.lines.find((l) => l.id === lineId);
      if (!line) return;
      const max = maxDispatchable(line);
      const errors: Record<string, string> = { ...validationErrors };

      if (isNaN(num) || num < 0) {
        errors[lineId] = 'Enter a valid quantity';
      } else if (num > max) {
        // Req 20.7: reject quantities exceeding remaining dispatchable
        errors[lineId] = `Maximum dispatchable: ${max}`;
      } else {
        delete errors[lineId];
      }
      setValidationErrors(errors);
      setLineQtys((prev) => ({ ...prev, [lineId]: isNaN(num) ? 0 : num }));
    },
    [order.lines, validationErrors]
  );

  const hasAnyQty = Object.values(lineQtys).some((q) => q > 0);
  const hasErrors = Object.keys(validationErrors).length > 0;
  const canSubmit = hasAnyQty && !hasErrors && !createMutation.isPending;

  const handleSubmit = () => {
    if (!canSubmit) return;
    const payload = buildCreateDeliveryPayload(order, lineQtys);
    createMutation.mutate(payload, {
      onError: (err) => {
        // Req 1.3: show toast, retain button state
        toast({
          title: 'Could not create delivery',
          description: err.message,
          variant: 'destructive',
        });
      },
    });
  };

  // Lines that have remaining dispatchable qty
  const dispatchableLines = order.lines.filter((l) => maxDispatchable(l) > 0);

  if (dispatchableLines.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">All allocated quantities have been dispatched.</p>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-4 py-3 bg-teal-50 hover:bg-teal-100 transition-colors text-teal-800 font-medium text-sm"
      >
        <span className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Create Delivery Note
        </span>
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {expanded && (
        <div className="p-4 space-y-4 bg-white">
          {/* Per-line quantity inputs (Req 20.1) */}
          <div className="space-y-3">
            <p className="text-xs text-gray-500">
              Enter dispatch quantity per line (max = allocated − dispatched).
            </p>
            {dispatchableLines.map((line) => {
              const max = maxDispatchable(line);
              const val = lineQtys[line.id] ?? 0;
              const err = validationErrors[line.id];
              return (
                <div key={line.id} className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <Label className="text-sm font-medium text-gray-800 truncate block">
                      {line.product_name || line.product_id}
                    </Label>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Allocated: {Number(line.allocated_qty ?? 0)} &bull; Dispatched: {Number(line.shipped_qty ?? 0)} &bull; Remaining: {max}
                    </p>
                  </div>
                  <div className="w-28 shrink-0">
                    <Input
                      type="number"
                      min={0}
                      max={max}
                      value={val}
                      onChange={(e) => handleQtyChange(line.id, e.target.value)}
                      className={cn('text-right', err ? 'border-red-400 focus-visible:ring-red-400' : '')}
                    />
                    {err && <p className="text-xs text-red-500 mt-1">{err}</p>}
                  </div>
                </div>
              );
            })}
          </div>

          {createMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{createMutation.error?.message}</AlertDescription>
            </Alert>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setExpanded(false)} disabled={createMutation.isPending}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!canSubmit}
              onClick={handleSubmit}
              className="bg-teal-600 hover:bg-teal-700"
            >
              {createMutation.isPending ? 'Creating…' : 'Create Delivery Note'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── DeliveryRow ─────────────────────────────────────────────────────────────

interface DeliveryRowProps {
  delivery: Delivery;
  onShip: (id: string) => void;
  onDeliver: (id: string) => void;
  shipLoading: boolean;
  deliverLoading: boolean;
}

function DeliveryRow({ delivery, onShip, onDeliver, shipLoading, deliverLoading }: DeliveryRowProps) {
  const status = delivery.status.toUpperCase();

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-3 border rounded-lg bg-white hover:bg-gray-50 transition-colors">
      {/* Delivery info */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-sm text-gray-900">{delivery.delivery_number}</span>
          <StatusBadge status={status} colorMap={DELIVERY_STATUS_COLORS} />
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500">
          {delivery.carrier && (
            <span>
              <span className="font-medium text-gray-600">Carrier:</span> {delivery.carrier}
            </span>
          )}
          {delivery.tracking_number && (
            <span>
              <span className="font-medium text-gray-600">Tracking:</span> {delivery.tracking_number}
            </span>
          )}
          {delivery.shipped_at && (
            <span>
              <span className="font-medium text-gray-600">Shipped:</span>{' '}
              {new Date(delivery.shipped_at).toLocaleDateString()}
            </span>
          )}
          {delivery.delivered_at && (
            <span>
              <span className="font-medium text-gray-600">Delivered:</span>{' '}
              {new Date(delivery.delivered_at).toLocaleDateString()}
            </span>
          )}
        </div>
        {delivery.lines.length > 0 && (
          <p className="text-xs text-gray-400">
            {delivery.lines.length} line{delivery.lines.length !== 1 ? 's' : ''} &bull; Total qty:{' '}
            {delivery.lines.reduce((sum, l) => sum + l.quantity, 0)}
          </p>
        )}
      </div>

      {/* Action buttons — Req 1.5 */}
      <div className="shrink-0">
        {status === 'DRAFT' && (
          // Req 1.6: "Mark as Shipped" for DRAFT
          <Button
            size="sm"
            disabled={shipLoading}
            onClick={() => onShip(delivery.id)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Truck className="mr-2 h-4 w-4" />
            {shipLoading ? 'Shipping…' : 'Mark as Shipped'}
          </Button>
        )}
        {status === 'SHIPPED' && (
          // Req 1.8: "Mark as Delivered" for SHIPPED
          <Button
            size="sm"
            disabled={deliverLoading}
            onClick={() => onDeliver(delivery.id)}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <CheckCircle2 className="mr-2 h-4 w-4" />
            {deliverLoading ? 'Completing…' : 'Mark as Delivered'}
          </Button>
        )}
        {/* DELIVERED: no action buttons — Req 1.5 */}
      </div>
    </div>
  );
}

// ─── DispatchPanel (Main Export) ─────────────────────────────────────────────

export default function DispatchPanel({ order, onOrderUpdate }: DispatchPanelProps) {
  const queryClient = useQueryClient();
  const [shippingId, setShippingId] = useState<string | null>(null);
  const [deliveringId, setDeliveringId] = useState<string | null>(null);

  const {
    data: deliveries = [],
    isLoading: deliveriesLoading,
    isError: deliveriesError,
    refetch: refetchDeliveries,
  } = useDeliveries(order.id);

  const shipMutation = useShipDelivery(order.id);
  const deliverMutation = useDeliverDelivery(order.id, onOrderUpdate);

  const handleShip = useCallback(
    (deliveryId: string) => {
      setShippingId(deliveryId);
      shipMutation.mutate(
        { deliveryId },
        {
          onError: (err) => {
            // Req 1.7: toast error, retain button state
            toast({
              title: 'Could not mark as shipped',
              description: err.message,
              variant: 'destructive',
            });
          },
          onSettled: () => setShippingId(null),
        }
      );
    },
    [shipMutation]
  );

  const handleDeliver = useCallback(
    (deliveryId: string) => {
      setDeliveringId(deliveryId);
      deliverMutation.mutate(deliveryId, {
        onError: (err) => {
          // Req 1.7: toast error, retain button state
          toast({
            title: 'Could not mark as delivered',
            description: err.message,
            variant: 'destructive',
          });
        },
        onSettled: () => setDeliveringId(null),
      });
    },
    [deliverMutation]
  );

  // Req 1.4: after delivery note created, refresh list
  const handleDeliveryCreated = useCallback(
    (_delivery: Delivery) => {
      void queryClient.invalidateQueries({ queryKey: ['deliveries', order.id] });
    },
    [queryClient, order.id]
  );

  return (
    <Card data-testid="dispatch-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Package className="h-5 w-5 text-teal-600" />
          Dispatch Panel
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Per-line dispatch tracking — Req 20.3 */}
        <DispatchLineTracking order={order} />

        {/* Create delivery note form — Req 1.2, 20.1 */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Create Delivery Note</h4>
          <CreateDeliveryForm order={order} onCreated={handleDeliveryCreated} />
        </div>

        {/* Delivery notes list — Req 1.4, 20.4 */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Delivery Notes
            {deliveries.length > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-500">
                ({deliveries.length})
              </span>
            )}
          </h4>

          {deliveriesLoading && (
            <div className="space-y-2">
              {[1, 2].map((n) => (
                <div key={n} className="h-16 rounded-lg bg-gray-100 animate-pulse" />
              ))}
            </div>
          )}

          {deliveriesError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center gap-2">
                Could not load delivery notes.
                <button
                  type="button"
                  onClick={() => void refetchDeliveries()}
                  className="underline text-sm"
                >
                  Retry
                </button>
              </AlertDescription>
            </Alert>
          )}

          {!deliveriesLoading && !deliveriesError && deliveries.length === 0 && (
            <p className="text-sm text-gray-500 italic py-2">
              No delivery notes yet. Use "Create Delivery Note" above to initiate dispatch.
            </p>
          )}

          {!deliveriesLoading && !deliveriesError && deliveries.length > 0 && (
            <div className="space-y-2">
              {deliveries.map((delivery) => (
                <DeliveryRow
                  key={delivery.id}
                  delivery={delivery}
                  onShip={handleShip}
                  onDeliver={handleDeliver}
                  shipLoading={shippingId === delivery.id && shipMutation.isPending}
                  deliverLoading={deliveringId === delivery.id && deliverMutation.isPending}
                />
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── DispatchLineTracking ────────────────────────────────────────────────────

/**
 * Displays per-line tracking: ordered, allocated, dispatched, remaining.
 * Requirement 20.3
 */
function DispatchLineTracking({ order }: { order: SalesOrder }) {
  if (order.lines.length === 0) return null;

  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-700 mb-2">Line Dispatch Tracking</h4>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b text-gray-600">
              <th className="px-3 py-2 text-left font-medium">Product</th>
              <th className="px-3 py-2 text-right font-medium">Ordered</th>
              <th className="px-3 py-2 text-right font-medium">Allocated</th>
              <th className="px-3 py-2 text-right font-medium">Dispatched</th>
              <th className="px-3 py-2 text-right font-medium">Remaining</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((line) => {
              const ordered = Number(line.quantity ?? 0);
              const allocated = Number(line.allocated_qty ?? 0);
              const dispatched = Number(line.shipped_qty ?? 0);
              const remaining = Math.max(0, allocated - dispatched);
              const isFullyDispatched = remaining === 0 && allocated > 0;

              return (
                <tr
                  key={line.id}
                  className={cn(
                    'border-b hover:bg-gray-50',
                    isFullyDispatched ? 'opacity-60' : ''
                  )}
                >
                  <td className="px-3 py-2">
                    <span className="font-medium text-gray-800">
                      {line.product_name || line.product_id}
                    </span>
                    {line.product_code && (
                      <span className="block text-gray-400">{line.product_code}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{ordered}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{allocated}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{dispatched}</td>
                  <td
                    className={cn(
                      'px-3 py-2 text-right tabular-nums font-semibold',
                      remaining > 0 ? 'text-amber-600' : 'text-emerald-600'
                    )}
                  >
                    {remaining}
                    {isFullyDispatched && (
                      <CheckCircle2 className="inline ml-1 h-3 w-3 text-emerald-500" />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
