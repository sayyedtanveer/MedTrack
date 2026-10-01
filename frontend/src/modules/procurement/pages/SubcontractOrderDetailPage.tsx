import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import {
  supplyChainApi,
  type SubcontractOrderDetail,
  type SubcontractOrderLine,
} from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import { SubcontractMaterialSelector } from "../components/SubcontractMaterialSelector"
import { IssueMaterialDrawer } from "../components/IssueMaterialDrawer"
import type { Location, Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { usePermissions } from "@/hooks/usePermissions"
import {
  CheckCircle, XCircle, Package, RotateCcw, ArrowLeftRight, Boxes, Loader2, Info,
} from "lucide-react"

// ── helpers ────────────────────────────────────────────────────────────────────

function locKind(l: Location & { location_type?: string }) {
  return l.location_type ?? (l as { type?: string }).type ?? ""
}

// Helper component for output batch display
function OutputBatchDisplay({ outputBatch }: { outputBatch: Record<string, unknown> }) {
  const batchNumber = outputBatch.batch_number ? String(outputBatch.batch_number) : 'N/A';
  const materialName = outputBatch.material_name ? String(outputBatch.material_name) : 'N/A';
  const quantity = typeof outputBatch.quantity === 'number' ? outputBatch.quantity : (outputBatch.quantity ? Number(outputBatch.quantity) : 0);
  const status = outputBatch.status ? String(outputBatch.status) : 'Unknown';
  
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
        Processed output batch
      </p>
      <div className="text-xs border rounded px-2 py-1.5 bg-white flex items-center gap-3">
        <span className="font-mono font-medium text-emerald-700">{batchNumber}</span>
        <span className="text-muted-foreground">{materialName}</span>
        <span>Qty: {quantity}</span>
        <Badge variant="outline" className="text-xs">{status}</Badge>
      </div>
    </div>
  );
}

function statusBadge(s: string) {
  const map: Record<string, string> = {
    draft:               "bg-slate-100 text-slate-700",
    approved:            "bg-blue-100 text-blue-700",
    materials_issued:    "bg-amber-100 text-amber-700",
    partially_received:  "bg-orange-100 text-orange-700",
    completed:           "bg-emerald-100 text-emerald-700",
    cancelled:           "bg-red-100 text-red-700",
  }
  return map[s] ?? "bg-slate-100 text-slate-700"
}

// ── Material Info Component ────────────────────────────────────────────────────

function MaterialInfo({ materialId }: { materialId: string }) {
  const [material, setMaterial] = useState<Material | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    materialService.getMaterial(materialId)
      .then(setMaterial)
      .catch(() => setMaterial(null))
      .finally(() => setLoading(false))
  }, [materialId])

  if (loading) {
    return <span className="text-xs text-muted-foreground">Loading...</span>
  }

  if (!material) {
    return <span className="font-mono text-xs text-muted-foreground">{materialId.slice(0, 8)}…</span>
  }

  return (
    <div className="text-sm">
      <div className="font-mono font-medium">{material.code}</div>
      <div className="text-xs text-muted-foreground">{material.name}</div>
    </div>
  )
}

// ── component ────────────────────────────────────────────────────────────────

