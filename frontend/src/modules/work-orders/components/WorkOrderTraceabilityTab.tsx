import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/services/api"
import { DataTable } from "@/components/shared/DataTable"
import { ColumnDef } from "@tanstack/react-table"
import { Activity } from "lucide-react"

interface WOTraceabilityItem {
  material_id: string
  material_code: string
  material_name: string
  batch_id: string | null
  batch_number: string | null
  reserved_quantity: number | null
  issued_quantity: number | null
  consumed_quantity: number | null
  returned_quantity: number | null
  source: string | null
  created_at: string
}

export function WorkOrderTraceabilityTab({ workOrderId }: { workOrderId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["wo-traceability", workOrderId],
    queryFn: () => apiClient.get(`/inventory/traceability/work-order/${workOrderId}`).then((r: any) => r.data),
    enabled: Boolean(workOrderId),
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

  const items: WOTraceabilityItem[] = data?.items || []

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground rounded-2xl border border-slate-200/80 bg-white shadow-sm">
        <Activity className="h-10 w-10 mb-3 opacity-30" />
        <p className="text-sm font-medium">No traceability records found</p>
        <p className="text-xs mt-1">Material reservations or consumption for this work order will appear here.</p>
      </div>
    )
  }

  const columns: ColumnDef<WOTraceabilityItem>[] = [
    {
      accessorKey: "material_code",
      header: "Material Code",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.material_code}</span>,
    },
    {
      accessorKey: "material_name",
      header: "Material Name",
      cell: ({ row }) => <span className="text-sm">{row.original.material_name}</span>,
    },
    {
      accessorKey: "batch_number",
      header: "Batch / Lot",
      cell: ({ row }) => <span className="text-xs font-mono">{row.original.batch_number || "—"}</span>,
    },
    {
      accessorKey: "issued_quantity",
      header: "Issued",
      cell: ({ row }) => <span className="text-sm tabular-nums text-right block text-blue-600 font-medium">{Number(row.original.issued_quantity || 0).toFixed(3)}</span>,
    },
    {
      accessorKey: "consumed_quantity",
      header: "Consumed",
      cell: ({ row }) => <span className="text-sm tabular-nums text-right block text-emerald-600 font-medium">{Number(row.original.consumed_quantity || 0).toFixed(3)}</span>,
    },
    {
      accessorKey: "returned_quantity",
      header: "Returned",
      cell: ({ row }) => <span className="text-sm tabular-nums text-right block text-amber-600">{Number(row.original.returned_quantity || 0).toFixed(3)}</span>,
    },
  ]

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Material Traceability</h2>
        <p className="mt-1 text-xs text-slate-500">Track exact material batches issued, consumed, and returned.</p>
      </div>
      <DataTable columns={columns} data={items} />
    </div>
  )
}
