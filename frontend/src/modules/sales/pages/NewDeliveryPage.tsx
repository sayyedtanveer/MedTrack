/**
 * NewDeliveryPage
 *
 * Reached from:
 * - SO detail page action "Create Delivery Note" → /sales/orders/:id/delivery/new
 * - Dispatch Queue "Create Delivery Note" button  → /deliveries/new?so_id=:soId
 *
 * Loads the SO, shows per-line quantity inputs pre-filled with max dispatchable qty,
 * then calls POST /deliveries. On success navigates to the delivery dashboard.
 */

import { useState, useEffect } from "react"
import { useParams, useSearchParams, useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/services/api-client"
import { deliveryService as _deliveryService } from "@/services/delivery.service"
import { ordersApi } from "@/services/sales.service"
import type { SalesOrder, SalesOrderLine } from "@/types/sales.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ArrowLeft, Loader2, Truck } from "lucide-react"
import { toast } from "sonner"
import { formatCurrency } from "@/utils/currency"

// Max dispatchable qty for a line = allocated - already shipped
function maxDispatchable(line: SalesOrderLine): number {
  return Math.max(0, Number(line.allocated_qty ?? 0) - Number(line.shipped_qty ?? 0))
}

export default function NewDeliveryPage() {
  const { id: soIdFromParams } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const soIdFromQuery = searchParams.get("so_id")
  const soId = soIdFromParams ?? soIdFromQuery ?? ""

  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [order, setOrder] = useState<SalesOrder | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Per-line qty state: lineId → quantity
  const [lineQtys, setLineQtys] = useState<Record<string, number>>({})
  const [qtyErrors, setQtyErrors] = useState<Record<string, string>>({})

  // Carrier / tracking (optional)
  const [carrier, setCarrier] = useState("")
  const [tracking, setTracking] = useState("")
  const [notes, setNotes] = useState("")

  useEffect(() => {
    if (!soId) {
      setError("No sales order ID provided.")
      setLoading(false)
      return
    }
    ordersApi
      .get(soId)
      .then((so) => {
        setOrder(so)
        // Pre-fill with max dispatchable per line
        const init: Record<string, number> = {}
        so.lines.forEach((l) => {
          init[l.id] = maxDispatchable(l)
        })
        setLineQtys(init)
      })
      .catch(() => setError("Failed to load sales order."))
      .finally(() => setLoading(false))
  }, [soId])

  const handleQtyChange = (lineId: string, raw: string, line: SalesOrderLine) => {
    const max = maxDispatchable(line)
    const val = parseInt(raw, 10)
    const errors = { ...qtyErrors }
    if (isNaN(val) || val < 0) {
      errors[lineId] = "Enter a valid quantity"
    } else if (val > max) {
      errors[lineId] = `Max: ${max}`
    } else {
      delete errors[lineId]
    }
    setQtyErrors(errors)
    setLineQtys((prev) => ({ ...prev, [lineId]: isNaN(val) ? 0 : val }))
  }

  const handleSubmit = async () => {
    if (!order) return
    const lines = order.lines
      .filter((l) => (lineQtys[l.id] ?? 0) > 0)
      .map((l) => ({
        sales_order_line_id: l.id,
        quantity: lineQtys[l.id],
      }))

    if (lines.length === 0) {
      toast.error("Enter at least one line quantity > 0")
      return
    }

    if (Object.keys(qtyErrors).length > 0) {
      toast.error("Fix quantity errors before saving")
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        sales_order_id: order.id,
        lines,
        carrier: carrier || null,
        tracking_number: tracking || null,
        notes: notes || null,
      }
      const { data } = await apiClient.post("/deliveries", payload)
      toast.success(`Delivery note ${data.delivery_number} created`)
      queryClient.invalidateQueries({ queryKey: ["active-deliveries"] })
      queryClient.invalidateQueries({ queryKey: ["delivery-dispatch-queue"] })
      queryClient.invalidateQueries({ queryKey: ["deliveries", order.id] })
      navigate("/delivery/dashboard")
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to create delivery note")
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center gap-2 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading order...
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="p-8">
        <p className="text-red-600 mb-4">{error ?? "Order not found"}</p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Go Back
        </Button>
      </div>
    )
  }

  const dispatchableLines = order.lines.filter((l) => maxDispatchable(l) > 0)

  return (
    <div className="space-y-6 p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Create Delivery Note</h1>
          <p className="text-sm text-muted-foreground">
            Order {order.order_number} — {order.client_name}
          </p>
        </div>
      </div>

      {/* Line quantities */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dispatch Quantities</CardTitle>
          <CardDescription>Enter the quantity to dispatch per line. Max = allocated − already shipped.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {dispatchableLines.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              All allocated quantities have already been dispatched for this order.
            </p>
          ) : (
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-muted/40 border-b text-muted-foreground">
                  <th className="px-3 py-2 text-left font-medium">Product</th>
                  <th className="px-3 py-2 text-right font-medium">Ordered</th>
                  <th className="px-3 py-2 text-right font-medium">Allocated</th>
                  <th className="px-3 py-2 text-right font-medium">Shipped</th>
                  <th className="px-3 py-2 text-right font-medium">Max</th>
                  <th className="px-3 py-2 text-right font-medium w-28">Dispatch Qty</th>
                </tr>
              </thead>
              <tbody>
                {dispatchableLines.map((line) => {
                  const max = maxDispatchable(line)
                  const err = qtyErrors[line.id]
                  return (
                    <tr key={line.id} className="border-b hover:bg-muted/20">
                      <td className="px-3 py-2">
                        <div className="font-medium">{line.product_name || line.product_id}</div>
                        {line.product_code && (
                          <div className="text-xs text-muted-foreground">{line.product_code}</div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">{line.quantity}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{line.allocated_qty}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{line.shipped_qty}</td>
                      <td className="px-3 py-2 text-right tabular-nums font-medium text-teal-700">{max}</td>
                      <td className="px-3 py-2 text-right">
                        <div>
                          <Input
                            type="number"
                            min={0}
                            max={max}
                            value={lineQtys[line.id] ?? max}
                            onChange={(e) => handleQtyChange(line.id, e.target.value, line)}
                            className={`w-24 text-right ${err ? "border-red-400" : ""}`}
                          />
                          {err && <p className="text-xs text-red-500 mt-0.5">{err}</p>}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Shipping details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Shipping Details (Optional)</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label className="text-xs">Carrier</Label>
            <Input
              placeholder="e.g. FedEx, UPS"
              value={carrier}
              onChange={(e) => setCarrier(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Tracking Number</Label>
            <Input
              placeholder="e.g. 1234567890"
              value={tracking}
              onChange={(e) => setTracking(e.target.value)}
            />
          </div>
          <div className="col-span-2 space-y-1.5">
            <Label className="text-xs">Notes</Label>
            <Input
              placeholder="Any delivery instructions..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <Card className="bg-muted/20">
        <CardContent className="pt-4 flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Order total: <span className="font-semibold text-foreground">{formatCurrency(order.grand_total)}</span>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => navigate(-1)} disabled={submitting}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting || dispatchableLines.length === 0}
              className="bg-teal-600 hover:bg-teal-700"
            >
              {submitting ? (
                <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
              ) : (
                <Truck className="w-3.5 h-3.5 mr-1" />
              )}
              Create Delivery Note
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
