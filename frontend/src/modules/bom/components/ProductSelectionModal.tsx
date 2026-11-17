import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search, Package2, ChevronDown, ChevronRight, AlertCircle, Loader2, Layers } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { ItemTemplate, ItemVariant } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"

interface ProductSelectionModalProps {
  onSelect: (product: ItemTemplate | ItemVariant, isTemplate: boolean) => void
  onCancel: () => void
}

/** Build a human-readable attribute string from variant_key e.g. "SIZE=SMALL|COLOR=RED" → "SMALL / RED" */
function formatAttributes(variant_key: string): string {
  if (!variant_key) return ""
  return variant_key
    .split("|")
    .map((kv) => kv.split("=").slice(1).join("="))
    .join(" / ")
}

export function ProductSelectionModal({ onSelect, onCancel }: ProductSelectionModalProps) {
  const [searchQuery, setSearchQuery] = useState("")
  // Track which template groups are expanded; default all expanded
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [selectedId, setSelectedId] = useState<string>("")
  const [selectedIsTemplate, setSelectedIsTemplate] = useState<boolean>(false)

  // ── Data fetching ─────────────────────────────────────────────────────────
  const {
    data: templatesData,
    isLoading: isLoadingTemplates,
    isError: isErrorTemplates,
  } = useQuery({
    queryKey: ["bom-templates"],
    queryFn: () => bomService.getTemplates({ page_size: 100 }),
    staleTime: 30_000,
  })

  const {
    data: variantsData,
    isLoading: isLoadingVariants,
    isError: isErrorVariants,
  } = useQuery({
    queryKey: ["bom-variants"],
    queryFn: () => bomService.getAllVariants({ page_size: 100 }),
    staleTime: 30_000,
  })

  const templates = templatesData?.items ?? []
  const variants = variantsData?.items ?? []
  const isLoading = isLoadingTemplates || isLoadingVariants
  const isError = isErrorTemplates || isErrorVariants

  // ── Build grouped structure ───────────────────────────────────────────────
  // Map template_id → variants that belong to it
  const variantsByTemplate = useMemo(() => {
    const map: Record<string, ItemVariant[]> = {}
    for (const v of variants) {
      const tid = v.template_id
      if (!map[tid]) map[tid] = []
      map[tid].push(v)
    }
    return map
  }, [variants])

  // ── Filtered groups (search-aware) ────────────────────────────────────────
  const filteredGroups = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()

    return templates
      .map((tpl) => {
        const tplVariants = variantsByTemplate[tpl.id] ?? []

        if (!q) {
          return { template: tpl, variants: tplVariants, matchesParent: true }
        }

        const parentMatches =
          tpl.name.toLowerCase().includes(q) || tpl.code.toLowerCase().includes(q)
        const matchingVariants = tplVariants.filter(
          (v) =>
            v.name.toLowerCase().includes(q) ||
            v.code.toLowerCase().includes(q) ||
            (v.variant_key && v.variant_key.toLowerCase().includes(q)) ||
            formatAttributes(v.variant_key ?? "").toLowerCase().includes(q)
        )

        if (!parentMatches && matchingVariants.length === 0) return null

        return {
          template: tpl,
          variants: parentMatches ? tplVariants : matchingVariants,
          matchesParent: parentMatches,
        }
      })
      .filter(Boolean) as Array<{
        template: ItemTemplate
        variants: ItemVariant[]
        matchesParent: boolean
      }>
  }, [templates, variantsByTemplate, searchQuery])

  const totalVisible = filteredGroups.reduce(
    (n, g) => n + 1 + g.variants.length,
    0
  )

  // ── Expand helpers ────────────────────────────────────────────────────────
  const isExpanded = (tplId: string) =>
    expanded[tplId] !== false // default: expanded

  const toggleExpand = (tplId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpanded((prev) => ({ ...prev, [tplId]: !isExpanded(tplId) }))
  }

  // ── Selection ─────────────────────────────────────────────────────────────
  const selectTemplate = (tpl: ItemTemplate) => {
    setSelectedId(tpl.id)
    setSelectedIsTemplate(true)
  }

  const selectVariant = (v: ItemVariant) => {
    setSelectedId(v.id)
    setSelectedIsTemplate(false)
  }

  const handleConfirm = () => {
    if (!selectedId) return
    if (selectedIsTemplate) {
      const tpl = templates.find((t) => t.id === selectedId)
      if (tpl) onSelect(tpl, true)
    } else {
      const v = variants.find((v) => v.id === selectedId)
      if (v) onSelect(v, false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold">Select Finished Good</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Select a parent template or a specific variant to target
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          id="product-search"
          placeholder="Search by name, code or variant attributes…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 h-9 text-sm"
          autoFocus
        />
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 rounded-md" />
          ))}
        </div>
      )}

      {/* Error */}
      {!isLoading && isError && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>Failed to load products. Please try again.</AlertDescription>
        </Alert>
      )}

      {/* Empty */}
      {!isLoading && !isError && totalVisible === 0 && (
        <div className="text-center py-8 text-sm text-muted-foreground">
          <Package2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
          {searchQuery
            ? `No products match "${searchQuery}"`
            : "No finished goods found. Create a product template first."}
        </div>
      )}

      {/* Grouped product list */}
      {!isLoading && !isError && totalVisible > 0 && (
        <div className="border rounded-md overflow-hidden bg-card max-h-[55vh] overflow-y-auto">
          {filteredGroups.map(({ template: tpl, variants: tplVariants }) => {
            const exp = isExpanded(tpl.id)
            const isSelected = selectedId === tpl.id && selectedIsTemplate

            return (
              <div key={tpl.id} className="border-b last:border-b-0">
                {/* ── Template row ── */}
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => selectTemplate(tpl)}
                  onKeyDown={(e) => e.key === "Enter" && selectTemplate(tpl)}
                  className={`flex items-center gap-2 px-3 py-2.5 cursor-pointer select-none transition-colors ${
                    isSelected
                      ? "bg-primary/8 border-l-2 border-primary"
                      : "hover:bg-muted/40"
                  }`}
                >
                  {/* Expand toggle */}
                  {tplVariants.length > 0 ? (
                    <button
                      type="button"
                      onClick={(e) => toggleExpand(tpl.id, e)}
                      className="shrink-0 w-5 h-5 flex items-center justify-center rounded hover:bg-muted text-muted-foreground"
                      aria-label={exp ? "Collapse variants" : "Expand variants"}
                    >
                      {exp ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                    </button>
                  ) : (
                    <span className="w-5 shrink-0" />
                  )}

                  <Package2 className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />

                  <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm truncate">{tpl.name}</span>
                    <span className="font-mono text-xs text-muted-foreground shrink-0">
                      {tpl.code}
                    </span>
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0 shrink-0 bg-blue-50 text-blue-700 border-blue-200"
                    >
                      Template
                    </Badge>
                    {tplVariants.length > 0 && (
                      <span className="text-xs text-muted-foreground shrink-0">
                        {tplVariants.length} variant{tplVariants.length !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>

                  {/* Selection indicator */}
                  <div
                    className={`w-4 h-4 rounded-full border-2 shrink-0 transition-colors ${
                      isSelected
                        ? "bg-primary border-primary"
                        : "border-muted-foreground/40"
                    }`}
                  />
                </div>

                {/* ── Variant rows (collapsible) ── */}
                {exp &&
                  tplVariants.map((v) => {
                    const isVarSelected = selectedId === v.id && !selectedIsTemplate
                    const attrs = formatAttributes(v.variant_key ?? "")

                    return (
                      <div
                        key={v.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => selectVariant(v)}
                        onKeyDown={(e) => e.key === "Enter" && selectVariant(v)}
                        className={`flex items-center gap-2 pl-9 pr-3 py-2 cursor-pointer select-none transition-colors border-t border-dashed border-muted ${
                          isVarSelected
                            ? "bg-primary/8 border-l-2 border-primary"
                            : "hover:bg-muted/30"
                        }`}
                      >
                        <Layers className="w-3 h-3 shrink-0 text-muted-foreground/70" />

                        <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
                          <span className="text-sm truncate">{v.name}</span>
                          <span className="font-mono text-xs text-muted-foreground shrink-0">
                            {v.code}
                          </span>
                          {attrs && (
                            <span className="text-xs text-muted-foreground/80 bg-muted/60 px-1.5 py-0.5 rounded shrink-0">
                              {attrs}
                            </span>
                          )}
                          <Badge
                            variant="outline"
                            className="text-[10px] px-1.5 py-0 shrink-0 bg-emerald-50 text-emerald-700 border-emerald-200"
                          >
                            Variant
                          </Badge>
                        </div>

                        <div
                          className={`w-4 h-4 rounded-full border-2 shrink-0 transition-colors ${
                            isVarSelected
                              ? "bg-primary border-primary"
                              : "border-muted-foreground/40"
                          }`}
                        />
                      </div>
                    )
                  })}
              </div>
            )
          })}
        </div>
      )}

      {/* Count info */}
      {!isLoading && !isError && totalVisible > 0 && (
        <p className="text-xs text-muted-foreground">
          {filteredGroups.length} product{filteredGroups.length !== 1 ? "s" : ""}
          {searchQuery && " matching"}
          {selectedId && (
            <span className="ml-2 text-primary font-medium">
              · {selectedIsTemplate ? "Template" : "Variant"} selected
            </span>
          )}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2 justify-end pt-1">
        <Button variant="outline" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={handleConfirm}
          disabled={!selectedId || isLoading}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              Loading…
            </>
          ) : (
            "Select Product"
          )}
        </Button>
      </div>
    </div>
  )
}
