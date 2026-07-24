import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { materialService } from "@/services/material.service"
import { tenantService } from "@/services/tenant.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { Save, TrendingUp, TrendingDown, Minus, Package, Calendar, User, ShoppingCart } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Drawer } from "@/components/shared/Drawer"
import { useEffect, useState } from "react"
import { supplyChainApi } from "@/services/supply-chain.service"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PurchaseHistoryItem } from "@/types/material.types"

const GENERIC_RAW_NAMES = new Set([
  "raw material",
  "raw materials",
  "material",
  "materials",
  "component",
  "components",
  "item",
  "items",
])

const GENERIC_FINISHED_NAMES = new Set([
  "finished good",
  "finished goods",
  "product",
  "products",
  "final product",
  "finished item",
  "goods",
  "item",
  "items",
])

const normalizeMaterialName = (value: string) =>
  value.trim().replace(/\s+/g, " ").toLowerCase()

const materialSchema = z.object({
  // legacy backend may still accept `code`; Phase 2 prefers `item_code`
  item_code: z.string().trim().max(50).optional(),
  // legacy (backward compat)
  code: z.string().trim().max(50).optional(),

  name: z.string().trim().min(1, "Name is required").max(255),
  material_type: z.enum(["raw", "finished", "semi_finished"]),
  base_unit_id: z.string().uuid("Please select a valid unit").nullable().optional(),
  description: z.string().max(2000).optional().nullable(),
  category_id: z.string().uuid("Please select a valid category"),
  reorder_level: z.coerce.number().min(0).optional().nullable(),
  location_id: z.string().uuid("Please select a valid location").nullable().optional(),

  is_batch_tracked: z.boolean().default(false).optional(),
  is_serialized: z.boolean().default(false).optional(),

  inspection_required: z.boolean().optional(),
  inspection_template_id: z.string().uuid().nullable().optional(),

  // Phase 2: lock after creation (default true)
  code_locked: z.boolean().default(true).optional(),

  // Opening stock (only used in create mode)
  opening_stock: z.coerce.number().min(0, "Opening stock must be 0 or greater").optional().nullable(),

  current_cost: z.coerce
    .number()
    .min(0, "Standard Purchase Cost must be 0 or greater")
    .max(999999999.9999, "Value exceeds maximum allowed")
    .optional()
    .nullable(),
}).superRefine(({ name, material_type }, ctx) => {
  const normalized = normalizeMaterialName(name)
  if (material_type === "raw" && GENERIC_RAW_NAMES.has(normalized)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["name"],
      message: "Use the actual raw material name, for example Brass Body, Glass Tube, or O-Ring Seal.",
    })
  }
  if ((material_type === "finished" || material_type === "semi_finished") && GENERIC_FINISHED_NAMES.has(normalized)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["name"],
      message: "Use the actual finished good name, for example Gear Rotameter - Standard.",
    })
  }
})

type MaterialFormValues = z.infer<typeof materialSchema>

interface Props {
  materialId: string | null
  open: boolean
  onClose: () => void
}

// ── Purchasing Summary Card ────────────────────────────────────────────────────

