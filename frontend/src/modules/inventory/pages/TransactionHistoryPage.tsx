import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"
import { materialService } from "@/services/material.service"
import { InventoryTransaction } from "@/types/material.types"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { ColumnDef } from "@tanstack/react-table"
import { ArrowDownToLine, ArrowUpToLine, Replace } from "lucide-react"

export default function TransactionHistoryPage() {
  const { data: transactions, isLoading } = useQuery({
    queryKey: ["transactions"],
    queryFn: () => materialService.getTransactions({ page: 1, page_size: 200 }),
  })

  const { data: materialsData } = useQuery({
    queryKey: ["materials", "transaction-history"],
    queryFn: () => materialService.getMaterials({ page: 1, page_size: 500 }),
  })

  const materialLookup = useMemo(() => {
    return new Map((materialsData?.items || []).map((material) => [material.id, material]))
  }, [materialsData])

  // Define columns for TanStack Table
  const columns = useMemo<ColumnDef<InventoryTransaction>[]>(() => [
    {
      accessorKey: "created_at",
      header: "Date / Time",
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return <span className="text-sm font-medium">{date.toLocaleString()}</span>;
      },
    },
    {
      accessorKey: "transaction_type",
      header: "Type",
      cell: ({ row }) => {
        const type = row.original.transaction_type;
        const inTypes = ["in", "OPENING_STOCK", "PURCHASE_RECEIPT", "FG_RECEIPT", "RECEIPT_REVERSAL", "SALES_RETURN", "DISPATCH_REVERSAL"];
        const outTypes = ["out", "MATERIAL_ISSUE", "PROD_CONSUMPTION", "DISPATCH", "SCRAP"];
        const holdTypes = ["RESERVATION"];
        const releaseTypes = ["RESERVATION_RELEASE"];
        
        let label = type.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
        if (type === "in") label = "Stock In";
        if (type === "out") label = "Stock Out";
        
        if (inTypes.includes(type) || releaseTypes.includes(type)) return <span className="inline-flex items-center text-green-600 bg-green-50 px-2 py-1 rounded text-xs font-semibold"><ArrowDownToLine className="w-3 h-3 mr-1"/> {label}</span>;
        if (outTypes.includes(type)) return <span className="inline-flex items-center text-red-600 bg-red-50 px-2 py-1 rounded text-xs font-semibold"><ArrowUpToLine className="w-3 h-3 mr-1"/> {label}</span>;
        if (type === "adjustment") return <span className="inline-flex items-center text-blue-600 bg-blue-50 px-2 py-1 rounded text-xs font-semibold"><Replace className="w-3 h-3 mr-1"/> Adjustment</span>;
        if (type === "transfer") return <span className="inline-flex items-center text-purple-600 bg-purple-50 px-2 py-1 rounded text-xs font-semibold"><Replace className="w-3 h-3 mr-1"/> Transfer</span>;
        if (holdTypes.includes(type)) return <span className="inline-flex items-center text-amber-600 bg-amber-50 px-2 py-1 rounded text-xs font-semibold"><ArrowUpToLine className="w-3 h-3 mr-1"/> {label}</span>;
        
        return <span className="inline-flex items-center text-gray-600 bg-gray-50 px-2 py-1 rounded text-xs font-semibold">{type}</span>;
      },
    },
    {
      accessorKey: "material_id",
      header: "Item",
      cell: ({ row }) => {
        const material = materialLookup.get(row.original.material_id)
        return (
          <div>
            <p className="font-medium">{material?.code || "Unknown item"}</p>
            <p className="text-xs text-muted-foreground">{material?.name || "Material no longer available"}</p>
          </div>
        )
      },
    },
    {
      accessorKey: "quantity",
      header: "Quantity",
      cell: ({ row }) => {
        const type = row.original.transaction_type;
        const inTypes = ["in", "OPENING_STOCK", "PURCHASE_RECEIPT", "FG_RECEIPT", "RECEIPT_REVERSAL", "SALES_RETURN", "DISPATCH_REVERSAL", "RESERVATION_RELEASE"];
        const outTypes = ["out", "MATERIAL_ISSUE", "PROD_CONSUMPTION", "DISPATCH", "SCRAP", "RESERVATION"];
        
        let color = "text-blue-600";
        let sign = "";
        
        if (inTypes.includes(type)) { color = "text-green-600"; sign = "+"; }
        else if (outTypes.includes(type)) { color = "text-red-600"; sign = "-"; }
        else if (type === "adjustment") { color = "text-blue-600"; }
        
        return <span className={`font-mono font-bold ${color}`}>{sign}{row.original.quantity}</span>;
      },
    },
    {
      accessorKey: "remarks",
      header: "Remarks",
      cell: ({ row }) => <span className="text-sm text-muted-foreground truncate max-w-[200px] inline-block" title={row.original.remarks || ""}>{row.original.remarks || "-"}</span>,
    },
  ], [materialLookup])


  return (
    <div className="w-full space-y-6">
      <PageHeader 
        title="Transaction History" 
        description="Immutable audit log of all stock movements and adjustments."
      />

      {isLoading ? (
        <TableSkeleton rows={15} />
      ) : (
        <div className="bg-card border rounded-lg overflow-hidden">
          <DataTable 
            columns={columns} 
            data={transactions || []} 
            searchKey="remarks" 
            searchPlaceholder="Search by remarks..."
          />
        </div>
      )}
    </div>
  )
}
