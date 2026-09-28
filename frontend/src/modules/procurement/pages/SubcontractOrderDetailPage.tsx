import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import {
  supplyChainApi,
  type SubcontractOrderDetail,
  type SubcontractOrderLine,
} from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import { SubcontractMaterialSelector } from "../components/SubcontractMaterialSelector"
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
  CheckCircle, XCircle, Package, RotateCcw, ArrowLeftRight, Boxes, Loader2,
} from "lucide-react"

// ── helpers ────────────────────────────────────────────────────────────────────

function locKind(l: Location & { location_type?: string }) {
  return l.location_type ?? (l as { type?: string }).type ?? ""
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
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast({ title: detail || "Operation failed", variant: "destructive" })
    } finally {
      setBusy(false)
    }
  }

  const approve = () =>
    act(() => supplyChainApi.approveSubcontractOrder(orderId!).then(() => undefined),
      "Order approved — component list loaded from BOM")

  const cancel = () =>
    act(() => supplyChainApi.cancelSubcontractOrder(orderId!).then(() => undefined), "Order cancelled")

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
          <div>
            <h1 className="text-2xl font-semibold font-mono">{order.order_number}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Output qty: {order.quantity} · Received: {order.received_quantity ?? 0}
              {order.due_date && ` · Due: ${order.due_date}`}
            </p>
            {order.notes && <p className="text-xs text-muted-foreground mt-1">{order.notes}</p>}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(order.status)}`}>
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

      {/* ── Component lines ──────────────────────────────────────────── */}
      {order.lines.length > 0 && (
        <section>
          <h2 className="font-medium mb-2 flex items-center gap-2">
            <Package className="h-4 w-4" />Required components
            <span className="text-xs text-muted-foreground font-normal">(from BOM snapshot)</span>
          </h2>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className="text-right">Required</TableHead>
                <TableHead className="text-right">Issued</TableHead>
                <TableHead className="text-right">Returned</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {order.lines.map((ln: SubcontractOrderLine) => (
                <TableRow key={ln.id}
                  className={issueMat === ln.material_id ? "bg-blue-50" : ""}
                >
                  <TableCell className="font-mono text-xs">{ln.material_id.slice(0, 8)}…</TableCell>
                  <TableCell className="text-right">{ln.required_quantity}</TableCell>
                  <TableCell className="text-right">{ln.issued_quantity}</TableCell>
                  <TableCell className="text-right">{ln.returned_quantity}</TableCell>
                  <TableCell>
                    <Badge variant={ln.status === "issued" ? "default" : "secondary"}>
                      {ln.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </section>
      )}

      {/* ── Issue materials ──────────────────────────────────────────── */}
      {canIssue && (
        <section className="border rounded-lg p-4 space-y-4">
          <div>
            <h2 className="font-medium flex items-center gap-2">
              <ArrowLeftRight className="h-4 w-4" />Issue material to vendor
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Moves stock from your warehouse to the vendor's subcontractor location.
            </p>
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
                typeFilter="raw"           /* "raw" also includes semi_finished in the component */
                label="Component material"
                placeholder="Search raw or semi-finished components…"
                disabled={!allowOps}
              />
              {issuePendingQty !== null && issuePendingQty > 0 && (
                <p className="text-xs text-blue-700 mt-1">
                  Pending from BOM: {issuePendingQty} units
                </p>
              )}
              {issuePendingQty === 0 && issueMat && (
                <p className="text-xs text-emerald-700 mt-1">✓ This component has been fully issued</p>
              )}
            </div>
            <div className="space-y-1">
              <Label>Quantity</Label>
              <Input type="number" min={0.001} step={0.001}
                value={issueQty} onChange={(e) => setIssueQty(e.target.value)} disabled={!allowOps} />
            </div>
            <div className="space-y-1">
              <Label>From warehouse</Label>
              <Select value={issueFrom} onValueChange={setIssueFrom} disabled={!allowOps}>
                <SelectTrigger disabled={!allowOps}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {warehouses.map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label>Batch ID <span className="text-muted-foreground text-xs">(UUID — paste from inventory for full traceability)</span></Label>
              <Input value={issueBatchId} onChange={(e) => setIssueBatchId(e.target.value)}
                disabled={!allowOps} placeholder="Optional — leave blank if not batch-tracked" />
            </div>
          </div>
          <Button onClick={issue} disabled={!allowOps || busy || !issueMat || !issueFrom}>
            {busy ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Issuing…</> : "Issue to vendor"}
          </Button>
        </section>
      )}

      {/* ── Receive output ───────────────────────────────────────────── */}
      {canReceive && (
        <section className="border rounded-lg p-4 space-y-4">
          <div>
            <h2 className="font-medium flex items-center gap-2">
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
          <Button onClick={receive} disabled={!allowOps || busy || !recvMat || !recvWh}>
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
          <Button variant="outline" onClick={returnMat} disabled={!allowOps || busy || !retMat || !retLoc}>
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
            {((traceability.input_batches ?? []) as Record<string, unknown>[]).map((b, i) => (
              <div key={i} className="text-xs border rounded px-2 py-1.5 mb-1 bg-white flex items-center gap-3">
                <span className="font-mono font-medium">{b.material_code as string ?? (b.material_id as string)?.slice(0,8)}</span>
                <span className="text-muted-foreground">{b.material_name as string}</span>
                <span>Qty: {b.quantity as number}</span>
                {b.batch_number && <span className="font-mono text-blue-700">Batch: {b.batch_number as string}</span>}
                {b.issued_at && <span className="text-muted-foreground ml-auto">{new Date(b.issued_at as string).toLocaleDateString()}</span>}
              </div>
            ))}
          </div>

          {traceability.output_batch && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Processed output batch
              </p>
              {(() => {
                const ob = traceability.output_batch as Record<string, unknown>
                return (
                  <div className="text-xs border rounded px-2 py-1.5 bg-white flex items-center gap-3">
                    <span className="font-mono font-medium text-emerald-700">{ob.batch_number as string}</span>
                    <span className="text-muted-foreground">{ob.material_name as string}</span>
                    <span>Qty: {ob.quantity as number}</span>
                    <Badge variant="outline" className="text-xs">{ob.status as string}</Badge>
                  </div>
                )
              })()}
            </div>
          )}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Inventory transactions ({((traceability.inventory_transactions ?? []) as unknown[]).length})
            </p>
            {((traceability.inventory_transactions ?? []) as Record<string, unknown>[]).map((tx, i) => (
              <div key={i} className="text-xs border rounded px-2 py-1 mb-1 bg-white flex gap-2">
                <span className="font-medium capitalize">{tx.type as string}</span>
                <span>Qty: {tx.quantity as number}</span>
                <span className="text-muted-foreground">{tx.remarks as string}</span>
              </div>
            ))}
          </div>
        </section>
      )}

    </div>
  )
}
