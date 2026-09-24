import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/services/api"
import { DataTable } from "@/components/shared/DataTable"
import { ColumnDef } from "@tanstack/react-table"
import { Link } from "react-router-dom"
import { Activity } from "lucide-react"

interface TraceabilityItem {
  transaction_id: string
  transaction_type: string
  material_code: string
  material_name: string
  quantity: number
  unit_id: string
  batch_id: string | null
  batch_number: string | null
  reference_type: string | null
  reference_id: string | null
  wo_number: string | null
  finished_product_name: string | null
  reserved_quantity: number | null
  issued_quantity: number | null
  consumed_quantity: number | null
  returned_quantity: number | null
  created_at: string
  created_by: string
  remarks: string | null
  status: string | null
}

export function MaterialTraceabilityTab({ materialId }: { materialId: string }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["material-traceability", materialId],
    queryFn: () => apiClient.get(`/inventory/traceability/material/${materialId}`).then((r: any) => r.data),
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

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-red-500">
        <Activity className="h-10 w-10 mb-3 opacity-30" />
        <p className="text-sm font-medium">Failed to load traceability data.</p>
        <p className="text-xs mt-1 text-slate-500">{(error as any)?.message || "An unexpected API error occurred."}</p>
      </div>
    )
  }

  const items: TraceabilityItem[] = data?.items || []

  const woItems = items;

  if (woItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
        <Activity className="h-10 w-10 mb-3 opacity-30" />
        <p className="text-sm font-medium">No Work Orders have consumed this material yet.</p>
      </div>
    )
  }

  const columns: ColumnDef<TraceabilityItem>[] = [
    {
      accessorKey: "wo_number",
      header: "Work Order",
      cell: ({ row }) => {
        if (row.original.reference_type === "work_order" && row.original.reference_id) {
          return (
            <Link
              to={`/manufacturing/work-orders?id=${row.original.reference_id}`}
              className="text-primary hover:underline font-medium font-mono text-sm"
              onClick={(e) => e.stopPropagation()}
            >
              {row.original.wo_number}
            </Link>
          )
        }
        return <span className="text-sm">{row.original.reference_id}</span>
      },
    },
    {
      accessorKey: "finished_product_name",
      header: "Product",
      cell: ({ row }) => <span className="text-sm truncate max-w-[200px] inline-block" title={row.original.finished_product_name || ""}>{row.original.finished_product_name || "—"}</span>,
    },
    {
      accessorKey: "batch_number",
      header: "Batch / Lot",
      cell: ({ row }) => <span className="text-xs font-mono">{row.original.batch_number || "—"}</span>,
    },
    {
      accessorKey: "quantity",
      header: "Consumed Qty",
      cell: ({ row }) => <span className="text-sm tabular-nums text-right block">{row.original.quantity}</span>,
    },
    {
      accessorKey: "created_at",
      header: "Consumption Date",
      cell: ({ row }) => (
        <span className="text-xs whitespace-nowrap">
          {new Date(row.original.created_at).toLocaleDateString("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
          })}
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {row.original.status || "—"}
        </span>
      )
    }
  ]

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground mb-4">
        Showing all Work Orders where this material was consumed.
      </p>
      <div className="border rounded-md bg-white">
        <DataTable columns={columns} data={woItems} searchKey="batch_number" searchPlaceholder="Filter by batch..." />
      </div>
    </div>
  )
}
