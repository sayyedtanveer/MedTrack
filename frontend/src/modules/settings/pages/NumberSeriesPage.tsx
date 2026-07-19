import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useMemo, useState } from "react"
import { useToast } from "@/hooks/use-toast"
import { useNavigate } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { Settings2, Pencil, RefreshCw, AlertCircle } from "lucide-react"
import { numberSeriesService, NumberSeriesConfig } from "@/services/number-series.service"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { usePermissions } from "@/hooks/usePermissions"
import { BusinessAssistantPanel } from "@/components/shared/BusinessAssistantPanel"
import { numberSeriesListAssistant } from "../business-assistant/numberSeriesAssistant"

/** Human-friendly labels for entity types */
const ENTITY_TYPE_LABELS: Record<string, string> = {
  material: "Material",
  product: "Product",
  purchase_order: "Purchase Order",
  sales_order: "Sales Order",
  invoice: "Invoice",
  grn: "GRN",
  work_order: "Work Order",
  batch: "Batch",
  customer: "Customer",
  supplier: "Supplier",
}

function formatEntityType(entityType: string): string {
  return ENTITY_TYPE_LABELS[entityType] || entityType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

function buildFormatPreview(config: NumberSeriesConfig): string {
  const parts: string[] = [config.prefix || "??"]
  if (config.include_abbreviation) {
    parts.push("ABC".slice(0, config.abbreviation_length || 3))
  }
  parts.push("0".repeat(config.sequence_length || 6))
  return parts.join(config.separator || "-")
}

export default function NumberSeriesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isAdmin } = usePermissions()
  const [initializing, setInitializing] = useState(false)

  const { data: configs, isLoading, isError, refetch } = useQuery({
    queryKey: ["number-series-configs"],
    queryFn: () => numberSeriesService.listConfigs(),
    retry: 1,
  })
  const { toast } = useToast()

  /** Manual initialize handler — re-calls the list endpoint which seeds defaults */
  const handleInitialize = async () => {
    setInitializing(true)
    try {
      const result = await refetch()
      if (result.error) {
        toast({
          title: "Initialization failed",
          description: (result.error as any)?.message || "Failed to initialize number series",
          variant: "destructive",
        })
      }
      queryClient.invalidateQueries({ queryKey: ["number-series-configs"] })
    } finally {
      setInitializing(false)
    }
  }

  const canEdit = isAdmin()

  const columns = useMemo<ColumnDef<NumberSeriesConfig>[]>(
    () => [
      {
        accessorKey: "entity_type",
        header: "Entity Type",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{formatEntityType(row.original.entity_type)}</span>
          </div>
        ),
      },
      {
        id: "auto_generate",
        header: "Auto Generate",
        cell: ({ row }) => (
          <Badge variant={row.original.auto_generate ? "default" : "secondary"}>
            {row.original.auto_generate ? "On" : "Off"}
          </Badge>
        ),
      },
      {
        accessorKey: "prefix",
        header: "Prefix",
        cell: ({ row }) => (
          <code className="rounded bg-muted px-2 py-1 text-sm">
            {row.original.prefix || "—"}
          </code>
        ),
      },
      {
        id: "format_preview",
        header: "Format Preview",
        cell: ({ row }) => (
          <code className="text-sm text-muted-foreground">
            {buildFormatPreview(row.original)}
          </code>
        ),
      },
      {
        id: "actions",
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) =>
          canEdit ? (
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  navigate(`/settings/business-config/number-series/${row.original.entity_type}`)
                }
              >
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </Button>
            </div>
          ) : (
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  navigate(`/settings/business-config/number-series/${row.original.entity_type}`)
                }
              >
                View
              </Button>
            </div>
          ),
      },
    ],
    [navigate, canEdit]
  )

  // Empty state — error or empty data
  const showEmptyState = !isLoading && (isError || (!configs || configs.length === 0))

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Number Series"
        description="Configure how item codes and document numbers are generated for each entity type."
        action={
          <BusinessAssistantPanel
            config={numberSeriesListAssistant}
            triggerLabel="Business Assistant"
          />
        }
      />

      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : showEmptyState ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
          <AlertCircle className="h-10 w-10 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No configuration found</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-md">
            Number series configurations have not been initialized yet. Click below to
            seed the default configuration for all entity types.
          </p>
          <Button onClick={handleInitialize} disabled={initializing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${initializing ? "animate-spin" : ""}`} />
            {initializing ? "Initializing..." : "Initialize Default Configuration"}
          </Button>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={configs || []}
          searchKey="entity_type"
          searchPlaceholder="Search entity types..."
        />
      )}
    </div>
  )
}
