import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search, Loader2, Package2, Layers, Box, X } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOMLineInput, ComponentType } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { materialService } from "@/services/material.service"

interface BOMLineFormProps {
  onAdd: (line: BOMLineInput) => void
  onCancel: () => void
}

// ─── Debounce hook ────────────────────────────────────────────────────────────
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])
  return debounced
}

const typeIcons = {
  material: Package2,
  template: Layers,
  variant: Box,
} as const

const componentSources = [
  { value: "raw", title: "Raw material", description: "An input such as a wooden board.", icon: Package2 },
  { value: "semi_finished", title: "Semi-finished item", description: "A part already tracked in stock, such as a chair seat.", icon: Box },
  { value: "product", title: "Product BOM reference", description: "Show another item’s BOM and its inputs in this product’s BOM tree.", icon: Layers },
] as const

type ComponentSource = (typeof componentSources)[number]["value"]
type ProductReference = Extract<ComponentType, "template" | "variant">

// ─── Component search result ──────────────────────────────────────────────────
interface ComponentResult {
  id: string
  label: string
  sub?: string
  type: ComponentType
  baseUnitId?: string | null
}

export function BOMLineForm({ onAdd, onCancel }: BOMLineFormProps) {
  const [source, setSource] = useState<ComponentSource>("raw")
  const [productReference, setProductReference] = useState<ProductReference>("variant")
  const compType: ComponentType = source === "product" ? productReference : "material"
  const [search, setSearch] = useState("")
  const [selected, setSelected] = useState<ComponentResult | null>(null)
  const [qty, setQty] = useState("1")
  const [scrap, setScrap] = useState("0")
  const [unitId, setUnitId] = useState("")

  const debouncedSearch = useDebounce(search, 300)

  // Fetch units for unit selector
  const { data: units, isPending: loadingUnits, isError: unitsUnavailable, refetch: refetchUnits } = useQuery({
    queryKey: ["units"],
    queryFn: () => materialService.getUnits(),
    staleTime: 60_000,
  })
  const activeUnits = (units ?? []).filter(unit => unit.is_active)
  const selectedUnit = activeUnits.find(unit => unit.id === unitId)
  const stockUnit = activeUnits.find(unit => unit.id === selected?.baseUnitId)

  // Fetch components based on type + debounced search
  const { data: results, isFetching: searching } = useQuery({
    queryKey: ["component-search", source, compType, debouncedSearch],
    queryFn: async (): Promise<ComponentResult[]> => {
      if (compType === "material") {
        const materialType = source === "semi_finished" ? "semi_finished" : "raw"
        const r = await bomService.getMaterials({
          query: debouncedSearch,
          material_type: materialType,
          page_size: 20,
        })
        const filtered = r.items.filter(m => m.material_type === materialType)
        return filtered.map(m => ({ id: m.id, label: m.name, sub: m.code, type: "material", baseUnitId: m.base_unit_id }))
      } else if (compType === "template") {
        const r = await bomService.getTemplates({ query: debouncedSearch, page_size: 20 })
        return r.items.map((t) => ({ id: t.id, label: t.name, sub: t.code, type: "template", baseUnitId: t.base_unit_id }))
      } else {
        const r = await bomService.getAllVariants({ query: debouncedSearch, page_size: 20 })
        return r.items.map((v) => ({ id: v.id, label: v.name, sub: v.code, type: "variant", baseUnitId: v.base_unit_id }))
      }
    },
    enabled: !selected,
    staleTime: 10_000,
  })

  const handleSelect = (item: ComponentResult) => {
    setSelected(item)
    setSearch(item.label)
    setUnitId("")
  }

  const resetComponent = () => {
    setSelected(null)
    setSearch("")
    setUnitId("")
  }

  const handleAdd = () => {
    if (!selected || !selectedUnit) return
    const line: BOMLineInput = {
      quantity: parseFloat(qty) || 1,
      scrap_percentage: parseFloat(scrap) || 0,
      unit_id: selectedUnit.id,
    }
    if (selected.type === "material") line.material_id = selected.id
    else if (selected.type === "template") line.template_id = selected.id
    else line.variant_id = selected.id
    onAdd(line)
  }

  const Icon = typeIcons[compType]

  return (
    <div className="rounded-lg border bg-muted/20 p-4 space-y-4">
      <h4 className="text-sm font-medium">Add Component</h4>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">What are you adding?</legend>
        <div className="grid gap-2 md:grid-cols-3">
          {componentSources.map(({ value, title, description, icon: SourceIcon }) => (
            <label key={value} className={cn(
              "flex items-start gap-2 rounded-lg border bg-background p-3 text-sm",
              "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
              source === value && "border-primary bg-primary/5",
            )}>
              <input
                type="radio"
                name="bom-component-source"
                className="mt-1 shrink-0 accent-primary"
                checked={source === value}
                onChange={() => { setSource(value); resetComponent() }}
                aria-label={title}
              />
              <span>
                <span className="flex items-start gap-1.5 font-medium">
                  <SourceIcon className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                  {title}
                </span>
                <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{description}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {source === "product" && (
        <div className="space-y-2">
          <div className="rounded-md bg-muted px-3 py-2 text-xs leading-relaxed text-muted-foreground">
            <p className="font-medium text-foreground">Link the BOM for the part your contractor makes</p>
            <p className="mt-1">
              Select the semi-finished variant with the active BOM that lists the raw materials you send to the contractor.
              If you created that BOM for the template, choose <strong>Shared product template BOM</strong> instead.
              For example, add the chair seat BOM to the finished chair BOM to see the wooden boards under the chair seat in the BOM tree.
            </p>
          </div>
          <Label htmlFor="bom-component-product-reference">Where was the component’s BOM created?</Label>
          <Select value={productReference} onValueChange={(value) => {
            setProductReference(value === "template" ? "template" : "variant")
            resetComponent()
          }}>
            <SelectTrigger id="bom-component-product-reference"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="variant">Specific variant BOM</SelectItem>
              <SelectItem value="template">Shared product template BOM</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Debounced search */}
      <div className="space-y-1.5">
        <Label htmlFor="bom-component-search">
          {source === "raw" ? "Search raw materials" : source === "semi_finished" ? "Search semi-finished items" : compType === "variant" ? "Search product variants" : "Search product templates"}
        </Label>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            id="bom-component-search"
            className="pl-8 pr-8"
            placeholder={
              source === "raw" ? "Search raw material by name or code..."
                : source === "semi_finished" ? "Search semi-finished item by name or code..."
                : "Search by name or code..."
            }
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              if (selected) setSelected(null)
            }}
          />
          {(searching) && (
            <Loader2 className="absolute right-2.5 top-2.5 w-4 h-4 text-muted-foreground animate-spin" />
          )}
          {selected && (
            <button
              className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground"
              onClick={() => { setSelected(null); setSearch(""); setUnitId("") }}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Search results dropdown */}
        {!selected && search && results && results.length > 0 && (
          <div className="rounded-md border bg-popover shadow-md overflow-hidden max-h-48 overflow-y-auto z-10">
            {results.map((r) => (
              <button
                key={r.id}
                className={cn(
                  "w-full text-left px-3 py-2 text-sm hover:bg-accent/60 flex items-center gap-2",
                  "transition-colors"
                )}
                onClick={() => handleSelect(r)}
              >
                <Icon className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                <div className="min-w-0">
                  <span className="truncate font-medium">{r.label}</span>
                  {r.sub && (
                    <span className="text-xs text-muted-foreground ml-2 font-mono">{r.sub}</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
        {!selected && search && results && results.length === 0 && !searching && (
          <p className="text-xs text-muted-foreground px-1">No results found.</p>
        )}
      </div>

      {/* Quantity, Scrap, Unit row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label>Quantity</Label>
          <Input
            type="number"
            min="0.001"
            step="0.01"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            placeholder="1"
          />
        </div>
        <div className="space-y-1.5">
          <Label>Scrap %</Label>
          <Input
            type="number"
            min="0"
            max="100"
            step="0.1"
            value={scrap}
            onChange={(e) => setScrap(e.target.value)}
            placeholder="0"
          />
        </div>
        <div className="col-span-2 space-y-1.5 sm:col-span-1">
          <Label htmlFor="bom-component-unit">Unit of measure (required)</Label>
          <Select value={unitId} onValueChange={setUnitId} disabled={!selected || activeUnits.length === 0}>
            <SelectTrigger id="bom-component-unit" aria-describedby="bom-component-unit-help">
              <SelectValue placeholder="Select a unit" />
            </SelectTrigger>
            <SelectContent>
              {activeUnits.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.code} — {u.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div id="bom-component-unit-help" className="text-xs text-muted-foreground">
            {loadingUnits ? "Loading units…" : unitsUnavailable ? (
              <button type="button" className="underline" onClick={() => void refetchUnits()}>Could not load units. Retry</button>
            ) : activeUnits.length === 0 ? "No active units are configured." : !selected ? "Select a component first." : stockUnit
              ? `Stock unit for this component: ${stockUnit.code}`
              : "Choose the unit for the quantity entered above."}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          size="sm"
          disabled={!selected || !selectedUnit || !qty || parseFloat(qty) <= 0}
          onClick={handleAdd}
        >
          Add Line
        </Button>
      </div>
    </div>
  )
}
