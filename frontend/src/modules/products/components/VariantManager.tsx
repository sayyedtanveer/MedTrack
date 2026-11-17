import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "react-router-dom"
import { Box, Plus, Loader2, Pencil, Check, X, Link2, Link2Off, GitBranch } from "lucide-react"
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
  startAdding?: boolean
  onCreateFormClose?: () => void
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
          <Label className="text-xs font-medium">
            Finished Good Inventory Item
          </Label>
          <Select value={materialId} onValueChange={setMaterialId}>
            <SelectTrigger className={materialId === NO_MATERIAL ? "border-amber-400" : ""}>
              <SelectValue placeholder="Select finished goods material..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NO_MATERIAL}>— No material linked —</SelectItem>
              {/* Finished Goods Section */}
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
              {/* Semi-Finished Section */}
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return t.includes("semi") || t === "sf"
              }).length > 0 && (
                <div className="px-2 py-1 text-[10px] text-muted-foreground font-semibold uppercase tracking-wide border-t mt-1 pt-1">
                  Semi-Finished
                </div>
              )}
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return t.includes("semi") || t === "sf"
              }).map(m => (
                <SelectItem key={m.id} value={m.id}>
                  {m.code} — {m.name}{" "}
                  <span className="text-xs text-purple-600">🟣 SF</span>
                </SelectItem>
              ))}
              {/* Other Materials Section */}
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return !t.includes("finish") && t !== "fg" && !t.includes("semi") && t !== "sf"
              }).length > 0 && (
                <div className="px-2 py-1 text-[10px] text-muted-foreground font-semibold uppercase tracking-wide border-t mt-1 pt-1">
                  Other Materials
                </div>
              )}
              {fgMaterials.filter(m => {
                const t = String(m.material_type || "").toLowerCase()
                return !t.includes("finish") && t !== "fg" && !t.includes("semi") && t !== "sf"
              }).map(m => (
                <SelectItem key={m.id} value={m.id}>
                  {m.code} — {m.name}{" "}
                  <span className="text-xs text-muted-foreground">({m.material_type})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {materialId === NO_MATERIAL && (
            <p className="text-xs text-amber-600 mt-1">
              Inventory item not linked. This variant cannot participate in stock reservation/fulfillment until a finished-good inventory item is linked.
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

export function VariantManager({ template, canEdit, startAdding = false, onCreateFormClose }: VariantManagerProps) {
  const qc = useQueryClient()
  const navigate = useNavigate()

  // Create form state
  const [isAdding, setIsAdding] = useState(startAdding)
  const [newValues, setNewValues] = useState<Record<string, string>>({})
  const [standardCost, setStandardCost] = useState("0")
  const [sellingPrice, setSellingPrice] = useState("")
  const [materialId, setMaterialId] = useState(NO_MATERIAL)
  const defaultOutputType = template.code.startsWith("SFG-") ? "semi_finished" : "finished"
  const [outputType, setOutputType] = useState<"finished" | "semi_finished">(defaultOutputType)
  const isSemiFinished = outputType === "semi_finished"

  // Edit state — tracks which variant is being edited
  const [editingId, setEditingId] = useState<string | null>(null)

  // Load ALL materials for the link dropdown (not just 'finished' type)
  // This handles legacy data where material_type may be stored as 'finished_goods', 'FG', etc.
  const { data: fgMaterials } = useQuery({
    queryKey: ["materials", "all-for-variant-link"],
    queryFn: () => materialService.getMaterials({ page: 1, page_size: 500 }),
    staleTime: 30_000,
  })

  const semiFinishedQuery = useQuery({
    queryKey: ["materials", "active-semi-finished-for-variant-link"],
    queryFn: () => materialService.getMaterials({
      material_type: "semi_finished",
      is_active: true,
      page: 1,
      page_size: 500,
    }),
    enabled: canEdit && isAdding && isSemiFinished,
    staleTime: 30_000,
    refetchOnWindowFocus: "always",
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
      setOutputType(defaultOutputType)
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
    if (isSemiFinished && !selectedMaterial) {
      toast.error("Select an active semi-finished inventory material")
      return
    }
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
    addMutation.mutate(payload, { onSuccess: onCreateFormClose })
  }

  // Fix 5: also reset materialId on cancel
  const handleCancelCreate = () => {
    setIsAdding(false)
    setNewValues({})
    setStandardCost("0")
    setSellingPrice("")
    setMaterialId(NO_MATERIAL)
    setOutputType(defaultOutputType)
    onCreateFormClose?.()
  }

  const handleSaveEdit = (id: string, payload: UpdateVariantInput) => {
    editMutation.mutate({ id, payload })
  }

  const setVal = (k: string, v: string) => setNewValues(prev => ({ ...prev, [k]: v }))

  const fgList = fgMaterials?.items ?? []
  const linkOptions = isSemiFinished
    ? (semiFinishedQuery.data?.items ?? []).filter(material =>
        material.material_type === "semi_finished" && material.is_active,
      )
    : fgList.filter(material => {
        const type = String(material.material_type || "").toLowerCase()
        return (type.includes("finish") && !type.includes("semi")) || type === "fg"
      })
  const selectedMaterial = linkOptions.find(material => material.id === materialId)

  return (
    <div className="space-y-4">
      {/* Header */}
      {!onCreateFormClose && <div className="flex justify-between items-center mb-4 border-b pb-2">
        <h2 className="text-base font-medium flex items-center gap-2">
          <Box className="w-4 h-4" /> Variants ({variants?.total || 0})
        </h2>
        {!isAdding && canEdit && (
          <Button variant="outline" size="sm" onClick={() => setIsAdding(true)}>
            <Plus className="w-4 h-4 mr-1" /> Add Variant
          </Button>
        )}
      </div>}

      {/* Create Variant Form */}
      {isAdding && canEdit && (
        <div className="rounded-lg border bg-muted/20 p-4 space-y-4 mb-4">
          <h4 className="text-sm font-medium">Create New Variant</h4>
          {template.attributes.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              This product has no options such as size or color. Save it as a standard variant.
            </p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {template.attributes.map(attr => (
                <div key={attr.key} className="space-y-1.5">
                  <Label className="text-xs">
                    {attr.label}
                  </Label>
                  {attr.values && attr.values.length > 0 ? (
                    <Select
                      value={newValues[attr.key] || ""}
                      onValueChange={value => setVal(attr.key, value)}
                    >
                      <SelectTrigger aria-label={attr.label}>
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
                      aria-label={attr.label}
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
              <Label htmlFor="new-variant-cost" className="text-xs">Standard cost (required)</Label>
              <Input
                id="new-variant-cost"
                type="number"
                min="0"
                step="0.01"
                value={standardCost}
                onChange={e => setStandardCost(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-variant-price" className="text-xs">Selling price (optional)</Label>
              <Input
                id="new-variant-price"
                type="number"
                min="0"
                step="0.01"
                value={sellingPrice}
                onChange={e => setSellingPrice(e.target.value)}
              />
            </div>
          </div>

          <fieldset className="space-y-3 rounded-lg border bg-background px-3 pb-3">
            <legend className="px-1 text-sm font-medium">Inventory item for this variant</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {([
                { value: "finished", label: "Finished good" },
                { value: "semi_finished", label: "Semi-finished (subcontracting)" },
              ] as const).map(option => (
                <Button
                  key={option.value}
                  type="button"
                  variant={outputType === option.value ? "secondary" : "outline"}
                  aria-pressed={outputType === option.value}
                  className="h-auto min-h-9 whitespace-normal text-left"
                  disabled={addMutation.isPending}
                  onClick={() => {
                    if (outputType === option.value) return
                    setOutputType(option.value)
                    setMaterialId(NO_MATERIAL)
                  }}
                >
                  {option.label}
                </Button>
              ))}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="variant-inventory-material" className="text-xs font-medium">
                {isSemiFinished ? "Semi-finished item (required)" : "Finished good inventory material"}
              </Label>
              <Select
                value={materialId === NO_MATERIAL && isSemiFinished ? "" : materialId}
                onValueChange={setMaterialId}
                disabled={addMutation.isPending || (isSemiFinished && linkOptions.length === 0)}
              >
                <SelectTrigger id="variant-inventory-material" aria-describedby="variant-inventory-help">
                  <SelectValue placeholder="Select a semi-finished item" />
                </SelectTrigger>
                <SelectContent>
                  {!isSemiFinished && <SelectItem value={NO_MATERIAL}>Auto-create a finished good</SelectItem>}
                  {linkOptions.map(material => (
                    <SelectItem key={material.id} value={material.id}>
                      {material.code} — {material.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div id="variant-inventory-help" className="space-y-1.5 text-xs leading-relaxed text-muted-foreground">
                {isSemiFinished ? (
                  <>
                    {semiFinishedQuery.isPending ? (
                      <p role="status">Loading semi-finished materials…</p>
                    ) : semiFinishedQuery.isError ? (
                      <p role="alert">
                        Could not load semi-finished materials.{" "}
                        <button type="button" className="font-medium text-primary underline" onClick={() => void semiFinishedQuery.refetch()}>Retry</button>
                      </p>
                    ) : linkOptions.length === 0 ? (
                      <p>No active semi-finished materials found.</p>
                    ) : null}
                    <p>
                      Select the item you’ll receive after the supplier finishes the work. For example, if you send wooden boards to be cut into chair seats, select Wooden chair seat.
                    </p>
                    <p>Use the same stock unit for both the item and this variant, such as pieces.</p>
                    <p>
                      Item missing?{" "}
                      <Link to="/inventory/materials" target="_blank" rel="noopener noreferrer" className="font-medium text-primary underline">
                        Add a semi-finished item in Materials (opens in a new tab)
                      </Link>
                      . Then return here and select it.
                    </p>
                    {!template.is_active && (
                      <p>Activate this product template before using the variant on a subcontract order.</p>
                    )}
                  </>
                ) : (
                  <p>{materialId === NO_MATERIAL ? "Saving will create and link a finished good in Inventory." : "Saving will link the selected finished good."}</p>
                )}
              </div>
            </div>
          </fieldset>

          {/* Real-time Variant Summary */}
          <div className="bg-primary/5 rounded-lg p-3 border border-primary/20 text-sm mt-4">
            <h5 className="font-semibold mb-2">Review before saving</h5>
            <div className="grid grid-cols-[1fr_2fr] sm:grid-cols-[150px_1fr] gap-y-1 gap-x-4">
              <div className="text-muted-foreground">Product:</div>
              <div className="font-medium">{template.name}</div>
              
              <div className="text-muted-foreground">Variant:</div>
              <div className="font-medium">
                {Object.keys(newValues).length > 0 
                  ? Object.entries(newValues).filter(([_, v]) => v.trim()).map(([k, v]) => `${template.attributes.find(a => a.key === k)?.label || k}: ${v}`).join(', ')
                  : "Standard"}
              </div>

              <div className="text-muted-foreground">Variant code (SKU):</div>
              <div>Assigned automatically when you save</div>

              <div className="text-muted-foreground">Standard Cost:</div>
              <div className="font-medium">{formatCurrency(parseFloat(standardCost) || 0)}</div>

              <div className="text-muted-foreground">Selling Price:</div>
              <div className="font-medium">{sellingPrice ? formatCurrency(parseFloat(sellingPrice)) : "-"}</div>

              <div className="text-muted-foreground">Inventory Item:</div>
              <div className="font-medium">
                {selectedMaterial
                  ? `${selectedMaterial.name} (${selectedMaterial.code})`
                  : isSemiFinished ? "Choose a semi-finished item above" : "A finished good will be created on save"}
              </div>
              
            </div>
          </div>

          <div className="flex gap-2 justify-end pt-2">
            <Button variant="ghost" size="sm" onClick={handleCancelCreate} disabled={addMutation.isPending}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleCreate} disabled={addMutation.isPending || (isSemiFinished && !selectedMaterial)}>
              {addMutation.isPending && <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />}
              Create
            </Button>
          </div>
        </div>
      )}

      {/* Variants List */}
      {!onCreateFormClose && (isLoading ? (
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
                        Tracking: {fgList.find(m => m.id === v.material_id)?.code ?? "Linked"}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
                        <Link2Off className="w-2.5 h-2.5" />
                        Unlinked — Cannot be used in sales
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
                  <div className="flex items-center gap-1 mt-1">
                    {canEdit && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2"
                        onClick={() => setEditingId(v.id)}
                        disabled={editingId !== null && editingId !== v.id}
                      >
                        <Pencil className="w-3.5 h-3.5 mr-1" /> Edit
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => navigate(`/bom/new?variant_id=${v.id}`)}
                    >
                      <GitBranch className="w-3.5 h-3.5 mr-1" /> BOM
                    </Button>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      ))}
    </div>
  )
}
