import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { supplyChainApi, type SubcontractOrderSummary, type Supplier } from "@/services/supply-chain.service"
import { SubcontractMaterialSelector } from "../components/SubcontractMaterialSelector"
import type { Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { Plus, Factory, Loader2, Info, Package } from "lucide-react"
import { materialService } from "@/services/material.service"

function statusColor(s: string): "default" | "secondary" | "outline" | "destructive" {
  switch (s) {
    case "draft":             return "secondary"
    case "approved":          return "default"
    case "materials_issued":  return "default"
    case "partially_received": return "default"
    case "completed":         return "default"
    case "cancelled":         return "destructive"
    default:                  return "secondary"
  }
}

type BOMOption = {
  id: string
  version: string
  line_count: number
  valid_from: string | null
  link_type: "explicit" | "code_match"
}

type BOMLine = {
  id: string
  material_id: string | null
  quantity: number
  scrap_percentage: number
  material_code?: string
  material_name?: string
}

export default function SubcontractListPage() {
  const { toast } = useToast()
  const [orders, setOrders] = useState<SubcontractOrderSummary[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [open, setOpen] = useState(false)
  const [creating, setCreating] = useState(false)

  // Form state
  const [supplierId, setSupplierId] = useState("")
  const [outputMaterialId, setOutputMaterialId] = useState("")
  const [outputMaterial, setOutputMaterial] = useState<Material | null>(null)
  const [bomOptions, setBomOptions] = useState<BOMOption[]>([])
  const [bomId, setBomId] = useState("")
  const [bomLoading, setBomLoading] = useState(false)
  const [bomLinkType, setBomLinkType] = useState<"explicit" | "code_match" | null>(null)
  const [qty, setQty] = useState("1")
  const [dueDate, setDueDate] = useState("")
  const [notes, setNotes] = useState("")

  // Component preview
  const [previewLines, setPreviewLines] = useState<BOMLine[]>([])
  const [previewLoading, setPreviewLoading] = useState(false)

  const load = async () => {
    const [o, s] = await Promise.all([
      supplyChainApi.listSubcontractOrders(),
      supplyChainApi.listSuppliers(),
    ])
    setOrders(o.data.items ?? [])
    setSuppliers(s.data)
  }

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load", variant: "destructive" }))
  }, [toast])

  // Load BOM options when output material changes
  const handleOutputMaterialChange = async (id: string, mat: Material) => {
    setOutputMaterialId(id)
    setOutputMaterial(mat)
    setBomId("")
    setBomOptions([])
    setBomLinkType(null)
    setPreviewLines([])
    if (!id) return
    setBomLoading(true)
    try {
      const { data } = await supplyChainApi.getBOMsForSubcontractMaterial(id)
      setBomOptions(data.boms)
      if (data.boms.length === 1) {
        setBomId(data.boms[0].id)
        setBomLinkType(data.boms[0].link_type)
        await loadBomPreview(data.boms[0].id, Number(qty))
      }
    } catch {
      // Non-fatal — user can still create without BOM
    } finally {
      setBomLoading(false)
    }
  }

  // Load BOM component preview, enriching with material names
  const loadBomPreview = async (selectedBomId: string, orderQty: number) => {
    setPreviewLoading(true)
    setPreviewLines([])
    try {
      const { data } = await supplyChainApi.getBOMLines(selectedBomId)
      const lines = data.lines ?? []
      // Resolve material names in parallel
      const enriched = await Promise.all(
        lines
          .filter((l) => l.material_id)
          .map(async (l) => {
            try {
              const m = await materialService.getMaterial(l.material_id!)
              return {
                ...l,
                material_code: m.code,
                material_name: m.name,
                quantity: l.quantity * orderQty,
              }
            } catch {
              return { ...l, quantity: l.quantity * orderQty }
            }
          })
      )
      setPreviewLines(enriched)
    } catch {
      // Preview is informational — failure is non-fatal
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleBomChange = async (id: string) => {
    setBomId(id)
    const opt = bomOptions.find((b) => b.id === id)
    setBomLinkType(opt?.link_type ?? null)
    if (id) await loadBomPreview(id, Number(qty))
    else setPreviewLines([])
  }

  const handleQtyChange = async (val: string) => {
    setQty(val)
    if (bomId && val) await loadBomPreview(bomId, Number(val))
  }

  const resetForm = () => {
    setSupplierId(""); setOutputMaterialId(""); setOutputMaterial(null)
    setBomId(""); setBomOptions([]); setBomLinkType(null)
    setQty("1"); setDueDate(""); setNotes(""); setPreviewLines([])
  }

  const create = async () => {
    if (!supplierId || !outputMaterialId) {
      toast({ title: "Supplier and output material are required", variant: "destructive" })
      return
    }
    if (bomOptions.length > 0 && !bomId) {
      toast({ title: "Please select a BOM to calculate required component quantities", variant: "destructive" })
      return
    }
    setCreating(true)
    try {
      await supplyChainApi.createSubcontractOrder({
        supplier_id: supplierId,
        product_id: outputMaterialId,
        quantity: Number(qty),
        bom_id: bomId || null,
        due_date: dueDate || null,
        notes: notes || null,
      })
      toast({ title: "Subcontract order created" })
      setOpen(false)
      resetForm()
      await load()
    } catch {
      toast({ title: "Failed to create order", variant: "destructive" })
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <Factory className="h-6 w-6 text-muted-foreground flex-shrink-0 mt-1" />
          <div className="min-w-0 flex-1">
            <h1 className="text-xl sm:text-2xl font-semibold">Subcontracting</h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Send materials to a vendor for outside processing and receive semi-finished output.
            </p>
          </div>
        </div>

        <Dialog open={open} onOpenChange={(v) => { if (!v) resetForm(); setOpen(v) }}>
          <DialogTrigger asChild>
            <Button className="w-full sm:w-auto flex-shrink-0">
              <Plus className="mr-2 h-4 w-4" />New order
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>New subcontract order</DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Supplier */}
              <div className="space-y-2">
                <Label>Supplier <span className="text-destructive">*</span></Label>
                <Select value={supplierId} onValueChange={setSupplierId}>
                  <SelectTrigger><SelectValue placeholder="Select vendor…" /></SelectTrigger>
                  <SelectContent>
                    {suppliers.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.code} — {s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">The vendor who will perform the outside processing.</p>
              </div>

              {/* Output material */}
              <SubcontractMaterialSelector
                value={outputMaterialId}
                onChange={handleOutputMaterialChange}
                typeFilter="semi_finished"
                label="Output material"
                placeholder="Search semi-finished materials…"
                required
              />
              {outputMaterial && (
                <p className="text-xs text-muted-foreground -mt-1">
                  <span className="font-mono">{outputMaterial.code}</span> · Type: {outputMaterial.material_type}
                </p>
              )}
              {!outputMaterialId && (
                <p className="text-xs text-muted-foreground -mt-1">
                  Select the semi-finished material that the vendor will produce.
                  If it doesn't exist yet, create it first in Inventory → Materials.
                </p>
              )}

              {/* BOM selector */}
              {outputMaterialId && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-1">
                    BOM
                    {bomLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                    {bomOptions.length > 0 && <span className="text-destructive ml-1">*</span>}
                  </Label>

                  {bomOptions.length === 0 && !bomLoading && (
                    <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
                      No active BOM found for this material.
                      The order will be created without a component list — you can issue materials manually.
                      <br />
                      <span className="font-medium">Tip:</span> Create a BOM for <span className="font-mono">{outputMaterial?.code}</span> in the BOM module to enable automatic component calculation.
                    </div>
                  )}

                  {bomOptions.length > 0 && (
                    <>
                      <Select value={bomId} onValueChange={handleBomChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select BOM version…" />
                        </SelectTrigger>
                        <SelectContent>
                          {bomOptions.map((b) => (
                            <SelectItem key={b.id} value={b.id}>
                              v{b.version} · {b.line_count} components
                              {b.valid_from && ` · From ${b.valid_from.slice(0, 10)}`}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      {bomLinkType === "code_match" && (
                        <div className="flex items-start gap-1.5 text-xs text-blue-700 bg-blue-50 rounded px-2 py-1">
                          <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                          BOM found via product code match. For a more reliable link, associate this material with its product variant in the Products module.
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground">The BOM defines the raw materials required to produce the output.</p>
                    </>
                  )}
                </div>
              )}

              {/* Quantity + due date */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Quantity <span className="text-destructive">*</span></Label>
                  <Input type="number" min={0.001} step={0.001}
                    value={qty} onChange={(e) => handleQtyChange(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Due date</Label>
                  <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
                </div>
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label>Notes</Label>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional instructions for the vendor…" />
              </div>

              {/* Component preview */}
              {previewLines.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Components to be issued</span>
                    {previewLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                  </div>
                  <p className="text-xs text-muted-foreground">These materials will be issued to the selected vendor after approval.</p>
                  <div className="rounded-md border overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium">Material</th>
                          <th className="px-3 py-2 text-right font-medium">Required Qty</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {previewLines.map((l) => (
                          <tr key={l.id} className="hover:bg-slate-50">
                            <td className="px-3 py-1.5">
                              {l.material_code
                                ? <><span className="font-mono">{l.material_code}</span> — {l.material_name}</>
                                : <span className="font-mono text-muted-foreground">{l.material_id?.slice(0, 8)}…</span>
                              }
                            </td>
                            <td className="px-3 py-1.5 text-right font-mono">{l.quantity}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={() => { resetForm(); setOpen(false) }} className="w-full sm:w-auto">Cancel</Button>
              <Button onClick={create} disabled={creating} className="w-full sm:w-auto">
                {creating ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Creating…</> : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* ── Orders table ── */}
      <div className="border rounded-lg overflow-hidden">
        {/* Desktop table */}
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Output</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Due</TableHead>
                <TableHead className="text-right">Ordered</TableHead>
                <TableHead className="text-right">Received</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.map((o) => (
                <TableRow key={o.id}>
                  <TableCell className="font-mono text-sm">{o.order_number}</TableCell>
                  <TableCell className="text-sm">{o.supplier_name || "—"}</TableCell>
                  <TableCell className="text-sm">
                    <div className="max-w-[200px] truncate" title={o.product_code}>
                      {o.product_code || "—"}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusColor(o.status)} className="whitespace-nowrap">
                      {o.status.replace(/_/g, " ")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                    {o.due_date ?? "—"}
                  </TableCell>
                  <TableCell className="text-right">{o.quantity}</TableCell>
                  <TableCell className="text-right">{o.received_quantity ?? 0}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="link" size="sm" asChild>
                      <Link to={`/procurement/subcontract/${o.id}`}>Open →</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Mobile cards */}
        <div className="md:hidden divide-y">
          {orders.map((o) => (
            <Link
              key={o.id}
              to={`/procurement/subcontract/${o.id}`}
              className="block p-4 hover:bg-accent transition-colors"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="font-mono font-medium text-sm break-all">{o.order_number}</div>
                <Badge variant={statusColor(o.status)} className="shrink-0 text-xs">
                  {o.status.replace(/_/g, " ")}
                </Badge>
              </div>
              {o.supplier_name && (
                <div className="text-sm text-muted-foreground mb-1">
                  Supplier: {o.supplier_name}
                </div>
              )}
              {o.product_code && (
                <div className="text-sm text-muted-foreground mb-2 break-words">
                  Output: {o.product_code}
                </div>
              )}
              <div className="grid grid-cols-3 gap-2 text-xs mt-3">
                <div>
                  <div className="text-muted-foreground mb-1">Ordered</div>
                  <div className="font-medium">{o.quantity}</div>
                </div>
                <div>
                  <div className="text-muted-foreground mb-1">Received</div>
                  <div className="font-medium">{o.received_quantity ?? 0}</div>
                </div>
                <div>
                  <div className="text-muted-foreground mb-1">Due</div>
                  <div className="font-medium text-xs">{o.due_date ? new Date(o.due_date).toLocaleDateString() : "—"}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {orders.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Factory className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No subcontract orders yet.</p>
          <p className="text-xs mt-1">Create one to start issuing materials to a vendor for outside processing.</p>
        </div>
      )}
    </div>
  )
}
