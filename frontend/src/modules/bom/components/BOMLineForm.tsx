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

// ─── Component search result ──────────────────────────────────────────────────
interface ComponentResult {
  id: string
  label: string
  sub?: string
  type: ComponentType
}

export function BOMLineForm({ onAdd, onCancel }: BOMLineFormProps) {
  const [compType, setCompType] = useState<ComponentType>("material")
  const [search, setSearch] = useState("")
  const [selected, setSelected] = useState<ComponentResult | null>(null)
  const [qty, setQty] = useState("1")
  const [scrap, setScrap] = useState("0")
  const [unitId, setUnitId] = useState("auto")

  const debouncedSearch = useDebounce(search, 300)

  // Fetch units for unit selector
  const { data: units } = useQuery({
    queryKey: ["units"],
    queryFn: () => materialService.getUnits(),
    staleTime: 60_000,
  })

  // Fetch components based on type + debounced search
  const { data: results, isFetching: searching } = useQuery({
    queryKey: ["component-search", compType, debouncedSearch],
    queryFn: async (): Promise<ComponentResult[]> => {
      if (compType === "material") {
        const r = await bomService.getMaterials({
          query: debouncedSearch,
          material_type: "raw",
          page_size: 20,
        })
        return r.items.map((m) => ({ id: m.id, label: m.name, sub: m.code, type: "material" }))
      } else if (compType === "template") {
        const r = await bomService.getTemplates({ query: debouncedSearch, page_size: 20 })
        return r.items.map((t) => ({ id: t.id, label: t.name, sub: t.code, type: "template" }))
      } else {
        const r = await bomService.getAllVariants({ query: debouncedSearch, page_size: 20 })
        return r.items.map((v) => ({ id: v.id, label: v.name, sub: v.code, type: "variant" }))
      }
    },
    enabled: !selected,
    staleTime: 10_000,
  })

  const handleSelect = (item: ComponentResult) => {
    setSelected(item)
    setSearch(item.label)
  }

  const handleTypeChange = (t: ComponentType) => {
    setCompType(t)
    setSelected(null)
    setSearch("")
  }

  const handleAdd = () => {
    if (!selected) return
    const line: BOMLineInput = {
      quantity: parseFloat(qty) || 1,
      scrap_percentage: parseFloat(scrap) || 0,
      unit_id: unitId && unitId !== "auto" ? unitId : undefined,
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

      {/* Type selector */}
      <div className="space-y-1.5">
        <Label>Component Type</Label>
        <Select value={compType} onValueChange={(v) => handleTypeChange(v as ComponentType)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="material">
              <span className="flex items-center gap-2">
                <Package2 className="w-3.5 h-3.5" /> Raw Material
              </span>
            </SelectItem>
            <SelectItem value="template">
              <span className="flex items-center gap-2">
                <Layers className="w-3.5 h-3.5" /> Semi-Finished / Sub-Assembly (Base Product)
              </span>
            </SelectItem>
            <SelectItem value="variant">
              <span className="flex items-center gap-2">
                <Box className="w-3.5 h-3.5" /> Semi-Finished / Sub-Assembly (Specific Variant)
              </span>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Debounced search */}
      <div className="space-y-1.5">
        <Label>
          Search {compType === "material" ? "Raw Material" : "Sub-Assembly"}
        </Label>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            className="pl-8 pr-8"
            placeholder={
              compType === "material"
                ? "Search raw material by name or code..."
                : "Search sub-assembly by name or code..."
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
              onClick={() => { setSelected(null); setSearch("") }}
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
        {compType === "material" && (
          <p className="text-xs text-muted-foreground px-1 mt-1">
            BOM material lines are only for consumable raw items. Use sub-assemblies for manufactured items.
          </p>
        )}
      </div>

      {/* Quantity, Scrap, Unit row */}
      <div className="grid grid-cols-3 gap-3">
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
        <div className="space-y-1.5">
          <Label>Unit</Label>
          <Select value={unitId} onValueChange={setUnitId}>
            <SelectTrigger>
              <SelectValue placeholder="Auto" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto</SelectItem>
              {(units ?? []).map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.code}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          size="sm"
          disabled={!selected || !qty || parseFloat(qty) <= 0}
          onClick={handleAdd}
        >
          Add Line
        </Button>
      </div>
    </div>
  )
}
