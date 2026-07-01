import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { Settings2, Pencil } from "lucide-react"
import { numberSeriesService, NumberSeriesConfig } from "@/services/number-series.service"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

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

  const { data: configs, isLoading } = useQuery({
    queryKey: ["number-series-configs"],
    queryFn: () => numberSeriesService.listConfigs(),
  })

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
        cell: ({ row }) => (
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
        ),
      },
    ],
    [navigate]
  )

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Number Series"
        description="Configure how item codes and document numbers are generated for each entity type."
      />

      {isLoading ? (
        <TableSkeleton rows={6} />
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
