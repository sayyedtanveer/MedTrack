import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import {
  Layers, Search, CheckCircle2, Circle, AlertCircle,
  Copy, Eye, IndianRupee, ChevronDown, Plus, Calendar, Clock, Loader2
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { toast } from "sonner"
import { usePermissions } from "@/hooks/usePermissions"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { formatCurrency } from "@/utils/currency"

// We list BOMs by fetching templates first, then their BOMs
export default function BOMListPage() {
  const navigate = useNavigate()
  const { canEditBOM } = usePermissions()
  const [search, setSearch] = useState("")
  const [showOnlyWithBOM, setShowOnlyWithBOM] = useState(false)
  const [showOnlyActive, setShowOnlyActive] = useState(false)
  const [showOnlyDraft, setShowOnlyDraft] = useState(false)

  const { data: tplData, isLoading, isError, refetch } = useQuery({
    queryKey: ["bom-list-templates"],
    queryFn: () => bomService.getTemplates({ page_size: 100 }),
    staleTime: 30_000,
  })

  const templates = tplData?.items ?? []
  
  // Apply filters
  const filtered = templates
    .filter((template) => {
      if (search) {
        return (
          template.name.toLowerCase().includes(search.toLowerCase()) ||
          template.code.toLowerCase().includes(search.toLowerCase())
        )
      }
      return true
    })

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Bill of Materials"
        description="Manage multi-level BOMs, versions, and manufacturing routing."
        action={
          canEditBOM() ? (
            <Button onClick={() => navigate("/bom/new")} className="gap-1.5">
              <Layers className="w-4 h-4" />
              New BOM
            </Button>
          ) : undefined
        }
      />

      {/* Search and filters */}
      <div className="space-y-3">
        <div className="relative max-w-sm">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant={showOnlyWithBOM ? "default" : "outline"}
            size="sm"
            onClick={() => { setShowOnlyWithBOM(!showOnlyWithBOM); if(!showOnlyWithBOM) { setShowOnlyActive(false); setShowOnlyDraft(false); } }}
            className="gap-1.5"
          >
            <Circle className="w-3 h-3" />
            Has BOM
          </Button>
          <Button
            variant={showOnlyActive ? "default" : "outline"}
            size="sm"
            onClick={() => { setShowOnlyActive(!showOnlyActive); if(!showOnlyActive){ setShowOnlyWithBOM(false); setShowOnlyDraft(false); } }}
            className="gap-1.5"
          >
            <CheckCircle2 className="w-3 h-3" />
            Active Only
          </Button>
          <Button
            variant={showOnlyDraft ? "default" : "outline"}
            size="sm"
            onClick={() => { setShowOnlyDraft(!showOnlyDraft); if(!showOnlyDraft){ setShowOnlyWithBOM(false); setShowOnlyActive(false); } }}
            className="gap-1.5"
          >
            <AlertCircle className="w-3 h-3" />
            Draft Only
          </Button>
        </div>
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <div className="flex items-center justify-between w-full">
            <AlertDescription>Failed to load product list.</AlertDescription>
            <Button
              variant="outline"
              size="sm"
              className="ml-4 h-8"
              onClick={() => refetch()}
            >
              Retry
            </Button>
          </div>
        </Alert>
      )}

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-4 border border-dashed rounded-xl bg-muted/20">
          <div className="rounded-full bg-muted p-4">
            <Layers className="w-8 h-8 text-muted-foreground" />
          </div>
          <div className="text-center space-y-1">
            <h3 className="font-semibold text-base">
              No matching products found
            </h3>
            <p className="text-sm text-muted-foreground max-w-xs">
              Try a different search term.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tpl) => (
            <TemplateCard
              key={tpl.id}
              templateId={tpl.id}
              name={tpl.name}
              code={tpl.code}
              showOnlyWithBOM={showOnlyWithBOM}
              showOnlyActive={showOnlyActive}
              showOnlyDraft={showOnlyDraft}
              onClick={() => navigate(`/bom/list?templateId=${tpl.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Template card with mini version list ────────────────────────────────────

function TemplateCard({
  templateId,
  name,
  code,
  showOnlyWithBOM,
  showOnlyActive,
  showOnlyDraft,
  onClick,
}: {
  templateId: string
  name: string
  code: string
  showOnlyWithBOM: boolean
  showOnlyActive: boolean
  showOnlyDraft: boolean
  onClick: () => void
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { canEditBOM } = usePermissions()
  const [showCost, setShowCost] = useState(false)
  
  const { data, isLoading } = useQuery({
    queryKey: ["bom-versions", templateId, true],
    queryFn: () => bomService.getBOMsForProduct(templateId, true),
    staleTime: 30_000,
  })

  const boms = data?.items ?? []
  const activeBom = boms.find((b) => b.is_active)
  const draftBoms = boms.filter((b) => !b.is_active)
  
  // Use either active BOM or newest draft as the representative BOM for the card
  const representativeBom = activeBom || boms[0]

  // Cost fetch on demand to prevent mass API polling
  const { data: costData, isLoading: costLoading } = useQuery({
    queryKey: ["bom-cost", representativeBom?.id],
    queryFn: () => bomService.getBOMCost(representativeBom!.id),
    staleTime: 60_000,
    enabled: !!representativeBom && showCost,
  })

  // Apply filters AFTER all hooks are called
  const hasBoMs = boms.length > 0
  if (showOnlyWithBOM && !hasBoMs) return null
  if (showOnlyActive && !activeBom) return null
  if (showOnlyDraft && draftBoms.length === 0) return null

  const componentCount = representativeBom?.lines?.length ?? 0
  const operationsCount = representativeBom?.operations_count ?? 0
  const totalCost = costData?.total_cost ?? null
  const currencySymbol = costData?.currency_symbol ?? "₹"

  // Date formatters
  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A"
    return new Date(dateString).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
  }
  
  const formatRelative = (dateString?: string) => {
    if (!dateString) return "N/A"
    const diff = Date.now() - new Date(dateString).getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    if (days === 0) return "Today"
    if (days === 1) return "Yesterday"
    if (days < 30) return `${days} days ago`
    return formatDate(dateString)
  }

  const handleCreateBom = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await bomService.createBOM(templateId, {
        version: "v1.0",
        valid_from: new Date().toISOString(),
        template_id: templateId,
        lines: []
      })
      
      // Invalidate the query to refresh the BOM list immediately
      queryClient.invalidateQueries({ queryKey: ["bom-versions", templateId, true] })
      
      toast.success("BOM created successfully")
      navigate(`/bom/${res.id}`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to create BOM")
    }
  }

  return (
    <Card
      className="cursor-pointer hover:border-primary/50 hover:bg-accent/20 transition-all flex flex-col justify-between group"
      onClick={onClick}
    >
      <CardContent className="p-4 space-y-4">
        {/* Header with quick actions */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-sm truncate">{name}</h3>
            <p className="text-xs text-muted-foreground font-mono">{code}</p>
          </div>
          
          {representativeBom && canEditBOM() && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button variant="ghost" size="sm" className="w-7 h-7 p-0 hover:bg-primary/10">
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/bom/${representativeBom.id}`); }} className="gap-2">
                  <Eye className="w-3.5 h-3.5" />
                  View Details
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/bom/${representativeBom.id}?tab=tree`); }} className="gap-2">
                  <Layers className="w-3.5 h-3.5" />
                  View Tree
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/bom/${representativeBom.id}?action=copy`); }} className="gap-2">
                  <Copy className="w-3.5 h-3.5" />
                  Copy version
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        {/* BOM status and metrics */}
        {isLoading ? (
          <Skeleton className="h-10 w-full" />
        ) : boms.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-5 gap-2 border border-dashed border-border/60 rounded-lg bg-muted/10">
            <Layers className="w-5 h-5 text-muted-foreground/40" />
            <p className="text-xs font-medium text-muted-foreground">No BOM available</p>
            {canEditBOM() && (
              <Button variant="outline" size="sm" className="h-7 text-xs mt-1 bg-background" onClick={handleCreateBom}>
                <Plus className="w-3 h-3 mr-1.5" />
                Create BOM
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {/* Version counts and badges */}
            <div className="flex items-center flex-wrap gap-2 text-xs">
              <span className="text-muted-foreground font-medium">{boms.length} version{boms.length > 1 ? 's' : ''}</span>
              <div className="flex flex-wrap gap-1.5 ml-auto">
                {activeBom && (
                  <Badge className="bg-green-100 text-green-800 border-green-200 hover:bg-green-200 shadow-none font-normal px-1.5 py-0 flex items-center gap-1">
                     <span className="text-[10px]">●</span>
                     Active v{activeBom.version}
                  </Badge>
                )}
                {draftBoms.slice(0, activeBom ? 1 : 2).map(draft => (
                  <Badge key={draft.id} variant="outline" className="text-muted-foreground font-normal px-1.5 py-0 flex items-center gap-1">
                     <span className="text-[10px]">○</span>
                     v{draft.version}
                  </Badge>
                ))}
                {draftBoms.length > (activeBom ? 1 : 2) && (
                   <span className="text-[10px] text-muted-foreground self-center">+{draftBoms.length - (activeBom ? 1 : 2)}</span>
                )}
              </div>
            </div>

            {/* Representative BOM details */}
            {representativeBom && (
              <div className="pt-2 border-t space-y-3">
                {/* Dates */}
                <div className="flex flex-col gap-1 text-[11px] text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3 h-3" />
                    <span>Created: {formatDate(representativeBom.created_at)}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3" />
                    <span>Updated: <span className="text-foreground">{formatRelative(representativeBom.updated_at)}</span></span>
                  </div>
                </div>

                {/* Structure row */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex flex-col bg-muted/30 px-2 py-1.5 rounded border border-border/40">
                    <span className="text-muted-foreground text-[10px] uppercase font-semibold">Components</span>
                    <span className="font-medium text-foreground">{componentCount}</span>
                  </div>
                  <div className="flex flex-col bg-muted/30 px-2 py-1.5 rounded border border-border/40">
                    <span className="text-muted-foreground text-[10px] uppercase font-semibold">Operations</span>
                    <span className="font-medium text-foreground">{operationsCount}</span>
                  </div>
                </div>

                {/* Cost row */}
                <div className="flex items-center justify-between text-xs p-2 rounded bg-primary/5 border border-primary/10">
                   <div className="font-medium text-muted-foreground flex items-center gap-1.5">
                     <IndianRupee className="w-3.5 h-3.5 text-primary" />
                     Total Cost
                   </div>
                   <div className="font-semibold text-primary">
                     {!showCost ? (
                       <Button variant="ghost" size="sm" className="h-5 px-2 text-[10px] uppercase font-bold tracking-wide" onClick={(e) => { e.stopPropagation(); setShowCost(true); }}>
                         Load Cost
                       </Button>
                     ) : costLoading ? (
                       <Loader2 className="w-3 h-3 animate-spin"/>
                     ) : totalCost !== null ? (
                       formatCurrency(totalCost, currencySymbol)
                     ) : "—"}
                   </div>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