export default function SubcontractOrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const { toast } = useToast()
  const { canProcurementWrite } = usePermissions()
  const allowOps = canProcurementWrite()

  const [order, setOrder] = useState<SubcontractOrderDetail | null>(null)
  const [locations, setLocations] = useState<(Location & { location_type?: string })[]>([])
  const [traceability, setTraceability] = useState<Record<string, unknown> | null>(null)
  const [showTrace, setShowTrace] = useState(false)
  const [busy, setBusy] = useState(false)

  // Stock availability per material (material_id -> available quantity)
  const [stockAvailability, setStockAvailability] = useState<Record<string, number>>({})
  const [loadingStock, setLoadingStock] = useState(false)

  // Issue drawer state
  const [issueDrawerOpen, setIssueDrawerOpen] = useState(false)
  const [selectedLine, setSelectedLine] = useState<SubcontractOrderLine | null>(null)

  // Additional material issue form (for non-BOM materials)
  const [showAdditionalIssue, setShowAdditionalIssue] = useState(false)

  // Issue form — uses SubcontractMaterialSelector (raw OR semi_finished components)
  const [issueMat, setIssueMat] = useState("")
  const [issuePendingQty, setIssuePendingQty] = useState<number | null>(null)
  const [issueQty, setIssueQty] = useState("1")
  const [issueFrom, setIssueFrom] = useState("")
  const [issueBatchId, setIssueBatchId] = useState("")

  // Receive form — uses SubcontractMaterialSelector (defaults to order's output material)
  const [recvMat, setRecvMat] = useState("")
  const [recvQty, setRecvQty] = useState("1")
  const [recvWh, setRecvWh] = useState("")
  const [recvBatchNum, setRecvBatchNum] = useState("")

  // Return form
  const [retMat, setRetMat] = useState("")
  const [retQty, setRetQty] = useState("1")
  const [retLoc, setRetLoc] = useState("")

  const load = async () => {
    if (!orderId) return
    const { data } = await supplyChainApi.getSubcontractOrder(orderId)
    setOrder(data)
    setRecvQty(String(Math.max(0, (data.quantity ?? 0) - (data.received_quantity ?? 0))))
    setRecvMat(data.product_id ?? "")
    setRecvBatchNum(`SCO-${data.order_number}`)
    
    // Load stock availability for all component materials
    if (data.lines && data.lines.length > 0) {
      loadStockAvailability(data.lines.map(l => l.material_id))
    }
  }

  const loadStockAvailability = async (materialIds: string[]) => {
    if (materialIds.length === 0) return
    
    setLoadingStock(true)
    try {
      // Fetch stock for each material
      const stockPromises = materialIds.map(async (materialId) => {
        try {
          const stockInfo = await materialService.getMaterialStock(materialId)
          // Use available_stock from the API response (current_stock - reserved_stock)
          return {
            materialId,
            available: Number(stockInfo.available_stock || 0)
          }
        } catch {
          return { materialId, available: 0 }
        }
      })
      
      const results = await Promise.all(stockPromises)
      const stockMap: Record<string, number> = {}
      results.forEach(({ materialId, available }) => {
        stockMap[materialId] = available
      })
      setStockAvailability(stockMap)
    } catch (error) {
      console.error('Failed to load stock availability:', error)
    } finally {
      setLoadingStock(false)
    }
  }

  useEffect(() => {
    const init = async () => {
      const [, locs] = await Promise.all([load(), materialService.getLocations()])
      const locsTyped = locs as (Location & { location_type?: string })[]
      setLocations(locsTyped)
      const wh = locsTyped.find((l) => locKind(l) === "warehouse")
      if (wh) { setRecvWh(wh.id); setIssueFrom(wh.id); setRetLoc(wh.id) }
    }
    init().catch(() => toast({ title: "Failed to load", variant: "destructive" }))
  }, [orderId, toast])

  // When user selects a component for issue, pre-fill pending qty from order lines
  const handleIssueMaterialChange = (id: string) => {
    setIssueMat(id)
    if (order) {
      const line = order.lines.find((l) => l.material_id === id)
      if (line) {
        const pending = Math.max(0, line.required_quantity - line.issued_quantity)
        setIssuePendingQty(pending)
        setIssueQty(String(pending > 0 ? pending : 1))
      } else {
        setIssuePendingQty(null)
      }
    }
  }

  // ── actions ────────────────────────────────────────────────────────────────

  const act = async (fn: () => Promise<void>, successMsg: string) => {
    if (!allowOps || busy) return
    setBusy(true)
    try {
      await fn()
      toast({ title: successMsg })
      await load()
    } catch (e: unknown) {
      // Extract error message from various possible formats
      const errorObj = e as { 
        response?: { 
          data?: { 
            detail?: string
            error?: { message?: string }
            message?: string
          } 
        }
        message?: string
      }
      
      const detail = 
        errorObj?.response?.data?.error?.message ||
        errorObj?.response?.data?.detail ||
        errorObj?.response?.data?.message ||
        errorObj?.message ||
        "Operation failed"
      
      // Parse insufficient stock errors to be more helpful
      let displayMessage = detail
      if (detail.includes("Insufficient available stock")) {
        // Extract shortage amount if available
        const match = detail.match(/(\d+(?:\.\d+)?)\s*short/)
        if (match) {
          const shortage = match[1]
          displayMessage = `Insufficient stock. Short by ${shortage} units. Please check stock availability in the selected warehouse or choose a different warehouse.`
        } else {
          displayMessage = "Insufficient stock in the selected warehouse. Please check stock availability or choose a different warehouse."
        }
      }
      
      toast({ title: displayMessage, variant: "destructive" })
    } finally {
      setBusy(false)
    }
  }

  const approve = () =>
    act(() => supplyChainApi.approveSubcontractOrder(orderId!).then(() => undefined),
      "Order approved — component list loaded from BOM")

  const cancel = () =>
    act(() => supplyChainApi.cancelSubcontractOrder(orderId!).then(() => undefined), "Order cancelled")

  const handleIssueFromDrawer = async (data: {
    material_id: string
    quantity: number
    from_location_id: string
    batch_id: string | null
  }) => {
    await act(
      () =>
        supplyChainApi
          .issueSubcontract(orderId!, {
            material_id: data.material_id,
            quantity: data.quantity,
            from_location_id: data.from_location_id,
            batch_id: data.batch_id,
          })
          .then(() => undefined),
      "Material issued to vendor"
    )
  }

  const issue = () =>
    act(() =>
      supplyChainApi.issueSubcontract(orderId!, {
        material_id: issueMat,
        quantity: Number(issueQty),
        from_location_id: issueFrom,
        batch_id: issueBatchId.trim() || null,
      }).then(() => undefined),
      "Material issued to vendor"
    )

  const receive = () =>
    act(() =>
      supplyChainApi.receiveSubcontract(orderId!, {
        material_id: recvMat,
        quantity: Number(recvQty),
        warehouse_location_id: recvWh,
        output_batch_number: recvBatchNum.trim() || null,
      }).then(() => undefined),
      "Processed material received into stock"
    )

  const returnMat = () =>
    act(() =>
      supplyChainApi.returnSubcontractMaterial(orderId!, {
        material_id: retMat,
        quantity: Number(retQty),
        to_location_id: retLoc,
      }).then(() => undefined),
      "Material returned to warehouse"
    )

  const loadTrace = async () => {
    try {
      const { data } = await supplyChainApi.getSubcontractTraceability(orderId!)
      setTraceability(data as Record<string, unknown>)
      setShowTrace(true)
    } catch {
      toast({ title: "Failed to load traceability", variant: "destructive" })
    }
  }

  // ── render ─────────────────────────────────────────────────────────────────

  if (!order) return (
    <div className="flex items-center gap-2 p-6 text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />Loading…
    </div>
  )

  const warehouses = locations.filter((l) => locKind(l) === "warehouse" && l.is_active)
  const canApprove = order.status === "draft"
  const canIssue   = order.status === "approved" || order.status === "materials_issued"
  const canReceive = order.status === "materials_issued" || order.status === "partially_received"
  const canReturn  = ["materials_issued", "partially_received", "completed"].includes(order.status)
  const canCancel  = order.status === "draft" || order.status === "approved"

  return (
    <div className="space-y-8 max-w-4xl pb-12">

      {/* ── Header ───────────────────────────────────────────────────── */}
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link to="/procurement/subcontract">← Subcontract orders</Link>
        </Button>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-semibold font-mono">{order.order_number}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Output qty: {order.quantity} · Received: {order.received_quantity ?? 0}
              {order.due_date && ` · Due: ${order.due_date}`}
            </p>
            {order.notes && <p className="text-xs text-muted-foreground mt-1">{order.notes}</p>}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold whitespace-nowrap ${statusBadge(order.status)}`}>
              {order.status.replace(/_/g, " ")}
            </span>
            {canApprove && (
              <Button size="sm" disabled={busy || !allowOps} onClick={approve}>
                <CheckCircle className="mr-1.5 h-4 w-4" />Approve
              </Button>
            )}
            {canCancel && (
              <Button size="sm" variant="outline" disabled={busy || !allowOps} onClick={cancel}
                className="text-red-600 border-red-300 hover:bg-red-50">
                <XCircle className="mr-1.5 h-4 w-4" />Cancel
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={loadTrace}>
              <Boxes className="mr-1.5 h-4 w-4" />Traceability
            </Button>
          </div>
        </div>
      </div>

      {/* ── Draft status info - What will happen on approval ──────────── */}
      {canApprove && order.bom_id && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 p-4 space-y-2">
          <div className="flex items-start gap-2">
            <CheckCircle className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
            <div className="flex-1">
              <h3 className="font-medium text-blue-900">Ready for Approval</h3>
              <p className="text-sm text-blue-800 mt-1">
                When you approve this order, the system will:
              </p>
              <ul className="text-sm text-blue-800 mt-2 space-y-1 list-disc list-inside">
                <li>Snapshot the BOM components as order lines below</li>
                <li>Calculate required quantities based on order quantity ({order.quantity} units)</li>
                <li>Apply scrap percentages from the BOM</li>
                <li>Enable material issuing to the vendor</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {canApprove && !order.bom_id && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-4 space-y-2">
          <div className="flex items-start gap-2">
            <Package className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
            <div className="flex-1">
              <h3 className="font-medium text-amber-900">No BOM Linked</h3>
              <p className="text-sm text-amber-800 mt-1">
                This order doesn't have a BOM attached. After approval, you'll need to manually select and issue component materials to the vendor.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Component lines ──────────────────────────────────────────── */}
      {order.lines.length > 0 && (
        <section>
          <div className="flex items-start justify-between gap-4 mb-3">
            <div>
              <h2 className="font-medium flex items-center gap-2">
                <Package className="h-4 w-4" />Required components
                <span className="text-xs text-muted-foreground font-normal">(from BOM snapshot)</span>
              </h2>
              <p className="text-xs text-muted-foreground mt-1 flex items-start gap-1">
                <Info className="h-3 w-3 mt-0.5 shrink-0" />
                <span>
                  These materials come from the approved BOM snapshot. 
                  Use "Issue Material" to move required stock from your warehouse to the subcontractor.
                </span>
              </p>
            </div>
          </div>
          
          {/* Desktop table view */}
          <div className="hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Material</TableHead>
                  <TableHead className="text-right">Required</TableHead>
                  <TableHead className="text-right">Issued</TableHead>
                  <TableHead className="text-right">Returned</TableHead>
                  <TableHead className="text-right">Remaining</TableHead>
                  <TableHead className="text-right">Available Stock</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {order.lines.map((ln: SubcontractOrderLine) => {
                  const remaining = Math.max(
                    0,
                    ln.required_quantity - ln.issued_quantity + (ln.returned_quantity || 0)
                  )
                  const availableStock = stockAvailability[ln.material_id] ?? 0
                  const hasEnoughStock = availableStock >= remaining
                  
                  return (
                    <TableRow key={ln.id}>
                      <TableCell>
                        <MaterialInfo materialId={ln.material_id} />
                      </TableCell>
                      <TableCell className="text-right">{ln.required_quantity}</TableCell>
                      <TableCell className="text-right">{ln.issued_quantity}</TableCell>
                      <TableCell className="text-right">{ln.returned_quantity}</TableCell>
                      <TableCell className="text-right font-medium">
                        {remaining > 0 ? (
                          <span className="text-blue-600">{remaining}</span>
                        ) : (
                          <span className="text-muted-foreground">{remaining}</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {loadingStock ? (
                          <span className="text-xs text-muted-foreground">Loading...</span>
                        ) : hasEnoughStock ? (
                          <span className="text-emerald-600">{availableStock}</span>
                        ) : availableStock > 0 ? (
                          <span className="text-amber-600" title="Insufficient stock">
                            {availableStock} ⚠️
                          </span>
                        ) : (
                          <span className="text-red-600" title="No stock available">
                            0 ❌
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={ln.status === "issued" ? "default" : "secondary"}>
                          {ln.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {remaining > 0 && canIssue ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedLine(ln)
                              setIssueDrawerOpen(true)
                            }}
                            disabled={busy || !allowOps}
                          >
                            {ln.issued_quantity > 0 ? "Issue Remaining" : "Issue Material"}
                          </Button>
                        ) : remaining === 0 ? (
                          <span className="text-xs text-emerald-600 flex items-center justify-end gap-1">
                            <CheckCircle className="h-3 w-3" />
                            Fully Issued
                          </span>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>

          {/* Mobile card view */}
          <div className="md:hidden space-y-2">
            {order.lines.map((ln: SubcontractOrderLine) => {
              const remaining = Math.max(
                0,
                ln.required_quantity - ln.issued_quantity + (ln.returned_quantity || 0)
              )
              const availableStock = stockAvailability[ln.material_id] ?? 0
              const hasEnoughStock = availableStock >= remaining
              
              return (
                <div key={ln.id} className="border rounded-lg p-3 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <MaterialInfo materialId={ln.material_id} />
                    <Badge variant={ln.status === "issued" ? "default" : "secondary"} className="shrink-0">
                      {ln.status}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    <div>
                      <div className="text-muted-foreground">Required</div>
                      <div className="font-medium">{ln.required_quantity}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Issued</div>
                      <div className="font-medium">{ln.issued_quantity}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Returned</div>
                      <div className="font-medium">{ln.returned_quantity}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Remaining</div>
                      <div className="font-medium text-blue-600">{remaining}</div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs pt-2 border-t">
                    <span className="text-muted-foreground">Available Stock:</span>
                    {loadingStock ? (
                      <span className="text-muted-foreground">Loading...</span>
                    ) : hasEnoughStock ? (
                      <span className="font-semibold text-emerald-600">{availableStock} ✓</span>
                    ) : availableStock > 0 ? (
                      <span className="font-semibold text-amber-600">{availableStock} ⚠️</span>
                    ) : (
                      <span className="font-semibold text-red-600">0 ❌</span>
                    )}
                  </div>
                  {remaining > 0 && canIssue ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full"
                      onClick={() => {
                        setSelectedLine(ln)
                        setIssueDrawerOpen(true)
                      }}
                      disabled={busy || !allowOps}
                    >
                      {ln.issued_quantity > 0 ? "Issue Remaining" : "Issue Material"}
                    </Button>
                  ) : remaining === 0 ? (
                    <div className="text-xs text-emerald-600 flex items-center justify-center gap-1 py-2">
                      <CheckCircle className="h-3 w-3" />
                      Fully Issued
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* ── Issue Drawer ─────────────────────────────────────────────── */}
      <IssueMaterialDrawer
        open={issueDrawerOpen}
        onOpenChange={setIssueDrawerOpen}
        line={selectedLine}
        orderNumber={order.order_number}
        supplierName={order.supplier_name}
        warehouses={warehouses}
        onIssue={handleIssueFromDrawer}
        busy={busy}
      />

      {/* ── Additional Material Issue (Non-BOM) ──────────────────────── */}
      {canIssue && (
        <section className="border-t pt-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="font-medium text-base flex items-center gap-2">
                Additional Material
              </h2>
              <p className="text-xs text-muted-foreground mt-1 flex items-start gap-1">
                <Info className="h-3 w-3 mt-0.5 shrink-0" />
                <span>
                  Use this only when the vendor needs an additional material that is NOT included in the approved BOM.
                </span>
              </p>
            </div>
            {!showAdditionalIssue && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowAdditionalIssue(true)}
                disabled={busy || !allowOps}
              >
                + Issue Additional Material
              </Button>
            )}
          </div>

          {showAdditionalIssue && (
            <div className="border rounded-lg p-3 sm:p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium flex items-center gap-2 text-sm">
                  <ArrowLeftRight className="h-4 w-4" />Issue non-BOM material
                </h3>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowAdditionalIssue(false)}
                  disabled={busy}
                >
                  Cancel
                </Button>
              </div>
              {!allowOps && (
                <p className="text-xs bg-amber-50 text-amber-800 rounded px-2 py-1">
                  Requires procurement write permission.
                </p>
              )}
              <div className="grid gap-3 sm:grid-cols-2">
                {/* Material — raw or semi_finished components */}
                <div className="sm:col-span-2">
                  <SubcontractMaterialSelector
                    value={issueMat}
                    onChange={(id) => handleIssueMaterialChange(id)}
                    typeFilter="raw"
                    label="Component material"
                    placeholder="Search raw or semi-finished components…"
                    disabled={!allowOps}
                  />
                  {issuePendingQty !== null && issuePendingQty > 0 && (
                    <p className="text-xs text-blue-700 mt-1">
                      Note: This material is in the BOM with {issuePendingQty} units remaining. Consider using the "Issue Material" button in the Required Components section above.
                    </p>
                  )}
                  {issuePendingQty === 0 && issueMat && (
                    <p className="text-xs text-emerald-700 mt-1">✓ This BOM component has been fully issued</p>
                  )}
                </div>
                <div className="space-y-1">
                  <Label className="text-sm">Quantity</Label>
                  <Input type="number" min={0.001} step={0.001}
                    value={issueQty} onChange={(e) => setIssueQty(e.target.value)} disabled={!allowOps} />
                </div>
                <div className="space-y-1">
                  <Label className="text-sm">From warehouse</Label>
                  <Select value={issueFrom} onValueChange={setIssueFrom} disabled={!allowOps}>
                    <SelectTrigger disabled={!allowOps}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {warehouses.map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <Label className="text-sm">
                    Batch ID <span className="text-muted-foreground text-xs">(optional — for traceability)</span>
                  </Label>
                  <Input value={issueBatchId} onChange={(e) => setIssueBatchId(e.target.value)}
                    disabled={!allowOps} placeholder="Leave blank if not batch-tracked" />
                </div>
              </div>
              <Button onClick={issue} disabled={!allowOps || busy || !issueMat || !issueFrom} className="w-full sm:w-auto">
                {busy ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Issuing…</> : "Issue to vendor"}
              </Button>
            </div>
          )}
        </section>
      )}

      {/* ── Receive output ───────────────────────────────────────────── */}
      {canReceive && (
        <section className="border rounded-lg p-3 sm:p-4 space-y-4">
          <div>
            <h2 className="font-medium flex items-center gap-2 text-sm sm:text-base">
              <Package className="h-4 w-4" />Receive processed output
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Receives the finished/processed semi-finished material into your warehouse stock.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {/* Output material — semi-finished or finished */}
            <div className="sm:col-span-2">
              <SubcontractMaterialSelector
                value={recvMat}
                onChange={(id) => setRecvMat(id)}
                typeFilter="semi_finished"
                label="Output material (what vendor returns)"
                placeholder="Search semi-finished materials…"
                disabled={!allowOps}
              />
            </div>
            <div className="space-y-1">
              <Label>Quantity received</Label>
              <Input type="number" min={0.001} step={0.001}
                value={recvQty} onChange={(e) => setRecvQty(e.target.value)} disabled={!allowOps} />
            </div>
            <div className="space-y-1">
              <Label>To warehouse</Label>
              <Select value={recvWh} onValueChange={setRecvWh} disabled={!allowOps}>
                <SelectTrigger disabled={!allowOps}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {warehouses.map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label>Output batch number <span className="text-muted-foreground text-xs">(auto-generated if blank)</span></Label>
              <Input value={recvBatchNum} onChange={(e) => setRecvBatchNum(e.target.value)}
                disabled={!allowOps} placeholder={`SCO-${order.order_number}`} />
            </div>
          </div>
          {order.output_batch_id && (
            <p className="text-xs text-emerald-700 bg-emerald-50 rounded px-2 py-1">
              ✓ Output batch already recorded: {order.output_batch_id.slice(0, 8)}…
            </p>
          )}
          <Button onClick={receive} disabled={!allowOps || busy || !recvMat || !recvWh} className="w-full sm:w-auto">
            {busy ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Receiving…</> : "Receive into stock"}
          </Button>
        </section>
      )}

      {/* ── Return unused material ───────────────────────────────────── */}
      {canReturn && (
        <section className="border rounded-lg p-4 space-y-4">
          <div>
            <h2 className="font-medium flex items-center gap-2">
              <RotateCcw className="h-4 w-4" />Return unused material
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Returns raw/semi-finished materials from the vendor back to your warehouse.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <SubcontractMaterialSelector
                value={retMat}
                onChange={(id) => setRetMat(id)}
                typeFilter="raw"
                label="Material to return"
                placeholder="Search material…"
                disabled={!allowOps}
              />
            </div>
            <div className="space-y-1">
              <Label>Quantity</Label>
              <Input type="number" min={0.001} step={0.001}
                value={retQty} onChange={(e) => setRetQty(e.target.value)} disabled={!allowOps} />
            </div>
            <div className="space-y-1">
              <Label>Return to warehouse</Label>
              <Select value={retLoc} onValueChange={setRetLoc} disabled={!allowOps}>
                <SelectTrigger disabled={!allowOps}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {warehouses.map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button variant="outline" onClick={returnMat} disabled={!allowOps || busy || !retMat || !retLoc} className="w-full sm:w-auto">
            {busy ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Returning…</> : "Return to warehouse"}
          </Button>
        </section>
      )}

      {/* ── Issue history ────────────────────────────────────────────── */}
      <section>
        <h2 className="font-medium mb-2">Issue history</h2>
        {order.issues.length === 0 ? (
          <p className="text-sm text-muted-foreground">No materials issued yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Returned</TableHead>
                <TableHead>Batch</TableHead>
                <TableHead>Issued</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {order.issues.map((i) => (
                <TableRow key={i.id}>
                  <TableCell className="font-mono text-xs">{i.material_id.slice(0, 8)}…</TableCell>
                  <TableCell className="text-right">{i.quantity}</TableCell>
                  <TableCell className="text-right">{i.returned_quantity ?? 0}</TableCell>
                  <TableCell className="text-xs">
                    {i.batch_number ?? (i.batch_id ? i.batch_id.slice(0, 8) + "…" : "—")}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {i.issued_at ? new Date(i.issued_at).toLocaleDateString() : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>

      {/* ── Traceability panel ───────────────────────────────────────── */}
      {showTrace && traceability && (
        <section className="border rounded-lg p-4 space-y-4 bg-slate-50">
          <div className="flex items-center justify-between">
            <h2 className="font-medium flex items-center gap-2">
              <Boxes className="h-4 w-4" />Traceability chain
            </h2>
            <Button variant="ghost" size="sm" onClick={() => setShowTrace(false)}>Close</Button>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Raw material batches sent to vendor
            </p>
            {((traceability.input_batches ?? []) as Record<string, unknown>[]).length === 0 && (
              <p className="text-xs text-muted-foreground">None recorded.</p>
            )}
            {((traceability.input_batches ?? []) as Record<string, unknown>[]).map((b, i) => {
              const materialCode = b.material_code ? String(b.material_code) : (b.material_id ? String(b.material_id).slice(0,8) : 'N/A');
              const materialName = b.material_name ? String(b.material_name) : 'N/A';
              const quantity = typeof b.quantity === 'number' ? b.quantity : (b.quantity ? Number(b.quantity) : 0);
              const batchNumber = b.batch_number ? String(b.batch_number) : null;
              const issuedAt = b.issued_at ? String(b.issued_at) : null;
              
              return (
              <div key={i} className="text-xs border rounded px-2 py-1.5 mb-1 bg-white flex items-center gap-3">
                <span className="font-mono font-medium">{materialCode}</span>
                <span className="text-muted-foreground">{materialName}</span>
                <span>Qty: {quantity}</span>
                {batchNumber && <span className="font-mono text-blue-700">Batch: {batchNumber}</span>}
                {issuedAt && <span className="text-muted-foreground ml-auto">{new Date(issuedAt).toLocaleDateString()}</span>}
              </div>
              );
            })}
          </div>

          {Boolean(traceability.output_batch) && (
            <OutputBatchDisplay outputBatch={traceability.output_batch as Record<string, unknown>} />
          )}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Inventory transactions ({((traceability.inventory_transactions ?? []) as unknown[]).length})
            </p>
            {((traceability.inventory_transactions ?? []) as Record<string, unknown>[]).map((tx, i) => {
              const txType = tx.type ? String(tx.type) : 'N/A';
              const txQuantity = typeof tx.quantity === 'number' ? tx.quantity : (tx.quantity ? Number(tx.quantity) : 0);
              const txRemarks = tx.remarks ? String(tx.remarks) : '';
              
              return (
                <div key={i} className="text-xs border rounded px-2 py-1 mb-1 bg-white flex gap-2">
                  <span className="font-medium capitalize">{txType}</span>
                  <span>Qty: {txQuantity}</span>
                  {txRemarks && <span className="text-muted-foreground">{txRemarks}</span>}
                </div>
              )
            })}
          </div>
        </section>
      )}

    </div>
  )
}
