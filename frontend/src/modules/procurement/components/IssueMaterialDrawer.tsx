import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Loader2, Package, Building2, Hash } from "lucide-react"
import type { SubcontractOrderLine } from "@/services/supply-chain.service"
import type { Location, Material } from "@/types/material.types"
import { materialService } from "@/services/material.service"

interface IssueMaterialDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  line: SubcontractOrderLine | null
  orderNumber: string
  supplierName?: string
  warehouses: Location[]
  onIssue: (data: {
    material_id: string
    quantity: number
    from_location_id: string
    batch_id: string | null
  }) => Promise<void>
  busy: boolean
}

export function IssueMaterialDrawer({
  open,
  onOpenChange,
  line,
  orderNumber,
  supplierName,
  warehouses,
  onIssue,
  busy,
}: IssueMaterialDrawerProps) {
  const [material, setMaterial] = useState<Material | null>(null)
  const [loadingMaterial, setLoadingMaterial] = useState(false)
  const [quantity, setQuantity] = useState("")
  const [warehouseId, setWarehouseId] = useState("")
  const [batchId, setBatchId] = useState("")
  const [showConfirm, setShowConfirm] = useState(false)

  // Calculate remaining quantity
  const remaining = line
    ? Math.max(
        0,
        line.required_quantity - line.issued_quantity + (line.returned_quantity || 0)
      )
    : 0

  // Load material details when line changes
  useEffect(() => {
    if (line?.material_id && open) {
      setLoadingMaterial(true)
      materialService
        .getMaterial(line.material_id)
        .then(setMaterial)
        .catch(() => setMaterial(null))
        .finally(() => setLoadingMaterial(false))
    } else {
      setMaterial(null)
    }
  }, [line?.material_id, open])

  // Reset form when dialog opens with new line
  useEffect(() => {
    if (open && line) {
      setQuantity(String(remaining > 0 ? remaining : 1))
      setShowConfirm(false)
      setBatchId("")
      // Pre-select first warehouse if available
      if (warehouses.length > 0 && !warehouseId) {
        setWarehouseId(warehouses[0].id)
      }
    }
  }, [open, line, remaining, warehouses, warehouseId])

  const handleConfirmClick = () => {
    setShowConfirm(true)
  }

  const handleFinalIssue = async () => {
    if (!line) return

    await onIssue({
      material_id: line.material_id,
      quantity: Number(quantity),
      from_location_id: warehouseId,
      batch_id: batchId.trim() || null,
    })

    // Reset and close
    setShowConfirm(false)
    onOpenChange(false)
  }

  const handleCancel = () => {
    if (showConfirm) {
      setShowConfirm(false)
    } else {
      onOpenChange(false)
    }
  }

  if (!line) return null

  const selectedWarehouse = warehouses.find((w) => w.id === warehouseId)
  const isValid = quantity && warehouseId && Number(quantity) > 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] flex flex-col">
        {!showConfirm ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Issue Material to Vendor
              </DialogTitle>
              <DialogDescription>
                Move stock from your warehouse to the subcontractor
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4 overflow-y-auto flex-1">
              {/* Context Info */}
              <div className="rounded-lg bg-slate-50 p-3 space-y-2 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Hash className="h-4 w-4" />
                  <span className="font-medium">Subcontract Order:</span>
                  <span className="font-mono">{orderNumber}</span>
                </div>
                {supplierName && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Building2 className="h-4 w-4" />
                    <span className="font-medium">Vendor:</span>
                    <span>{supplierName}</span>
                  </div>
                )}
              </div>

              {/* Material Info (Read-only) */}
              <div className="space-y-2">
                <Label className="text-base font-semibold">Material</Label>
                <div className="rounded-lg border bg-muted/50 p-3">
                  {loadingMaterial ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading material details...
                    </div>
                  ) : material ? (
                    <>
                      <div className="font-mono font-medium text-base">
                        {material.code}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {material.name}
                      </div>
                    </>
                  ) : (
                    <div className="font-mono text-sm text-muted-foreground">
                      {line.material_id.slice(0, 8)}...
                    </div>
                  )}
                </div>
              </div>

              {/* BOM Requirement Info */}
              <div className="rounded-lg border p-3 space-y-1 text-sm">
                <div className="font-medium text-muted-foreground mb-2">
                  BOM Requirement
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <div className="text-xs text-muted-foreground">Required</div>
                    <div className="font-semibold">{line.required_quantity}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">
                      Already Issued
                    </div>
                    <div className="font-semibold">{line.issued_quantity}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Remaining</div>
                    <div className="font-semibold text-blue-600">{remaining}</div>
                  </div>
                </div>
              </div>

              {/* Quantity Input */}
              <div className="space-y-2">
                <Label htmlFor="issue-quantity">
                  Quantity to Issue <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="issue-quantity"
                  type="number"
                  min={0.001}
                  step={0.001}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  disabled={busy}
                  placeholder="Enter quantity"
                />
                {Number(quantity) > remaining && (
                  <p className="text-xs text-amber-600">
                    ⚠️ Quantity exceeds remaining requirement ({remaining})
                  </p>
                )}
              </div>

              {/* Warehouse Selector */}
              <div className="space-y-2">
                <Label htmlFor="issue-warehouse">
                  From Location <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={warehouseId}
                  onValueChange={setWarehouseId}
                  disabled={busy}
                >
                  <SelectTrigger id="issue-warehouse">
                    <SelectValue placeholder="Select location" />
                  </SelectTrigger>
                  <SelectContent>
                    {warehouses.map((wh) => {
                      const locType = (wh as { type?: string }).type ?? (wh as { location_type?: string }).location_type ?? 'unknown'
                      return (
                        <SelectItem key={wh.id} value={wh.id}>
                          {wh.name} {locType !== 'warehouse' && locType !== 'unknown' && <span className="text-xs text-muted-foreground">({locType})</span>}
                        </SelectItem>
                      )
                    })}
                  </SelectContent>
                </Select>
              </div>

              {/* Batch/Lot Input */}
              <div className="space-y-2">
                <Label htmlFor="issue-batch">
                  Batch / Lot{" "}
                  <span className="text-xs text-muted-foreground font-normal">
                    (optional — for traceability)
                  </span>
                </Label>
                <Input
                  id="issue-batch"
                  value={batchId}
                  onChange={(e) => setBatchId(e.target.value)}
                  disabled={busy}
                  placeholder="Leave blank if not batch-tracked"
                />
                <p className="text-xs text-muted-foreground">
                  ℹ️ Enter batch ID only if this material requires batch tracking
                </p>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0 flex-shrink-0 border-t pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                disabled={busy}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleConfirmClick}
                disabled={!isValid || busy}
              >
                Continue
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            {/* Confirmation View */}
            <DialogHeader>
              <DialogTitle>Confirm Material Issue</DialogTitle>
              <DialogDescription>
                Review the details before issuing material
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3 py-4 overflow-y-auto flex-1">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-2 border-b">
                  <span className="text-muted-foreground">Material</span>
                  <span className="font-medium">
                    {material ? (
                      <span>
                        {material.code} — {material.name}
                      </span>
                    ) : (
                      <span className="font-mono">
                        {line.material_id.slice(0, 8)}...
                      </span>
                    )}
                  </span>
                </div>

                <div className="flex justify-between py-2 border-b">
                  <span className="text-muted-foreground">Quantity</span>
                  <span className="font-semibold text-blue-600">{quantity}</span>
                </div>

                <div className="flex justify-between py-2 border-b">
                  <span className="text-muted-foreground">From Location</span>
                  <span className="font-medium">
                    {selectedWarehouse?.name || warehouseId}
                  </span>
                </div>

                {batchId && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-muted-foreground">Batch</span>
                    <span className="font-mono text-sm">{batchId}</span>
                  </div>
                )}

                <div className="flex justify-between py-2 pt-3">
                  <span className="text-muted-foreground">
                    Remaining after issue
                  </span>
                  <span className="font-semibold">
                    {Math.max(0, remaining - Number(quantity))}
                  </span>
                </div>
              </div>

              <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm">
                <p className="text-blue-900">
                  This will transfer stock from{" "}
                  <span className="font-medium">{selectedWarehouse?.name}</span>{" "}
                  to the subcontractor and update the inventory transaction log.
                </p>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0 flex-shrink-0 border-t pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                disabled={busy}
              >
                Back
              </Button>
              <Button type="button" onClick={handleFinalIssue} disabled={busy}>
                {busy ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Issuing...
                  </>
                ) : (
                  "Confirm Issue"
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
