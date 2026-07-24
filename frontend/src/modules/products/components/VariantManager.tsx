import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Box, Plus, Loader2, Pencil, Check, X, Link2, Link2Off } from "lucide-react"
import { productService, CreateVariantInput, UpdateVariantInput } from "@/services/product.service"
import { materialService } from "@/services/material.service"
import { ItemTemplate, ItemVariant } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { formatCurrency } from "@/utils/currency"

const NO_MATERIAL = "__none__"

interface VariantManagerProps {
  template: ItemTemplate
  canEdit: boolean
}

// ── Inline Edit Form ──────────────────────────────────────────────────────────

interface EditRowProps {
  variant: ItemVariant
  fgMaterials: { id: string; code: string; name: string; material_type?: string }[]
  onSave: (id: string, payload: UpdateVariantInput) => void
  onCancel: () => void
  isSaving: boolean
}

function EditRow({ variant, fgMaterials, onSave, onCancel, isSaving }: EditRowProps) {
  const [standardCost, setStandardCost] = useState(String(variant.standard_cost))
  const [sellingPrice, setSellingPrice] = useState(variant.selling_price != null ? String(variant.selling_price) : "")
  const [materialId, setMaterialId] = useState(variant.material_id ?? NO_MATERIAL)
  const [isActive, setIsActive] = useState(variant.is_active)

  const handleSave = () => {
    const cost = parseFloat(standardCost)
    if (isNaN(cost) || cost < 0) {
      toast.error("Standard cost must be >= 0")
      return
    }
    onSave(variant.id, {
      standard_cost: cost,
      selling_price: sellingPrice ? parseFloat(sellingPrice) : undefined,
      material_id: materialId !== NO_MATERIAL ? materialId : null,
      is_active: isActive,
    })
  }

  return (
    <div className="rounded-lg border border-primary/40 bg-muted/20 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{variant.name}</span>
        <span className="text-xs text-muted-foreground font-mono">{variant.code}</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs">Standard Cost</Label>
          <Input
            type="number"
            min="0"
            step="0.01"
            value={standardCost}
            onChange={e => setStandardCost(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Selling Price</Label>
          <Input
            type="number"
            min="0"
            step="0.01"
            value={sellingPrice}
            onChange={e => setSellingPrice(e.target.value)}
          />
        </div>
        <div className="col-span-2 space-y-1.5">
          <Label className="text-xs font-medium text-amber-700">
            Link to Inventory Material (Required for Sales Orders & Work Orders)
          </Label>
          <Select value={materialId} onValueChange={setMaterialId}>
            <SelectTrigger className={materialId === NO_MATERIAL ? "border-amber-400" : ""}>
              <SelectValue placeholder="Select finished goods material..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NO_MATERIAL}>— No material linked —</SelectItem>
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return t.includes("finish") || t === "fg"
              }).length > 0 && (
                <div className="px-2 py-1 text-[10px] text-muted-foreground font-semibold uppercase tracking-wide">
                  Finished Goods
                </div>
              )}
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return t.includes("finish") || t === "fg"
              }).map(m => (
                <SelectItem key={m.id} value={m.id}>
                  {m.code} — {m.name}
                </SelectItem>
              ))}
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return !t.includes("finish") && t !== "fg"
              }).length > 0 && (
                <div className="px-2 py-1 text-[10px] text-muted-foreground font-semibold uppercase tracking-wide border-t mt-1 pt-1">
                  Other Materials
                </div>
              )}
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return !t.includes("finish") && t !== "fg"
              }).map(m => (
                <SelectItem key={m.id} value={m.id}>
                  {m.code} — {m.name}{" "}
                  <span className="text-xs text-muted-foreground">({m.material_type})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {materialId === NO_MATERIAL && (
            <p className="text-xs text-amber-600">
              ⚠ Without a linked material, this variant cannot be used in sales orders or production.
            </p>
          )}
        </div>
        <div className="col-span-2 flex items-center gap-2">
          <Label className="text-xs">Active</Label>
          <button
            type="button"
            onClick={() => setIsActive(v => !v)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              isActive ? "bg-primary" : "bg-muted-foreground/30"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                isActive ? "translate-x-4" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>
      </div>

      <div className="flex gap-2 justify-end pt-1">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={isSaving}>
          <X className="w-3.5 h-3.5 mr-1" /> Cancel
        </Button>
        <Button size="sm" onClick={handleSave} disabled={isSaving}>
          {isSaving ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Check className="w-3.5 h-3.5 mr-1" />}
          Save
        </Button>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function VariantManager({ template, canEdit }: VariantManagerProps) {
  const qc = useQueryClient()

  // Create form state
  const [isAdding, setIsAdding] = useState(false)
  const [newValues, setNewValues] = useState<Record<string, string>>({})
  const [standardCost, setStandardCost] = useState("0")
  const [sellingPrice, setSellingPrice] = useState("")
  const [materialId, setMaterialId] = useState(NO_MATERIAL)

  // Edit state — tracks which variant is being edited
  const [editingId, setEditingId] = useState<string | null>(null)

  // Load ALL materials for the link dropdown (not just 'finished' type)
  // This handles legacy data where material_type may be stored as 'finished_goods', 'FG', etc.
  const { data: fgMaterials } = useQuery({
    queryKey: ["materials", "all-for-variant-link"],
    queryFn: () => materialService.getMaterials({ page: 1, page_size: 500 }),
    staleTime: 30_000,
  })

  const { data: variants, isLoading } = useQuery({
    queryKey: ["products", "template", template.id, "variants"],
    queryFn: () => productService.getVariants(template.id, { page_size: 100 }),
    staleTime: 10_000,
  })

  const addMutation = useMutation({
    mutationFn: (payload: CreateVariantInput) => productService.createVariant(template.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products", "template", template.id, "variants"] })
      toast.success("Variant created successfully")
      // Fix 5: reset ALL create-form state including materialId
      setIsAdding(false)
      setNewValues({})
      setStandardCost("0")
      setSellingPrice("")
      setMaterialId(NO_MATERIAL)
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to create variant")
    },
  })

  const editMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateVariantInput }) =>
      productService.updateVariant(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products", "template", template.id, "variants"] })
      toast.success("Variant updated")
      setEditingId(null)
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to update variant")
    },
  })

  const handleCreate = () => {
    for (const attr of template.attributes) {
      if (!newValues[attr.key]?.trim()) {
        toast.error(`Value for ${attr.label} is required`)
        return
      }
    }
    const cost = parseFloat(standardCost)
    if (isNaN(cost) || cost < 0) {
      toast.error("Standard cost must be >= 0")
      return
    }
    const payload: CreateVariantInput = {
      attribute_values: newValues,
      standard_cost: cost,
      selling_price: sellingPrice ? parseFloat(sellingPrice) : undefined,
      material_id: materialId !== NO_MATERIAL ? materialId : undefined,
    }
    addMutation.mutate(payload)
  }

  // Fix 5: also reset materialId on cancel
  const handleCancelCreate = () => {
    setIsAdding(false)
    setNewValues({})
    setStandardCost("0")
    setSellingPrice("")
    setMaterialId(NO_MATERIAL)
  }

  const handleSaveEdit = (id: string, payload: UpdateVariantInput) => {
    editMutation.mutate({ id, payload })
  }

  const setVal = (k: string, v: string) => setNewValues(prev => ({ ...prev, [k]: v }))

  const fgList = fgMaterials?.items ?? []

  // Separate into finished and other for display ordering
  const finishedMaterials = fgList.filter(m => {
    const t = String(m.material_type || "").toLowerCase()
    return t.includes("finish") || t === "fg"
  })
  const otherMaterials = fgList.filter(m => {
    const t = String(m.material_type || "").toLowerCase()
    return !t.includes("finish") && t !== "fg"
  })

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4 border-b pb-2">
        <h2 className="text-base font-medium flex items-center gap-2">
          <Box className="w-4 h-4" /> Variants ({variants?.total || 0})
        </h2>
        {!isAdding && canEdit && (
          <Button variant="outline" size="sm" onClick={() => setIsAdding(true)}>
            <Plus className="w-4 h-4 mr-1" /> Add Variant
          </Button>
        )}
      </div>

      {/* Create Variant Form */}
      {isAdding && canEdit && (
        <div className="rounded-lg border bg-muted/20 p-4 space-y-4 mb-4">
          <h4 className="text-sm font-medium">Create New Variant</h4>
          {template.attributes.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              This template has no dynamic attributes. The variant will act as a standard standalone SKU.
            </p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {template.attributes.map(attr => (
                <div key={attr.key} className="space-y-1.5">
                  <Label className="text-xs">
                    {attr.label} ({attr.key})
                  </Label>
                  {attr.values && attr.values.length > 0 ? (
                    <Select
                      value={newValues[attr.key] || ""}
                      onValueChange={value => setVal(attr.key, value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select value..." />
                      </SelectTrigger>
                      <SelectContent>
                        {attr.values.map(value => (
                          <SelectItem key={value} value={value}>
                            {value}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      placeholder="e.g. XL, Blue"
                      value={newValues[attr.key] || ""}
                      onChange={e => setVal(attr.key, e.target.value)}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="space-y-1.5">
              <Label className="text-xs">Standard Cost (Required)</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={standardCost}
                onChange={e => setStandardCost(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Selling Price (Optional)</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={sellingPrice}
                onChange={e => setSellingPrice(e.target.value)}
              />
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs font-medium text-amber-700">
                Link to Inventory Material (Required for Sales Orders & Work Orders)
              </Label>
              <p className="text-xs text-muted-foreground">
                Select the finished-goods material that tracks stock for this variant. Without this link,
                sales order confirmation will fail.
              </p>
              <Select value={materialId} onValueChange={setMaterialId}>
                <SelectTrigger className={materialId === NO_MATERIAL ? "border-amber-400" : ""}>
                  <SelectValue placeholder="Select finished goods material..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_MATERIAL}>— No material linked —</SelectItem>
                  {finishedMaterials.length > 0 && (
                    <div className="px-2 py-1 text-[10px] text-muted-foreground font-semibold uppercase tracking-wide">
                      Finished Goods
                    </div>
                  )}
                  {finishedMaterials.map(m => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.code} — {m.name}
                    </SelectItem>
                  ))}
                  {otherMaterials.length > 0 && (
                    <div className="px-2 py-1 text-[10px] text-muted-foreground font-semibold uppercase tracking-wide border-t mt-1 pt-1">
                      Other Materials
                    </div>
                  )}
                  {otherMaterials.map(m => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.code} — {m.name}{" "}
                      <span className="text-xs text-muted-foreground">({m.material_type})</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {materialId === NO_MATERIAL && (
                <p className="text-xs text-amber-600">
                  ⚠ You must link a finished-goods material to use this variant in sales and production.
                </p>
              )}
            </div>
          </div>

          <div className="flex gap-2 justify-end pt-2">
            <Button variant="ghost" size="sm" onClick={handleCancelCreate}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleCreate} disabled={addMutation.isPending}>
              {addMutation.isPending && <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />}
              Create
            </Button>
          </div>
        </div>
      )}

      {/* Variants List */}
      {isLoading ? (
        <div className="text-center py-6 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mx-auto" />
        </div>
      ) : variants?.items.length === 0 && !isAdding ? (
        <div className="text-center py-8 text-sm text-muted-foreground border border-dashed rounded-lg bg-accent/20">
          No variants created yet.
        </div>
      ) : (
        <div className="grid gap-3">
          {variants?.items.map(v =>
            editingId === v.id ? (
              // Fix 3: inline edit row
              <EditRow
                key={v.id}
                variant={v}
                fgMaterials={fgList}
                onSave={handleSaveEdit}
                onCancel={() => setEditingId(null)}
                isSaving={editMutation.isPending && editMutation.variables?.id === v.id}
              />
            ) : (
              <div
                key={v.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 border rounded-lg bg-card hover:border-primary/50 transition-colors"
              >
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="font-medium text-sm truncate">{v.name}</span>
                  <span className="text-xs text-muted-foreground font-mono truncate">{v.code}</span>
                  {Object.keys(v.attribute_values).length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {Object.entries(v.attribute_values).map(([k, val]) => (
                        <Badge
                          key={k}
                          variant="secondary"
                          className="text-[10px] px-1.5 py-0 font-normal"
                        >
                          {template.attributes.find(a => a.key === k)?.label || k}: {String(val)}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {/* Fix 4: material link status badge */}
                  <div className="mt-1.5">
                    {v.material_id ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-green-700 bg-green-50 border border-green-200 rounded px-1.5 py-0.5">
                        <Link2 className="w-2.5 h-2.5" />
                        {fgList.find(m => m.id === v.material_id)?.code ?? "Material linked"}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
                        <Link2Off className="w-2.5 h-2.5" />
                        No material linked — cannot use in sales orders
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap sm:flex-col gap-x-4 gap-y-1 sm:text-right shrink-0 items-start sm:items-end text-sm">
                  <span className="text-green-700 font-medium">
                    Cost: {formatCurrency(Number(v.standard_cost))}
                  </span>
                  {v.selling_price != null && (
                    <span className="text-muted-foreground">
                      Price: {formatCurrency(Number(v.selling_price))}
                    </span>
                  )}
                  <Badge variant={v.is_active ? "outline" : "secondary"} className="mt-1">
                    {v.is_active ? "Active" : "Inactive"}
                  </Badge>
                  {canEdit && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-1 h-7 px-2"
                      onClick={() => setEditingId(v.id)}
                      disabled={editingId !== null && editingId !== v.id}
                    >
                      <Pencil className="w-3.5 h-3.5 mr-1" /> Edit
                    </Button>
                  )}
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}
