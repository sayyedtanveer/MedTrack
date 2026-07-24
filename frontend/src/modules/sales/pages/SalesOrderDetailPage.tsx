/**
 * Sales Order Detail Page
 * View complete order details, line items, and perform status transitions
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CardSkeleton } from '@/components/shared/LoadingSkeleton';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { ordersApi } from '@/services/sales.service';
import { SalesOrder, OrderStatus } from '@/types/sales.types';
import { ArrowLeft, Edit2, Plus, MoreVertical } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { formatCurrency } from '@/utils/currency';
import { REALTIME_EVENT_NAME } from '@/components/notifications/RealtimeNotificationsBridge';
import SalesWorkflowTimeline from '@/modules/sales/components/SalesWorkflowTimeline';
import SalesOrderActionPanel from '@/modules/sales/components/SalesOrderActionPanel';
import DispatchPanel from '@/modules/sales/components/DispatchPanel';
import { SO_STATUS_COLOR_MAP } from '@/modules/sales/components/SalesOrderStatusConfig';
import { financeService, type Invoice } from '@/services/finance.service';
import { AuditHistoryTab } from '@/components/shared/AuditHistoryTab';
import { useToast } from '@/hooks/use-toast';
import { toast as sonnerToast } from 'sonner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import workOrderService from '@/services/work-order.service';
import { productService } from '@/services/product.service';
import type { ItemVariantSearchItem } from '@/types/bom.types';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Line Status Badge Colors (Req 19.3, 19.4)
const LINE_STATUS_COLORS: Record<string, string> = {
  PENDING: 'border-gray-200 bg-gray-50 text-gray-700',
  ALLOCATED: 'border-green-200 bg-green-50 text-green-700',
  PARTIAL: 'border-amber-200 bg-amber-50 text-amber-700',
  SHORT_CLOSED: 'border-red-200 bg-red-50 text-red-700',
  BACKORDER: 'border-purple-200 bg-purple-50 text-purple-700',
  CANCELLED: 'border-gray-200 bg-gray-100 text-gray-500',
};

export default function SalesOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast: _toast } = useToast();
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [shortCloseDialogOpen, setShortCloseDialogOpen] = useState(false);
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  // New Line Item State
  const [newLine, setNewLine] = useState({
    product_id: '',
    product_type: 'variant',
    uom_id: '',
    quantity: 1,
    tax_rate: 0
  });

  const [variants, setVariants] = useState<ItemVariantSearchItem[]>([]);

  useEffect(() => {
    productService.searchVariants({ is_active: true, page_size: 100 })
      .then(res => setVariants(res.items))
      .catch(console.error);
  }, []);

  const loadOrder = useCallback(async (silent = false) => {
    if (!id) return;
    try {
      setError(null);
      if (!silent) setLoading(true);
      const data = await ordersApi.get(id);
      setOrder(data);
      
      // Load invoice if order is INVOICED or later (Req 2.5, 2.6)
      if (data.status === OrderStatus.INVOICED || 
          data.status === OrderStatus.PAYMENT_RECEIVED || 
          data.status === OrderStatus.COMPLETED) {
        try {
          // Query invoices by client_id and find matching SO
          const invoices = await financeService.listInvoices({ client_id: data.client_id });
          const matchingInvoice = invoices.items.find(inv => inv.sales_order_id === data.id);
          if (matchingInvoice) {
            setInvoice(matchingInvoice);
          }
        } catch (err) {
          console.error('Failed to load invoice:', err);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load order');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadOrder();
  }, [loadOrder]);

  useEffect(() => {
    const handleRealtime = () => {
      void loadOrder(true);
    };
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime);
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime);
  }, [loadOrder]);

  const handleStatusChange = async (action: string) => {
    if (!order) return;

    // Handle cancel action - show dialog instead of executing immediately
    if (action === 'cancel') {
      setCancelDialogOpen(true);
      return;
    }

    setActionLoading(true);
    // Clear previous confirm error on a new action attempt
    if (action === 'confirm') setConfirmError(null);
    try {
      let updated: SalesOrder;
      switch (action) {
        case 'submit':
          updated = await ordersApi.submitForApproval(order.id);
          break;
        case 'approve':
          updated = await ordersApi.approve(order.id);
          break;
        case 'reject':
          updated = await ordersApi.reject(order.id);
          break;
        case 'confirm':
          updated = await ordersApi.confirm(order.id);
          break;
        case 'ship':
          updated = await ordersApi.ship(order.id, {
            line_shipments: Object.fromEntries(order.lines.map((line) => [line.id, line.allocated_qty])),
          });
          break;
        case 'deliver':
          updated = await ordersApi.deliver(order.id);
          break;
        case 'create_delivery':
          // Navigates to the DispatchPanel / Delivery creation flow
          navigate(`/sales/orders/${order.id}/delivery/new`);
          return;
        case 'record_payment':
          // Navigates to the payment recording flow
          navigate(`/sales/orders/${order.id}/payment`);
          return;
        default:
          return;
      }
      setOrder(updated);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Action failed';
      if (action === 'confirm') {
        setConfirmError(message);
        sonnerToast.error('Order Confirmation Failed', { description: message });
      } else {
        setError(message);
        sonnerToast.error('Action Failed', { description: message });
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Handler: Confirm Cancellation (Req 18.5, 18.7)
  const handleConfirmCancellation = async () => {
    if (!order) return;
    
    setActionLoading(true);
    try {
      const updated = await ordersApi.cancel(order.id, cancelReason || undefined);
      setOrder(updated);
      setError(null);
      setCancelDialogOpen(false);
      setCancelReason('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel order');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddLine = async () => {
    if (!order || !newLine.product_id || !newLine.uom_id || newLine.quantity <= 0) {
      setError('Please provide product ID, UOM ID, and a valid quantity');
      return;
    }
    setActionLoading(true);
    try {
      const updated = await ordersApi.addLine(order.id, {
        product_id: newLine.product_id,
        product_type: newLine.product_type as 'variant' | 'finished_product',
        uom_id: newLine.uom_id,
        quantity: newLine.quantity,
        tax_rate: newLine.tax_rate,
      });
      setOrder(updated);
      setNewLine({ ...newLine, product_id: '', quantity: 1 });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add line item');
    } finally {
      setActionLoading(false);
    }
  };

  // Handler: Create New WO for Remaining (Req 19.5)
  const handleCreateWOForRemaining = async (lineId: string) => {
    if (!order) return;
    const line = order.lines.find(l => l.id === lineId);
    if (!line) return;

    const remaining = line.quantity - line.allocated_qty;
    if (remaining <= 0) {
      setError('No remaining quantity to produce');
      return;
    }

    setActionLoading(true);
    try {
      // Fetch the active BOM for this product variant
      let bomId = line.product_id; // fallback — will be replaced below
      try {
        const bomsResp = await fetch(`/api/v1/products/${line.product_id}/boms?is_active=true`);
        if (bomsResp.ok) {
          const bomsData = await bomsResp.json();
          const activeBom = (bomsData.items ?? bomsData)?.[0];
          if (activeBom?.id) bomId = activeBom.id;
        }
      } catch {
        // If BOM fetch fails, fall through — backend will reject if BOM is invalid
      }

      await workOrderService.create({
        product_id: line.product_id,
        bom_id: bomId,
        planned_quantity: remaining,
        start_date: new Date().toISOString().split('T')[0],
        due_date: order.delivery_date,
        sales_order_id: order.id,
        notes: `Remaining quantity for SO ${order.order_number}, Line ${lineId}`,
      });
      
      setError(null);
      alert(`Work order created for remaining quantity: ${remaining}`);
      await loadOrder(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create work order');
    } finally {
      setActionLoading(false);
    }
  };

  // Handler: Short-Close Line (Req 19.6)
  const handleShortCloseLine = async () => {
    if (!order || !selectedLineId) return;
    
    setActionLoading(true);
    try {
      // Call endpoint to update line status to SHORT_CLOSED
      // This should also recalculate SO totals on backend
      await ordersApi.updateLine(order.id, selectedLineId, {
        line_status: 'SHORT_CLOSED',
      });
      
      setError(null);
      setShortCloseDialogOpen(false);
      setSelectedLineId(null);
      await loadOrder(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to short-close line');
    } finally {
      setActionLoading(false);
    }
  };


  if (loading) {
    return (
      <div className="p-8">
        <CardSkeleton />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="p-8">
        <div className="text-center">
          <p className="text-red-600 mb-4">Order not found</p>
          <Button onClick={() => navigate('/sales/orders')}>Back to Orders</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/sales/orders')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Order {order.order_number}</h1>
            <p className="text-gray-600">View and manage order details</p>
          </div>
        </div>
        <div className="flex gap-2">
          {order.status === OrderStatus.DRAFT && (
            <Button variant="outline" onClick={() => navigate(`/sales/orders/${order.id}/edit`)}>
              <Edit2 className="mr-2 h-4 w-4" />
              Edit
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Workflow Progress Timeline (Req 4.1–4.7) */}
      {id && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Order Progress</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <SalesWorkflowTimeline
              salesOrderId={id}
              currentStatus={order.status}
            />
          </CardContent>
        </Card>
      )}

      {/* Order Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge status={order.status} colorMap={SO_STATUS_COLOR_MAP} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Order Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{new Date(order.order_date).toLocaleDateString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Delivery Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">
              {new Date(order.delivery_date).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Grand Total</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold text-green-600">{formatCurrency(order.grand_total)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Order Details */}
      <Card>
        <CardHeader>
          <CardTitle>Order Information</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Client</label>
            <p className="text-gray-900">{order.client_name || order.client_id}</p>
            {order.client_code && <p className="text-xs text-gray-500 mt-1">{order.client_code}</p>}
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Payment Status</label>
            <p className="text-gray-900">{order.payment_status}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Created By</label>
            <p className="text-gray-900">{order.created_by || 'System'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Created At</label>
            <p className="text-gray-900">{new Date(order.created_at).toLocaleString()}</p>
          </div>
          {order.notes && (
            <div className="col-span-full">
              <label className="text-sm font-medium text-gray-700 block mb-1">Notes</label>
              <p className="text-gray-900 bg-gray-50 p-3 rounded">{order.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Line Items */}
      <Card>
        <CardHeader>
          <CardTitle>Order Line Items</CardTitle>
          <CardDescription>Products included in this order</CardDescription>
        </CardHeader>
        <CardContent>
          {order.lines.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No line items</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Product</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Quantity</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Unit Price</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Allocated Qty</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Dispatched Qty</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Remaining</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-700">Line Status</th>
                    <th className="px-4 py-2 text-right font-medium text-gray-700">Total</th>
                    <th className="px-4 py-2 text-center font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {order.lines.map((line) => {
                    const remaining = line.allocated_qty - line.shipped_qty;
                    const isPartial = String(line.line_status).toUpperCase() === 'PARTIAL';
                    
                    return (
                      <tr key={line.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <div className="font-medium">{line.product_name || line.product_id}</div>
                          <div className="text-xs text-gray-500">
                            {[line.product_code, line.product_type].filter(Boolean).join(' • ')}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {line.quantity} {line.uom_code || ''}
                        </td>
                        <td className="px-4 py-3">{formatCurrency(line.unit_price)}</td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">
                            {line.allocated_qty}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className="border-purple-200 bg-purple-50 text-purple-700">
                            {line.shipped_qty}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className="border-gray-200 bg-gray-50 text-gray-700">
                            {remaining}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge 
                            variant="outline" 
                            className={LINE_STATUS_COLORS[line.line_status] || LINE_STATUS_COLORS.PENDING}
                          >
                            {line.line_status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right font-semibold">{formatCurrency(line.total)}</td>
                        <td className="px-4 py-3 text-center">
                          {isPartial && (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem 
                                  onClick={() => handleCreateWOForRemaining(line.id)}
                                  disabled={actionLoading}
                                >
                                  Create New WO for Remaining
                                </DropdownMenuItem>
                                <DropdownMenuItem 
                                  onClick={() => {
                                    setSelectedLineId(line.id);
                                    setShortCloseDialogOpen(true);
                                  }}
                                  disabled={actionLoading}
                                  className="text-red-600"
                                >
                                  Short-Close Line
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          
          {order.status === OrderStatus.DRAFT && (
            <div className="mt-6 border-t pt-6">
              <h4 className="font-semibold mb-2 text-gray-800">Add Line Item</h4>

              {/* Guidance callout — explains the Product Variant → Material link requirement */}
              <div className="mb-4 rounded-md bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
                <p className="font-medium mb-1">How products work in sales orders</p>
                <p>
                  You select a <strong>Product Variant</strong> (e.g. "Widget — Size L"). For the order to be
                  confirmed and inventory reserved, each variant must have a{' '}
                  <strong>Finished Goods material linked</strong> to it. Variants with ⚠ are not linked yet —
                  go to <span className="font-mono">Products → [product] → Manage Variants → Edit</span> to
                  link the inventory material before using them in orders.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                <div className="col-span-2">
                  <label className="text-sm font-medium text-gray-700 block mb-1">Product Variant *</label>
                  <Select 
                    value={newLine.product_id}
                    onValueChange={(val) => {
                      const variant = variants.find(v => v.id === val);
                      setNewLine({ 
                        ...newLine, 
                        product_id: val, 
                        uom_id: variant?.base_unit_id || '' 
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a product variant" />
                    </SelectTrigger>
                    <SelectContent>
                      {variants.map(v => {
                        const hasNoMaterial = !v.stock_material_id && !(v as any).material_id;
                        return (
                          <SelectItem key={v.id} value={v.id}>
                            <span className="flex items-center gap-1.5">
                              {hasNoMaterial && (
                                <span className="text-amber-500 font-bold">⚠</span>
                              )}
                              {v.name} ({v.code})
                              {hasNoMaterial && (
                                <span className="text-xs text-amber-600 ml-1">— no material linked</span>
                              )}
                            </span>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  {/* Inline warning if the selected variant has no material */}
                  {newLine.product_id && (() => {
                    const selected = variants.find(v => v.id === newLine.product_id);
                    const hasNoMaterial = selected && !selected.stock_material_id && !(selected as any).material_id;
                    return hasNoMaterial ? (
                      <p className="mt-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                        ⚠ This variant has no inventory material linked. Order confirmation will fail.
                        Link a material in <strong>Products → Manage Variants</strong> first.
                      </p>
                    ) : null;
                  })()}
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Unit of Measure *</label>
                  <Input 
                    placeholder="Auto-filled UOM"
                    value={newLine.uom_id}
                    readOnly
                    className="bg-gray-100 text-gray-500 cursor-not-allowed"
                    title="UOM is automatically inherited from the product"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Quantity *</label>
                  <Input 
                    type="number"
                    min="1"
                    value={newLine.quantity}
                    onChange={(e) => setNewLine({ ...newLine, quantity: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <Button 
                    className="w-full bg-slate-800 hover:bg-slate-700" 
                    onClick={handleAddLine}
                    disabled={actionLoading}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add
                  </Button>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                * Note: Pricing is automatically resolved from the Client's assigned Price List or the Default Price List. 
                Auto-Work Order generation occurs on confirm if no physical stock is available.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Totals */}
      <Card>
        <CardHeader>
          <CardTitle>Order Totals</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between text-gray-600">
              <span>Subtotal:</span>
              <span>{formatCurrency(order.subtotal)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Discount:</span>
              <span className="text-red-600">-{formatCurrency(order.discount_amount)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Tax:</span>
              <span>{formatCurrency(order.tax_amount)}</span>
            </div>
            <div className="border-t pt-3 flex justify-between text-lg font-bold">
              <span>Grand Total:</span>
              <span className="text-green-600">{formatCurrency(order.grand_total)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Panel — status-driven action buttons, contextual info panels (Req 11.1–11.8, 3.8) */}
      <SalesOrderActionPanel
        order={order}
        actionLoading={actionLoading}
        confirmError={confirmError}
        onAction={handleStatusChange}
      />

      {/* Dispatch Panel — shown for READY_FOR_DISPATCH, SHIPPED statuses */}
      {(order.status === OrderStatus.READY_FOR_DISPATCH ||
        order.status === OrderStatus.SHIPPED ||
        order.status === OrderStatus.DELIVERED) && (
        <DispatchPanel order={order} onOrderUpdate={() => void loadOrder(true)} />
      )}

      {/* Invoice Display Section (Req 2.5, 2.6) */}
      {invoice && (order.status === OrderStatus.INVOICED || 
                   order.status === OrderStatus.PAYMENT_RECEIVED || 
                   order.status === OrderStatus.COMPLETED) && (
        <Card>
          <CardHeader>
            <CardTitle>Invoice Details</CardTitle>
            <CardDescription>Invoice and payment information</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Invoice Number</label>
                <a 
                  href={`/finance/invoices/${invoice.id}`}
                  className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                >
                  {invoice.invoice_number}
                </a>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Invoice Date</label>
                <p className="text-gray-900">{new Date(invoice.invoice_date).toLocaleDateString()}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Grand Total</label>
                <p className="text-gray-900 font-semibold text-green-600">
                  {formatCurrency(invoice.grand_total)}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Outstanding Balance</label>
                <p className="text-gray-900 font-semibold">
                  {formatCurrency(invoice.balance_due)}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Payment Status</label>
                <StatusBadge 
                  status={invoice.status} 
                  colorMap={{
                    DRAFT: 'gray',
                    SENT: 'blue',
                    PARTIAL: 'amber',
                    PAID: 'green',
                    OVERDUE: 'red',
                    CANCELLED: 'gray',
                    VOID: 'gray',
                  }}
                />
              </div>
            </div>
            {order.status === OrderStatus.INVOICED && invoice.balance_due > 0 && (
              <div className="mt-6 pt-6 border-t">
                <Button 
                  onClick={() => handleStatusChange('record_payment')}
                  className="bg-green-600 hover:bg-green-700"
                >
                  Record Payment
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Short-Close Confirmation Dialog (Req 19.6) */}
      <Dialog open={shortCloseDialogOpen} onOpenChange={setShortCloseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Short-Close Line</DialogTitle>
            <DialogDescription>
              This will mark the line as short-closed. Remaining quantity will not be fulfilled. Continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShortCloseDialogOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleShortCloseLine}
              disabled={actionLoading}
              className="bg-red-600 hover:bg-red-700"
            >
              {actionLoading ? 'Processing...' : 'Short-Close'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Audit History Section (Req 24.3, 24.4, 24.5, 24.6) */}
      <Card>
        <CardHeader>
          <CardTitle>Audit History</CardTitle>
          <CardDescription>Complete action log for this sales order</CardDescription>
        </CardHeader>
        <CardContent>
          <AuditHistoryTab entityType="sales_order" entityId={id || ''} />
        </CardContent>
      </Card>

      {/* SO Cancel Confirmation Dialog (Req 18.5, 18.7) */}
      {order && (
        <Dialog open={cancelDialogOpen} onOpenChange={(open) => {
          if (!actionLoading) {
            setCancelDialogOpen(open);
            if (!open) {
              setCancelReason('');
              setError(null);
            }
          }
        }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Cancel Sales Order</DialogTitle>
              <DialogDescription>
                Are you sure you want to cancel this order?
              </DialogDescription>
            </DialogHeader>
            {(() => {
              const reservedLines = order.lines.filter(l => (l.allocated_qty ?? 0) > 0);
              const totalReservedQty = reservedLines.reduce((sum, l) => sum + (l.allocated_qty ?? 0), 0);
              return reservedLines.length > 0 ? (
                <div className="space-y-3">
                  <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-800 space-y-1">
                    <p><span className="font-semibold">{reservedLines.length}</span> line item{reservedLines.length !== 1 ? 's have' : ' has'} reserved inventory.</p>
                    <p>Total reserved quantity: <span className="font-semibold">{totalReservedQty}</span> units</p>
                    <p className="flex items-center gap-1 text-amber-700 font-medium">
                      ⚠ This will release all inventory reservations.
                    </p>
                  </div>
                </div>
              ) : null;
            })()}
            {/* Inline error inside dialog (Req 18.7) */}
            {error && cancelDialogOpen && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
                <span>{error}</span>
              </div>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setCancelDialogOpen(false);
                  setCancelReason('');
                  setError(null);
                }}
                disabled={actionLoading}
              >
                Keep Order
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmCancellation}
                disabled={actionLoading}
              >
                {actionLoading ? 'Cancelling...' : 'Yes, Cancel Order'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
