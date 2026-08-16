/**
 * Delivery Dashboard Page
 * Dispatch queue (orders ready for dispatch) and active deliveries tracking.
 * Includes delivery cancellation (DRAFT/PACKING) and return info (SHIPPED) flows.
 * 
 * Requirements validated: 14.1–14.7, 33.1, 33.2, 33.5
 */

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Truck, PackageCheck, AlertCircle, Info } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { ToastAction } from "@/components/ui/toast"
import apiClient from "@/services/api-client"

interface DispatchQueueItem {
  id: string
  order_number: string
  customer_name: string | null   // backend field name
  client_name?: string | null    // alias for display
  grand_total: number
  total_quantity?: number
  ready_at: string | null
  due_date?: string | null
}

interface DeliveryItem {
  id: string
  delivery_number: string
  sales_order_number: string
  status: 'DRAFT' | 'PACKING' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED'
  carrier?: string
  tracking_number?: string
  total_quantity?: number
}

const STATUS_COLORS: Record<DeliveryItem['status'], string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  PACKING: "bg-blue-100 text-blue-700",
  SHIPPED: "bg-green-100 text-green-700",
  DELIVERED: "bg-emerald-100 text-emerald-700",
  CANCELLED: "bg-red-100 text-red-700",
}

/** Statuses from which a delivery can be cancelled (Req 33.1) */
const CANCELLABLE_DELIVERY_STATUSES: Array<DeliveryItem['status']> = ['DRAFT', 'PACKING']