function PurchasingSummaryCard({
  material,
  currencyCode,
}: {
  material: any
  currencyCode: string
}) {
  const standardCost = Number(material?.current_cost ?? 0)
  const latestPrice = material?.latest_purchase_price != null ? Number(material.latest_purchase_price) : null
  const lastDate = material?.last_purchase_date ?? null
  const lastSupplier = material?.last_supplier_name ?? null
  const purchaseCount = material?.purchase_count ?? 0

  let diffAmount: number | null = null
  let diffPct: number | null = null
  let diffDirection: "up" | "down" | "same" | null = null

  if (latestPrice !== null && standardCost > 0) {
    diffAmount = latestPrice - standardCost
    diffPct = (diffAmount / standardCost) * 100
    diffDirection = diffAmount > 0 ? "up" : diffAmount < 0 ? "down" : "same"
  }

  const fmt = (n: number) =>
    n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 4 })

  return (
    <div className="space-y-4">
      {/* Latest vs Standard comparison */}
      <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Standard Cost</span>
          <span className="text-sm font-semibold tabular-nums">
            {currencyCode} {fmt(standardCost)}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Latest Purchase Price</span>
          {latestPrice !== null ? (
            <span className="text-sm font-semibold tabular-nums">
              {currencyCode} {fmt(latestPrice)}
            </span>
          ) : (
            <span className="text-sm text-muted-foreground">No receipts yet</span>
          )}
        </div>

        {diffAmount !== null && diffDirection !== null && (
          <div className="flex items-center justify-between border-t pt-3">
            <span className="text-sm text-muted-foreground">Difference</span>
            <div className="flex items-center gap-1.5">
              {diffDirection === "up" && <TrendingUp className="h-4 w-4 text-red-500" />}
              {diffDirection === "down" && <TrendingDown className="h-4 w-4 text-green-500" />}
              {diffDirection === "same" && <Minus className="h-4 w-4 text-muted-foreground" />}
              <span
                className={`text-sm font-semibold tabular-nums ${
                  diffDirection === "up"
                    ? "text-red-600"
                    : diffDirection === "down"
                    ? "text-green-600"
                    : "text-muted-foreground"
                }`}
              >
                {diffAmount! >= 0 ? "+" : ""}
                {currencyCode} {fmt(Math.abs(diffAmount!))}
                {diffPct !== null && (
                  <span className="ml-1 text-xs font-normal">
                    ({diffPct >= 0 ? "+" : ""}{diffPct.toFixed(2)}%)
                  </span>
                )}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Meta info row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-md border p-3 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Calendar className="h-3.5 w-3.5" />
            <span className="text-xs">Last Purchased</span>
          </div>
          <span className="text-sm font-medium">
            {lastDate
              ? new Date(lastDate).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
              : "—"}
          </span>
        </div>

        <div className="rounded-md border p-3 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <User className="h-3.5 w-3.5" />
            <span className="text-xs">Last Supplier</span>
          </div>
          <span className="text-sm font-medium truncate" title={lastSupplier ?? ""}>
            {lastSupplier ?? "—"}
          </span>
        </div>

        <div className="rounded-md border p-3 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Package className="h-3.5 w-3.5" />
            <span className="text-xs">Purchase Count</span>
          </div>
          <span className="text-sm font-medium">{purchaseCount} Receipts</span>
        </div>
      </div>
    </div>
  )
}

// ── Purchase History Table ─────────────────────────────────────────────────────

function PurchaseHistoryTable({ materialId }: { materialId: string }) {
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 25

  const { data, isLoading } = useQuery({
    queryKey: ["purchase-history", materialId, page],
    queryFn: () => materialService.getPurchaseHistory(materialId, page, PAGE_SIZE),
    enabled: Boolean(materialId),
  })

  if (isLoading) {
    return (
      <div className="space-y-2 py-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-9 bg-muted/50 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
        <ShoppingCart className="h-10 w-10 mb-3 opacity-30" />
        <p className="text-sm font-medium">No purchase history</p>
        <p className="text-xs mt-1">Completed GRN receipts will appear here.</p>
      </div>
    )
  }

  const totalPages = Math.ceil(data.total / PAGE_SIZE)

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        {data.total} receipt{data.total !== 1 ? "s" : ""} · newest first
      </p>
      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-xs text-muted-foreground">
              <th className="px-3 py-2 text-left font-medium">Date</th>
              <th className="px-3 py-2 text-left font-medium">Supplier</th>
              <th className="px-3 py-2 text-left font-medium">PO</th>
              <th className="px-3 py-2 text-left font-medium">GRN</th>
              <th className="px-3 py-2 text-right font-medium">Qty</th>
              <th className="px-3 py-2 text-left font-medium">UOM</th>
              <th className="px-3 py-2 text-right font-medium">Unit Price</th>
              <th className="px-3 py-2 text-right font-medium">Total Value</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {data.items.map((item: PurchaseHistoryItem, idx: number) => (
              <tr key={idx} className="hover:bg-muted/20 transition-colors">
                <td className="px-3 py-2 text-xs tabular-nums whitespace-nowrap">
                  {item.date
                    ? new Date(item.date).toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })
                    : "—"}
                </td>
                <td className="px-3 py-2 max-w-[120px] truncate" title={item.supplier_name}>
                  {item.supplier_name}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{item.po_number}</td>
                <td className="px-3 py-2 font-mono text-xs">{item.grn_number}</td>
                <td className="px-3 py-2 text-right tabular-nums">{item.quantity.toLocaleString()}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{item.uom}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {item.currency} {item.unit_price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                </td>
                <td className="px-3 py-2 text-right tabular-nums font-medium">
                  {item.currency} {item.total_value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function MaterialFormDrawer({ materialId, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(materialId && materialId !== "new")

  const { data: material, isLoading: isFetchingMaterial } = useQuery({
    queryKey: ["material", materialId],
    queryFn: () => materialService.getMaterial(materialId!),
    enabled: isEditing && open,
  })

  const { data: categories, isLoading: isFetchingCategories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => materialService.getCategories(),
  })

  const { data: units, isLoading: isFetchingUnits } = useQuery({
    queryKey: ["units"],
    queryFn: () => materialService.getUnits(),
  })

  const { data: locations, isLoading: isFetchingLocations } = useQuery({
    queryKey: ["locations"],
    queryFn: () => materialService.getLocations(),
  })

  const { data: inspectionTemplates } = useQuery({
    queryKey: ["inspection-templates"],
    queryFn: () => supplyChainApi.listInspectionTemplates().then((r) => r.data),
    enabled: open && isEditing,
  })

  const { data: tenantProfile } = useQuery({
    queryKey: ["tenant-profile"],
    queryFn: () => tenantService.getProfile(),
  })
  const currencyCode = tenantProfile?.currency_code ?? ""

  const isFetching = isFetchingMaterial || isFetchingCategories || isFetchingUnits || isFetchingLocations;

  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm<MaterialFormValues>({
    resolver: zodResolver(materialSchema),
    defaultValues: {
      code: "",
      name: "",
      material_type: "raw",
      base_unit_id: null,
      description: "",
      category_id: "",
      reorder_level: 10,
      location_id: null,
      is_batch_tracked: false,
      is_serialized: false,
      inspection_required: false,
      inspection_template_id: null,
    }
  })

  // Reset form when material data loads or modal opens for "new"
  useEffect(() => {
    if (material) {
      reset({
        // prefer item_code; keep code for backward compat
        item_code: (material as any).item_code ?? material.code,
        code: material.code,
        name: material.name,
        material_type: (material.material_type as "raw" | "finished" | "semi_finished") || "raw",
        base_unit_id: material.base_unit_id || null,
        description: material.description || "",
        category_id: material.category_id || "",
        reorder_level: material.reorder_level ?? 10,
        location_id: material.location_id || null,
        is_batch_tracked: material.is_batch_tracked ?? false,
        is_serialized: material.is_serialized ?? false,
        inspection_required: material.inspection_required ?? false,
        inspection_template_id: material.inspection_template_id || null,
        code_locked: material.code_locked ?? true,
        current_cost: material.current_cost ?? 0,
      })
    } else if (materialId === "new") {
      reset({
        item_code: "",
        code: "",
        name: "",
        material_type: "raw",
        base_unit_id: null,
        description: "",
        category_id: "",
        reorder_level: 10,
        location_id: null,
        is_batch_tracked: false,
        is_serialized: false,
        inspection_required: false,
        inspection_template_id: null,
        code_locked: true,
      })
    }
  }, [material, materialId, reset])

  const saveMutation = useMutation({
    mutationFn: async (data: MaterialFormValues) => {
      if (isEditing) {
        return await materialService.updateMaterial(materialId!, {
          name: data.name,
          description: data.description,
          category_id: data.category_id,
          base_unit_id: data.base_unit_id,
          material_type: data.material_type,
          reorder_level: data.reorder_level,

          location_id: data.location_id,
          is_batch_tracked: data.is_batch_tracked,
          is_serialized: data.is_serialized,

          inspection_required: data.inspection_required,
          inspection_template_id: data.inspection_template_id ?? null,

          // Phase 2
          item_code: data.item_code ?? data.code ?? undefined,
          code_locked: data.code_locked ?? undefined,

          ...(data.material_type === "raw" ? { current_cost: data.current_cost ?? 0 } : {}),
        })
      } else {
        return await materialService.createMaterial({
          item_code: (data.item_code?.trim() || data.code?.trim()) || null,
          code_locked: data.code_locked ?? true,
          name: data.name,
          material_type: data.material_type,
          base_unit_id: data.base_unit_id || null,
          description: data.description || null,
          category_id: data.category_id,
          reorder_level: data.reorder_level,
          location_id: data.location_id || null,
          is_batch_tracked: data.is_batch_tracked,
          is_serialized: data.is_serialized,
          opening_stock: data.opening_stock && data.opening_stock > 0
            ? data.opening_stock
            : undefined,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] })
      onClose()
    }
  })

  const onSubmit = (data: MaterialFormValues) => {
    saveMutation.mutate(data)
  }

  const selectedMaterialType = watch("material_type") || "raw"
  const namePlaceholder =
    selectedMaterialType === "raw" ? "E.g. Brass Body" : "E.g. Gear Rotameter - Standard"
  const namingHint =
    selectedMaterialType === "raw"
      ? "Use the actual component name. Avoid generic labels like Raw Material."
      : "Use the finished product name shown to sales, planning, and clients."

  // ── General form content (shared between tabs and new-material mode) ────────
  const generalFormContent = (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="code">Item Code</Label>
          <Input id="code" placeholder="Auto-generate if blank" {...register("code")} disabled={isEditing} autoFocus={!isEditing} />
          {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="base_unit_id">Base Unit</Label>
          <Select 
            value={watch("base_unit_id") || ""} 
            onValueChange={(val) => setValue("base_unit_id", val, { shouldValidate: true })}
          >
            <SelectTrigger disabled={isEditing}>
              <SelectValue placeholder="Select Base Unit" />
            </SelectTrigger>
            <SelectContent>
              {units?.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.name} ({u.code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.base_unit_id && <p className="text-xs text-destructive">{errors.base_unit_id.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Material Name</Label>
          <Input id="name" placeholder={namePlaceholder} {...register("name")} autoFocus={isEditing} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          {!errors.name && <p className="text-xs text-muted-foreground">{namingHint}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="material_type">Material Type</Label>
          <Select 
            value={watch("material_type") || "raw"} 
            onValueChange={(val) => setValue("material_type", val as "raw" | "finished" | "semi_finished", { shouldValidate: true })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="raw">Raw Material</SelectItem>
              <SelectItem value="semi_finished">Semi-finished</SelectItem>
              <SelectItem value="finished">Finished Good</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description (Optional)</Label>
        <Textarea id="description" rows={3} {...register("description")} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="category_id">Category</Label>
          <Select 
            value={watch("category_id") || ""} 
            onValueChange={(val) => setValue("category_id", val, { shouldValidate: true })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select Category" />
            </SelectTrigger>
            <SelectContent>
              {categories?.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.category_id && <p className="text-xs text-destructive">{errors.category_id.message}</p>}
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="location_id">Storage Location</Label>
          <Select 
            value={watch("location_id") || ""} 
            onValueChange={(val) => setValue("location_id", val, { shouldValidate: true })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select Storage" />
            </SelectTrigger>
            <SelectContent>
              {locations?.map((l) => (
                <SelectItem key={l.id} value={l.id}>
                  {l.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.location_id && <p className="text-xs text-destructive">{errors.location_id.message}</p>}
        </div>
      </div>
    </div>
  )

  // ── Inventory tab content ───────────────────────────────────────────────────
  const inventoryTabContent = (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="reorder_level">Reorder Level</Label>
        <Input id="reorder_level" type="number" min="0" step="0.01" {...register("reorder_level")} />
        {errors.reorder_level && <p className="text-xs text-destructive">{errors.reorder_level.message}</p>}
      </div>

      <div className="space-y-3">
        <p className="text-sm font-medium">Tracking</p>
        <div className="flex items-center gap-2">
          <Checkbox
            id="is_batch_tracked"
            checked={watch("is_batch_tracked")}
            onCheckedChange={(v) => setValue("is_batch_tracked", v === true, { shouldValidate: true })}
          />
          <Label htmlFor="is_batch_tracked" className="font-normal cursor-pointer">Batch tracked</Label>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            id="is_serialized"
            checked={watch("is_serialized")}
            onCheckedChange={(v) => setValue("is_serialized", v === true, { shouldValidate: true })}
          />
          <Label htmlFor="is_serialized" className="font-normal cursor-pointer">Serialized</Label>
        </div>
      </div>

      {isEditing && (
        <div className="space-y-3 border-t pt-4">
          <p className="text-sm font-medium">Receiving / inspection</p>
          <div className="flex items-center gap-2">
            <Checkbox
              id="insp_req"
              checked={watch("inspection_required")}
              onCheckedChange={(v) => setValue("inspection_required", v === true, { shouldValidate: true })}
            />
            <Label htmlFor="insp_req" className="font-normal cursor-pointer">
              Inspection required
            </Label>
          </div>
          <div className="space-y-2">
            <Label>Inspection template</Label>
            <Select
              value={watch("inspection_template_id") || "__none__"}
              onValueChange={(v) =>
                setValue("inspection_template_id", v === "__none__" ? null : v, { shouldValidate: true })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="None" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">(none)</SelectItem>
                {(inspectionTemplates ?? []).map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <Drawer 
      open={open} 
      onOpenChange={(v) => !v && onClose()} 
      title={isEditing ? "Edit Material" : "New Material"}
      description={isEditing ? `Update details for ${material?.name || "material"}` : "Add a new material to your inventory catalog."}
    >
      {(isEditing && isFetching) ? (
         <FormSkeleton fields={5} />
      ) : isEditing ? (
        // ── Existing material: 4 tabs ────────────────────────────────────────
        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-4">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="inventory">Inventory</TabsTrigger>
            <TabsTrigger value="purchasing" disabled={selectedMaterialType !== "raw"}>Purchasing</TabsTrigger>
            <TabsTrigger value="history" disabled={selectedMaterialType !== "raw"}>History</TabsTrigger>
          </TabsList>

          {/* ── General tab ── */}
          <TabsContent value="general">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
              {generalFormContent}
              <div className="pt-4 flex gap-3 w-full sm:justify-end border-t">
                <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
                <Button type="submit" disabled={saveMutation.isPending} className="w-full sm:w-auto">
                  <Save className="mr-2 h-4 w-4" />
                  {saveMutation.isPending ? "Saving..." : "Save Material"}
                </Button>
              </div>
            </form>
          </TabsContent>

          {/* ── Inventory tab ── */}
          <TabsContent value="inventory">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
              {inventoryTabContent}
              <div className="pt-4 flex gap-3 w-full sm:justify-end border-t">
                <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
                <Button type="submit" disabled={saveMutation.isPending} className="w-full sm:w-auto">
                  <Save className="mr-2 h-4 w-4" />
                  {saveMutation.isPending ? "Saving..." : "Save Material"}
                </Button>
              </div>
            </form>
          </TabsContent>

          {/* ── Purchasing tab ── */}
          <TabsContent value="purchasing">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
              {/* Editable standard cost */}
              <div className="space-y-2">
                <Label htmlFor="current_cost">Standard Purchase Cost</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="current_cost"
                    type="number"
                    min="0"
                    step="0.0001"
                    placeholder="0.0000"
                    {...register("current_cost")}
                  />
                  <span className="text-sm text-muted-foreground shrink-0">
                    {currencyCode}
                  </span>
                </div>
                {errors.current_cost && (
                  <p className="text-xs text-destructive">{errors.current_cost.message as string}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Used by BOM Cost Rollup for standard costing. Set to 0 if unknown.
                </p>
              </div>

              {/* Live purchasing summary from GRNs */}
              <div className="space-y-2">
                <p className="text-sm font-medium">Purchasing Summary</p>
                <p className="text-xs text-muted-foreground">
                  Derived from completed GRN receipts. Read-only.
                </p>
                <PurchasingSummaryCard material={material} currencyCode={currencyCode} />
              </div>

              <div className="pt-4 flex gap-3 w-full sm:justify-end border-t">
                <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
                <Button type="submit" disabled={saveMutation.isPending} className="w-full sm:w-auto">
                  <Save className="mr-2 h-4 w-4" />
                  {saveMutation.isPending ? "Saving..." : "Save Material"}
                </Button>
              </div>
            </form>
          </TabsContent>

          {/* ── History tab ── */}
          <TabsContent value="history">
            <div className="pb-8">
              <div className="mb-3">
                <p className="text-sm font-medium">Purchase History</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Completed receipts only. Reversed and cancelled GRNs are excluded.
                </p>
              </div>
              {materialId && <PurchaseHistoryTable materialId={materialId} />}
            </div>
          </TabsContent>
        </Tabs>
      ) : (
        // ── New material: single form (no tabs) ──────────────────────────────
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
          {generalFormContent}

          <div className="space-y-2">
            <Label htmlFor="reorder_level">Reorder Level</Label>
            <Input id="reorder_level" type="number" min="0" step="0.01" {...register("reorder_level")} />
            {errors.reorder_level && <p className="text-xs text-destructive">{errors.reorder_level.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="opening_stock">Opening Stock</Label>
            <Input id="opening_stock" type="number" min="0" step="0.01" placeholder="Leave empty if none" {...register("opening_stock")} />
            {errors.opening_stock && <p className="text-xs text-destructive">{errors.opening_stock.message}</p>}
            <p className="text-xs text-muted-foreground">Initial stock quantity. A stock-in transaction will be recorded automatically.</p>
          </div>

          <div className="pt-4 flex gap-3 w-full sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
            <Button type="submit" disabled={saveMutation.isPending} className="w-full sm:w-auto">
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save Material"}
            </Button>
          </div>
        </form>
      )}
    </Drawer>
  )
}
