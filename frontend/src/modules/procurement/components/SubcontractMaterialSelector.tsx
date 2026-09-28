/**
 * Searchable material picker for subcontracting.
 *
 * By default shows semi_finished materials (for output product selection).
 * Pass typeFilter="raw" or typeFilter="all" to change the scope.
 */
import { useEffect, useState } from "react"
import { materialService } from "@/services/material.service"
import type { Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"

type MaterialTypeFilter = "semi_finished" | "raw" | "all"

const TYPE_LABELS: Record<string, string> = {
  raw: "Raw",
  semi_finished: "Semi-Finished",
  finished: "Finished Good",
}

type Props = {
  value: string          // material id (UUID)
  onChange: (id: string, material: Material) => void
  typeFilter?: MaterialTypeFilter
  label?: string
  placeholder?: string
  disabled?: boolean
  required?: boolean
}

export function SubcontractMaterialSelector({
  value,
  onChange,
  typeFilter = "semi_finished",
  label = "Output material",
  placeholder = "Search by code or name…",
  disabled = false,
  required = false,
}: Props) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")
  const [rows, setRows] = useState<Material[]>([])
  const [loading, setLoading] = useState(false)
  const [displayLabel, setDisplayLabel] = useState("")

  // Resolve display label when value changes externally
  useEffect(() => {
    if (!value) { setDisplayLabel(""); return }
    materialService
      .getMaterial(value)
      .then((m) => setDisplayLabel(`${m.code} — ${m.name}`))
      .catch(() => setDisplayLabel(`${value.slice(0, 8)}…`))
  }, [value])

  // Search with 280ms debounce
  useEffect(() => {
    if (!open) return
    let cancelled = false
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        const result = await materialService.getMaterials({
          query: q || undefined,
          // Pass type filter (backend accepts "raw" | "finished" but also handles "semi_finished" as a query param)
          material_type: typeFilter === "all" ? undefined : typeFilter as "raw" | "finished",
          is_active: true,
          page: 1,
          page_size: 40,
        })
        // Client-side filter for semi_finished since the API param may not support it
        let items = result.items
        if (typeFilter === "semi_finished") {
          items = items.filter((m) => m.material_type === "semi_finished")
        } else if (typeFilter === "raw") {
          items = items.filter((m) => m.material_type === "raw" || m.material_type === "semi_finished")
        }
        if (!cancelled) setRows(items)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 280)
    return () => { cancelled = true; clearTimeout(t) }
  }, [q, open, typeFilter])

  const pick = (m: Material) => {
    onChange(m.id, m)
    setDisplayLabel(`${m.code} — ${m.name}`)
    setOpen(false)
    setQ("")
  }

  return (
    <div className="space-y-2">
      {label && (
        <Label>
          {label}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
      )}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            className={cn(
              "w-full justify-start font-normal",
              !displayLabel && "text-muted-foreground"
            )}
            disabled={disabled}
          >
            {displayLabel || placeholder}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[min(100vw-2rem,32rem)] p-3" align="start">
          <Input
            autoFocus
            placeholder="Search code or name…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="mb-2"
          />
          <div className="max-h-64 overflow-auto space-y-1 text-sm">
            {loading && <p className="text-muted-foreground text-xs py-2 text-center">Loading…</p>}
            {!loading && rows.length === 0 && (
              <p className="text-muted-foreground text-xs py-2 text-center">
                No {typeFilter === "semi_finished" ? "semi-finished " : ""}materials found.
                {typeFilter === "semi_finished" && (
                  <> Go to <strong>Inventory → Materials</strong> to create one.</>
                )}
              </p>
            )}
            {rows.map((m) => (
              <button
                key={m.id}
                type="button"
                className={cn(
                  "w-full text-left rounded px-2 py-2 hover:bg-muted transition-colors"
                )}
                onClick={() => pick(m)}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-medium text-xs">{m.code}</span>
                  <span className="text-xs rounded-full px-1.5 py-0.5 bg-slate-100 text-slate-600">
                    {TYPE_LABELS[m.material_type] ?? m.material_type}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground truncate mt-0.5">{m.name}</div>
              </button>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
