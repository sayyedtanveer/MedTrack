import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { supplyChainApi, type PurchaseOrder, type Supplier } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import type { Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"
import { Plus, Trash2 } from "lucide-react"

type LineDraft = { material_id: string; quantity: string; unit_price: string }
type ShortagePrefill = {
  lines: { material_id: string; quantity: number; unit_price?: number }[]
  notes?: string
  expectedDelivery?: string
}

export default function PurchaseOrdersPage() {
  const { toast } = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const [pos, setPos] = useState<PurchaseOrder[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [open, setOpen] = useState(false)
  const [supplierId, setSupplierId] = useState("")
  const [expectedDelivery, setExpectedDelivery] = useState("")
  const [notes, setNotes] = useState("")
  const [lines, setLines] = useState<LineDraft[]>([{ material_id: "", quantity: "1", unit_price: "0" }])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    const [pr, sr, mr] = await Promise.all([
      supplyChainApi.listPurchaseOrders(),
      supplyChainApi.listSuppliers(),
      materialService.getMaterials({ page: 1, page_size: 200 }),
    ])
    setPos(pr.data)
    setSuppliers(sr.data)
    setMaterials(mr.items.filter((m) => m.material_type === "raw"))
  }

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load", variant: "destructive" }))
  }, [toast])

  useEffect(() => {
    const prefill = (location.state as { shortagePrefill?: ShortagePrefill } | null)?.shortagePrefill
    if (!prefill) {
      return
    }

    setOpen(true)
    setNotes(prefill.notes ?? "")
    setExpectedDelivery(prefill.expectedDelivery ?? "")
    setLines(
      prefill.lines.length
        ? prefill.lines.map((line) => ({
            material_id: line.material_id,
            quantity: String(line.quantity),
            unit_price: String(line.unit_price ?? 0),
          }))
        : [{ material_id: "", quantity: "1", unit_price: "0" }],
    )
    navigate(location.pathname, { replace: true, state: null })
  }, [location.pathname, location.state, navigate])

  const addLine = () => setLines((l) => [...l, { material_id: "", quantity: "1", unit_price: "0" }])
  const removeLine = (i: number) => setLines((l) => l.filter((_, j) => j !== i))
  const setLine = (i: number, patch: Partial<LineDraft>) =>
    setLines((l) => l.map((row, j) => (j === i ? { ...row, ...patch } : row)))

  const submitCreate = async () => {
    if (!supplierId) {
      toast({ title: "Select a supplier", variant: "destructive" })
      return
    }
    const clean = lines
      .filter((x) => x.material_id)
      .map((x) => ({
        material_id: x.material_id,
        quantity: Number(x.quantity),
        unit_price: Number(x.unit_price),
      }))
    if (!clean.length) {
      toast({ title: "Add at least one line", variant: "destructive" })
      return
    }
    setLoading(true)
    try {
      await supplyChainApi.createPurchaseOrder({
        supplier_id: supplierId,
        expected_delivery: expectedDelivery || undefined,
        notes: notes || undefined,
        lines: clean,
      })
      toast({ title: "Purchase order created" })
      setOpen(false)
      setSupplierId("")
      setExpectedDelivery("")
      setNotes("")
      setLines([{ material_id: "", quantity: "1", unit_price: "0" }])
      await load()
    } catch {
      toast({ title: "Create failed", variant: "destructive" })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Purchase orders</h1>
          <p className="text-sm text-muted-foreground">Draft → Send → Acknowledge → Receive</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New PO
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create purchase order</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Use this form to cover raw-material shortages before production release.
              </div>
              <div className="space-y-2">
                <Label>Supplier</Label>
                <Select value={supplierId} onValueChange={setSupplierId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose supplier" />
                  </SelectTrigger>
                  <SelectContent>
                    {suppliers.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.code} — {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Expected delivery</Label>
                <Input type="date" value={expectedDelivery} onChange={(e) => setExpectedDelivery(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Notes</Label>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label>Lines (raw materials)</Label>
                  <Button type="button" variant="outline" size="sm" onClick={addLine}>
                    Add line
                  </Button>
                </div>
                {lines.map((line, i) => (
                  <div key={i} className="flex flex-wrap gap-2 items-end border rounded-md p-2">
                    <div className="flex-1 min-w-[140px]">
                      <Label className="text-xs">Material</Label>
                      <Select value={line.material_id} onValueChange={(v) => setLine(i, { material_id: v })}>
                        <SelectTrigger>
                          <SelectValue placeholder="Material" />
                        </SelectTrigger>
                        <SelectContent className="max-h-60">
                          {materials.map((m) => (
                            <SelectItem key={m.id} value={m.id}>
                              {m.code} — {m.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="w-24">
                      <Label className="text-xs">Qty</Label>
                      <Input
                        type="number"
                        value={line.quantity}
                        onChange={(e) => setLine(i, { quantity: e.target.value })}
                      />
                    </div>
                    <div className="w-28">
                      <Label className="text-xs">Unit price</Label>
                      <Input
                        type="number"
                        value={line.unit_price}
                        onChange={(e) => setLine(i, { unit_price: e.target.value })}
                      />
                    </div>
                    {lines.length > 1 && (
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeLine(i)} aria-label="Remove line">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <DialogFooter>
              <Button onClick={submitCreate} disabled={loading}>
                Create PO
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>PO #</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Date</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {pos.map((p) => (
            <TableRow key={p.id}>
              <TableCell className="font-mono">{p.po_number}</TableCell>
              <TableCell>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{p.status}</span>
              </TableCell>
              <TableCell>{p.order_date}</TableCell>
              <TableCell className="text-right tabular-nums">
                {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(p.total_amount)}
              </TableCell>
              <TableCell className="text-right">
                <Button variant="link" asChild>
                  <Link to={`/procurement/purchase-orders/${p.id}`}>Open</Link>
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {pos.length === 0 && <p className="text-sm text-muted-foreground">No purchase orders yet.</p>}
    </div>
  )
}
