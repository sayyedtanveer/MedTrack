import { useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import { tenantService } from "@/services/tenant.service"
import type { Location } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

function locKind(l: Location & { location_type?: string }) {
  return l.location_type ?? (l as { type?: string }).type ?? ""
}

type CostDiff = {
  materialId: string
  materialName: string
  currentCost: number
  newPrice: number
  uom: string
}

export default function GrnPage() {
  const { toast } = useToast()
  const [searchParams] = useSearchParams()

  const { data: tenantProfile } = useQuery({
    queryKey: ["tenant-profile"],
    queryFn: () => tenantService.getProfile(),
  })
  const currencyCode = tenantProfile?.currency_code ?? ""

  const [poList, setPoList] = useState<PurchaseOrder[]>([])
  const [poId, setPoId] = useState("")
  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [locations, setLocations] = useState<(Location & { location_type?: string })[]>([])
  const [warehouseId, setWarehouseId] = useState("")
  const [qtyByLine, setQtyByLine] = useState<Record<string, string>>({})

  // Material map: keyed by material_id, holds current_cost and name
  const [materialMap, setMaterialMap] = useState<Record<string, { name: string; current_cost: number }>>({})

  // Standard Cost Prompt state
  const [showCostPrompt, setShowCostPrompt] = useState(false)
  const [costDiffs, setCostDiffs] = useState<CostDiff[]>([])
  const [updatingCost, setUpdatingCost] = useState(false)

  useEffect(() => {
    materialService.getLocations().then((locs) => {
      const typed = locs as (Location & { location_type?: string })[]
      setLocations(typed)
      const wh = typed.find((l) => locKind(l) === "warehouse")
      if (wh) setWarehouseId(wh.id)
    })
  }, [])

  useEffect(() => {
    supplyChainApi
      .listPurchaseOrders()
      .then((r) => {
        setPoList(r.data)
        const receivable = r.data.filter((p) => ["sent", "acknowledged", "partial"].includes(p.status))
        const fromUrl = searchParams.get("poId")
        setPoId((prev) => {
          if (fromUrl) return fromUrl
          if (prev) return prev
          return receivable[0]?.id ?? ""
        })
      })
      .catch(() => {})
  }, [searchParams])

  useEffect(() => {
    if (!poId) {
      setPo(null)
      setMaterialMap({})
      return
    }
    supplyChainApi
      .getPurchaseOrder(poId)
      .then(async (r) => {
        const poData = r.data
        setPo(poData)
        const q: Record<string, string> = {}
        poData.lines.forEach((l) => {
          const max = l.quantity - l.received_quantity
          q[l.id] = max > 0 ? String(max) : "0"
        })
        setQtyByLine(q)

        // Task 7.1: Fetch material records for cost comparison
        const uniqueMatIds = [...new Set(poData.lines.map((l) => l.material_id))]
        const matEntries = await Promise.all(
          uniqueMatIds.map(async (matId) => {
            try {
              const mat = await materialService.getMaterial(matId)
              return [matId, { name: (mat as any).name ?? matId, current_cost: Number((mat as any).current_cost ?? 0) }] as const
            } catch {
              return [matId, { name: matId, current_cost: 0 }] as const
            }
          })
        )
        setMaterialMap(Object.fromEntries(matEntries))
      })
      .catch(() => toast({ title: "Could not load PO", variant: "destructive" }))
  }, [poId, toast])

  const warehouseLocations = useMemo(
    () => locations.filter((l) => locKind(l) === "warehouse" && l.is_active),
    [locations]
  )

  // Task 7.4: Update Standard Cost for all diffs
  const handleUpdateCost = async () => {
    setUpdatingCost(true)
    try {
      for (const diff of costDiffs) {
        await materialService.updateMaterial(diff.materialId, { current_cost: diff.newPrice } as any)
        // Update local map so re-opens show fresh data
        setMaterialMap((prev) => ({
          ...prev,
          [diff.materialId]: { ...prev[diff.materialId], current_cost: diff.newPrice },
        }))
      }
      toast({ title: "Standard Cost updated successfully" })
      setShowCostPrompt(false)
    } catch {
      toast({ title: "Failed to update Standard Cost. Please try again.", variant: "destructive" })
      // Leave dialog open for retry
    } finally {
      setUpdatingCost(false)
    }
  }

  // Task 7.4: Ignore — close dialog, no changes
  const handleIgnore = () => {
    setShowCostPrompt(false)
    setCostDiffs([])
  }

  const submit = async () => {
    if (!po || !warehouseId) {
      toast({ title: "Select warehouse location", variant: "destructive" })
      return
    }
    const lines = po.lines
      .map((l) => ({
        line_id: l.id,
        quantity: Number(qtyByLine[l.id] || 0),
      }))
      .filter((x) => x.quantity > 0)
    if (!lines.length) {
      toast({ title: "Enter quantity for at least one line", variant: "destructive" })
      return
    }
    try {
      await supplyChainApi.receiveGoods(po.id, {
        lines,
        warehouse_location_id: warehouseId,
      })
      toast({ title: "Goods received" })
      const r = await supplyChainApi.getPurchaseOrder(po.id)
      setPo(r.data)

      // Task 7.2: Build cost diff list after successful GRN acceptance
      const diffs: CostDiff[] = po.lines
        .filter((l) => Number(qtyByLine[l.id] || 0) > 0)
        .filter((l) => {
          const mat = materialMap[l.material_id]
          return mat && Number(l.unit_price) !== mat.current_cost
        })
        .map((l) => {
          const mat = materialMap[l.material_id]
          const units = (mat as any)?.uom ?? ""
          return {
            materialId: l.material_id,
            materialName: mat?.name ?? l.material_id,
            currentCost: mat?.current_cost ?? 0,
            newPrice: Number(l.unit_price),
            uom: units,
          }
        })

      // Task 7.2: Show prompt only if there are differences (REQ-SC-003 AC6)
      if (diffs.length > 0) {
        setCostDiffs(diffs)
        setShowCostPrompt(true)
      }
    } catch (e: unknown) {
      const msg = e && typeof e === "object" && "response" in e ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail : null
      toast({ title: msg || "Receive failed", variant: "destructive" })
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link to="/procurement/purchase-orders">← Purchase orders</Link>
        </Button>
        <h1 className="text-2xl font-semibold">Goods receipt (GRN)</h1>
        <p className="text-sm text-muted-foreground">Post receipt against an open PO. Stock uses InventoryService.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Purchase order</Label>
          <Select value={poId} onValueChange={setPoId}>
            <SelectTrigger>
              <SelectValue placeholder="Select PO" />
            </SelectTrigger>
            <SelectContent>
              {poList
                .filter((p) => ["sent", "acknowledged", "partial"].includes(p.status))
                .map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.po_number} ({p.status})
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Warehouse location</Label>
          <Select value={warehouseId} onValueChange={setWarehouseId}>
            <SelectTrigger>
              <SelectValue placeholder="Warehouse" />
            </SelectTrigger>
            <SelectContent>
              {warehouseLocations.map((l) => (
                <SelectItem key={l.id} value={l.id}>
                  {l.name} ({locKind(l)})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {warehouseLocations.length === 0 && (
        <p className="text-sm text-amber-700">
          No warehouse location found. Create one under Inventory → master data (type: warehouse).
        </p>
      )}

      {po && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className="text-right">Unit Price</TableHead>
                <TableHead className="text-right">Remaining</TableHead>
                <TableHead className="text-right w-36">Receive now</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {po.lines.map((l) => {
                const rem = l.quantity - l.received_quantity
                const mat = materialMap[l.material_id]
                return (
                  <TableRow key={l.id}>
                    <TableCell className="text-sm">
                      {mat?.name ?? <span className="font-mono text-xs">{l.material_id.slice(0, 8)}…</span>}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(l.unit_price))}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{rem.toFixed(3)}</TableCell>
                    <TableCell className="text-right">
                      <Input
                        type="number"
                        className="text-right"
                        value={qtyByLine[l.id] ?? ""}
                        onChange={(e) => setQtyByLine((m) => ({ ...m, [l.id]: e.target.value }))}
                        min={0}
                        max={rem}
                        step="0.001"
                      />
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          <Button onClick={submit}>Post receipt</Button>
        </>
      )}

      {/* Task 7.3: StandardCostPromptDialog — REQ-SC-003 */}
      <Dialog open={showCostPrompt} onOpenChange={(open) => { if (!open && !updatingCost) handleIgnore() }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Update Standard Cost?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground mb-3">
            The purchase prices on this GRN differ from the current Standard Costs.
            Do you want to update the Standard Cost for these materials?
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className="text-right">Current Std Cost</TableHead>
                <TableHead className="text-right">New Purchase Price</TableHead>
                <TableHead className="text-right">Difference</TableHead>
                <TableHead className="text-right">Change</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {costDiffs.map((d) => {
                const diffAmt = d.newPrice - d.currentCost
                const diffPct = d.currentCost > 0 ? (diffAmt / d.currentCost) * 100 : null
                const isUp = diffAmt > 0
                const isDown = diffAmt < 0
                const fmt = (n: number) =>
                  n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 4 })
                return (
                  <TableRow key={d.materialId}>
                    <TableCell className="text-sm">
                      <div>{d.materialName}</div>
                      {d.uom && <div className="text-xs text-muted-foreground">{d.uom}</div>}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {currencyCode} {fmt(d.currentCost)}
                    </TableCell>
                    <TableCell className="text-right text-sm font-medium tabular-nums">
                      {currencyCode} {fmt(d.newPrice)}
                    </TableCell>
                    <TableCell
                      className={`text-right text-sm font-semibold tabular-nums ${
                        isUp ? "text-red-600" : isDown ? "text-green-600" : "text-muted-foreground"
                      }`}
                    >
                      {diffAmt >= 0 ? "+" : ""}{currencyCode} {fmt(Math.abs(diffAmt))}
                    </TableCell>
                    <TableCell
                      className={`text-right text-sm tabular-nums ${
                        isUp ? "text-red-500" : isDown ? "text-green-500" : "text-muted-foreground"
                      }`}
                    >
                      {diffPct !== null
                        ? `${diffPct >= 0 ? "+" : ""}${diffPct.toFixed(2)}%`
                        : "—"}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          <DialogFooter className="gap-2 mt-4">
            <Button variant="outline" onClick={handleIgnore} disabled={updatingCost}>
              Ignore
            </Button>
            <Button onClick={handleUpdateCost} disabled={updatingCost}>
              {updatingCost ? "Updating…" : "Update Standard Cost"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