export default function DeliveryDashboardPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  // Cancel dialog state
  const [cancelTarget, setCancelTarget] = useState<DeliveryItem | null>(null)
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)

  // Return info dialog state (for SHIPPED — no API call, informational only) (Req 33.2)
  const [returnInfoOpen, setReturnInfoOpen] = useState(false)

  // Fetch dispatch queue (orders ready for dispatch)
  const { data: dispatchQueue, isLoading: dispatchLoading } = useQuery<DispatchQueueItem[]>({
    queryKey: ["delivery-dispatch-queue"],
    queryFn: async () => {
      const response = await apiClient.get("/delivery/dispatch-queue")
      return response.data
    },
  })

  // Fetch active deliveries
  const { data: activeDeliveries, isLoading: deliveriesLoading } = useQuery<DeliveryItem[]>({
    queryKey: ["active-deliveries"],
    queryFn: async () => {
      const response = await apiClient.get("/deliveries", {
        params: { status: "DRAFT,PACKING,SHIPPED" }
      })
      return response.data
    },
  })

  // Ship delivery mutation
  const shipMutation = useMutation({
    mutationFn: async (deliveryId: string) => {
      await apiClient.post(`/deliveries/${deliveryId}/ship`)
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Delivery marked as shipped",
      })
      queryClient.invalidateQueries({ queryKey: ["active-deliveries"] })
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to mark delivery as shipped",
        variant: "destructive",
      })
    },
  })

  // Complete delivery mutation
  const completeMutation = useMutation({
    mutationFn: async (deliveryId: string) => {
      await apiClient.post(`/deliveries/${deliveryId}/deliver`)
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Delivery marked as delivered",
        action: <ToastAction altText="Go to Invoices" onClick={() => navigate('/finance/invoices')}>Generate Invoice</ToastAction>
      })
      queryClient.invalidateQueries({ queryKey: ["active-deliveries"] })
      queryClient.invalidateQueries({ queryKey: ["delivery-dispatch-queue"] })
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to mark delivery as delivered",
        variant: "destructive",
      })
    },
  })

  // Cancel delivery mutation (Req 33.1, 33.2, 33.5)
  const cancelMutation = useMutation({
    mutationFn: async (deliveryId: string) => {
      await apiClient.post(`/deliveries/${deliveryId}/cancel`)
    },
    onSuccess: () => {
      toast({
        title: "Delivery Cancelled",
        description: "Delivery has been cancelled and inventory restored.",
      })
      setCancelDialogOpen(false)
      setCancelTarget(null)
      setCancelError(null)
      queryClient.invalidateQueries({ queryKey: ["active-deliveries"] })
      queryClient.invalidateQueries({ queryKey: ["delivery-dispatch-queue"] })
    },
    onError: (error: any) => {
      // Show inline error inside dialog, keep dialog closable (Req 33.5)
      setCancelError(error.message || "Failed to cancel delivery. Please try again.")
    },
  })

  const openCancelDialog = (delivery: DeliveryItem) => {
    setCancelTarget(delivery)
    setCancelError(null)
    setCancelDialogOpen(true)
  }

  const closeCancelDialog = () => {
    if (!cancelMutation.isPending) {
      setCancelDialogOpen(false)
      setCancelTarget(null)
      setCancelError(null)
    }
  }

  if (dispatchLoading || deliveriesLoading) {
    return <div className="p-8">Loading Delivery Dashboard...</div>
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Delivery Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Dispatch queue and active deliveries tracking
          </p>
        </div>
      </div>

      {/* Dispatch Queue Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PackageCheck className="h-5 w-5 text-blue-500" />
            Dispatch Queue (Ready for Dispatch)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {dispatchQueue && dispatchQueue.length > 0 ? (
            <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order Number</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead className="text-right">Grand Total</TableHead>
                  <TableHead>Ready Since</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dispatchQueue
                  .sort((a, b) => {
                    const ta = a.ready_at ? new Date(a.ready_at).getTime() : 0
                    const tb = b.ready_at ? new Date(b.ready_at).getTime() : 0
                    return ta - tb
                  })
                  .map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-mono font-medium">{item.order_number}</TableCell>
                      <TableCell>{item.customer_name ?? item.client_name ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {item.grand_total !== undefined
                          ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(item.grand_total)
                          : "—"}
                      </TableCell>
                      <TableCell>
                        {item.ready_at ? new Date(item.ready_at).toLocaleDateString() : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          onClick={() => navigate(`/sales/orders/${item.id}/delivery/new`)}
                        >
                          Create Delivery
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
            </div>
          ) : (
            <p className="text-center py-8 text-muted-foreground">
              No orders are ready for dispatch
            </p>
          )}
        </CardContent>
      </Card>

      {/* Active Deliveries Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Truck className="h-5 w-5 text-green-500" />
            Active Deliveries
          </CardTitle>
        </CardHeader>
        <CardContent>
          {activeDeliveries && activeDeliveries.length > 0 ? (
            <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Delivery Number</TableHead>
                  <TableHead>Order Number</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Carrier</TableHead>
                  <TableHead>Tracking</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeDeliveries.map((delivery) => (
                  <TableRow key={delivery.id}>
                    <TableCell className="font-mono font-medium">{delivery.delivery_number}</TableCell>
                    <TableCell className="font-mono">{delivery.sales_order_number}</TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[delivery.status]}>
                        {delivery.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{delivery.carrier || '—'}</TableCell>
                    <TableCell className="font-mono text-sm">{delivery.tracking_number || '—'}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* Ship button for DRAFT/PACKING */}
                        {(delivery.status === 'DRAFT' || delivery.status === 'PACKING') && (
                          <Button
                            size="sm"
                            onClick={() => shipMutation.mutate(delivery.id)}
                            disabled={shipMutation.isPending || cancelMutation.isPending}
                          >
                            Ship
                          </Button>
                        )}

                        {/* Complete button for SHIPPED */}
                        {delivery.status === 'SHIPPED' && (
                          <Button
                            size="sm"
                            onClick={() => completeMutation.mutate(delivery.id)}
                            disabled={completeMutation.isPending}
                          >
                            Complete
                          </Button>
                        )}

                        {/* Cancel button for DRAFT/PACKING (Req 33.1) */}
                        {CANCELLABLE_DELIVERY_STATUSES.includes(delivery.status) && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600 border-red-200 hover:bg-red-50"
                            onClick={() => openCancelDialog(delivery)}
                            disabled={cancelMutation.isPending}
                          >
                            Cancel
                          </Button>
                        )}

                        {/* Create Return button for SHIPPED (Req 33.2) — informational only */}
                        {delivery.status === 'SHIPPED' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setReturnInfoOpen(true)}
                          >
                            Create Return
                          </Button>
                        )}

                        {delivery.status === 'DELIVERED' && (
                          <span className="text-sm text-muted-foreground">Completed</span>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
          ) : (
            <p className="text-center py-8 text-muted-foreground">
              No active deliveries
            </p>
          )}
        </CardContent>
      </Card>

      {/* Delivery Cancellation Confirmation Dialog (Req 33.1, 33.2, 33.5) */}
      <Dialog open={cancelDialogOpen} onOpenChange={closeCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Delivery</DialogTitle>
            <DialogDescription>
              {cancelTarget && (
                <>
                  Cancelling this delivery will restore{" "}
                  <span className="font-semibold">
                    {cancelTarget.total_quantity ?? 'the dispatched'}
                  </span>{" "}
                  units to inventory. The sales order will return to Ready for Dispatch status.
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          {/* Inline error inside dialog — keep dialog closable (Req 33.5) */}
          {cancelError && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{cancelError}</span>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={closeCancelDialog}
              disabled={cancelMutation.isPending}
            >
              Keep Delivery
            </Button>
            <Button
              variant="destructive"
              onClick={() => cancelTarget && cancelMutation.mutate(cancelTarget.id)}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? 'Cancelling...' : 'Yes, Cancel Delivery'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Return Info Dialog for SHIPPED deliveries (Req 33.2) — no API call, informational */}
      <Dialog open={returnInfoOpen} onOpenChange={setReturnInfoOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-500" />
              Create Goods Return
            </DialogTitle>
            <DialogDescription>
              For shipped deliveries, please process a goods return.
            </DialogDescription>
          </DialogHeader>
          <div className="bg-blue-50 border border-blue-200 rounded p-4 text-sm text-blue-800">
            <p>
              For shipped deliveries, cancellation is not permitted. To process a return, contact
              your warehouse team to initiate a goods return through the returns management process.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReturnInfoOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
