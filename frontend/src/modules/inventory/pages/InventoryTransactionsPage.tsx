/**
 * Inventory Transactions Page
 * Displays paginated transaction list with filters and running balance calculation.
 * Also exported as InventoryTransactionsTab for embedding in Material Detail Page.
 * 
 * Requirements validated: 31.3, 31.4, 31.5, 31.8
 */

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ChevronLeft, ChevronRight, Filter, RefreshCw } from "lucide-react"
import apiClient from "@/services/api-client"
import { format } from "date-fns"

interface InventoryTransaction {
  id: string
  transaction_type: string
  quantity: number
  running_balance: number
  reference_type: string
  reference_id: string
  reference_number?: string
  material_id: string
  material_name: string
  material_code: string
  warehouse_name?: string
  user_name?: string
  timestamp: string
  notes?: string
}

interface TransactionListResponse {
  items: InventoryTransaction[]
  total: number
  limit: number
  offset: number
}

interface TransactionFilters {
  dateFrom?: string
  dateTo?: string
  transactionType?: string
  material?: string
  warehouse?: string
  referenceType?: string
}

const TRANSACTION_TYPE_COLORS: Record<string, string> = {
  RESERVATION: "bg-indigo-100 text-indigo-700",
  DISPATCH: "bg-teal-100 text-teal-700",
  FG_RECEIPT: "bg-green-100 text-green-700",
  MATERIAL_ISSUE: "bg-purple-100 text-purple-700",
  PURCHASE_RECEIPT: "bg-blue-100 text-blue-700",
  RESERVATION_RELEASE: "bg-orange-100 text-orange-700",
  DISPATCH_REVERSAL: "bg-red-100 text-red-700",
  SCRAP: "bg-gray-100 text-gray-700",
  ADJUSTMENT: "bg-yellow-100 text-yellow-700",
  OPENING_STOCK: "bg-slate-100 text-slate-700",
  PRODUCTION_CONSUMPTION: "bg-violet-100 text-violet-700",
  SALES_RETURN: "bg-emerald-100 text-emerald-700",
  TRANSFER: "bg-cyan-100 text-cyan-700",
}

const TRANSACTION_TYPES = [
  "RESERVATION",
  "DISPATCH",
  "FG_RECEIPT",
  "MATERIAL_ISSUE",
  "PURCHASE_RECEIPT",
  "RESERVATION_RELEASE",
  "DISPATCH_REVERSAL",
  "SCRAP",
  "ADJUSTMENT",
  "OPENING_STOCK",
  "PRODUCTION_CONSUMPTION",
  "SALES_RETURN",
  "TRANSFER",
]

const REFERENCE_TYPES = ["sales_order", "work_order", "delivery", "purchase_order", "adjustment"]

function getReferenceLink(type: string, id: string): string {
  const routes: Record<string, string> = {
    sales_order: `/sales/orders/${id}`,
    work_order: `/work-orders/${id}`,
    delivery: `/deliveries/${id}`,
    purchase_order: `/procurement/purchase-orders/${id}`,
  }
  return routes[type] || "#"
}

function formatTransactionType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

interface InventoryTransactionsContentProps {
  filters?: TransactionFilters
  onFiltersChange?: (filters: TransactionFilters) => void
  materialId?: string
  showFilters?: boolean
  title?: string
}

function InventoryTransactionsContent({
  filters: externalFilters,
  onFiltersChange,
  materialId,
  showFilters = true,
  title = "Inventory Transactions",
}: InventoryTransactionsContentProps) {
  const [internalFilters, setInternalFilters] = useState<TransactionFilters>({})
  const [currentPage, setCurrentPage] = useState(0)
  const limit = 50

  const filters = externalFilters ?? internalFilters
  const updateFilters = onFiltersChange ?? setInternalFilters

  const { data, isLoading, isError, refetch, isFetching } = useQuery<TransactionListResponse>({
    queryKey: ["inventory-transactions", materialId, filters, currentPage],
    queryFn: async () => {
      const params: any = {
        offset: currentPage * limit,
        limit,
      }
      if (materialId) params.material_id = materialId
      if (filters.dateFrom) params.date_from = filters.dateFrom
      if (filters.dateTo) params.date_to = filters.dateTo
      if (filters.transactionType) params.transaction_type = filters.transactionType
      if (filters.material) params.material = filters.material
      if (filters.warehouse) params.warehouse = filters.warehouse
      if (filters.referenceType) params.reference_type = filters.referenceType

      const response = await apiClient.get("/inventory/transactions", { params })
      return response.data
    },
    retry: 1,
  })

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
          {data && (
            <p className="mt-1 text-sm text-slate-500">
              Showing {data.items.length} of {data.total} transactions
            </p>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {showFilters && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Filter className="h-4 w-4" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-1">
                <Label htmlFor="date-from" className="text-xs">
                  Date From
                </Label>
                <Input
                  id="date-from"
                  type="date"
                  value={filters.dateFrom || ""}
                  onChange={(e) => updateFilters({ ...filters, dateFrom: e.target.value })}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="date-to" className="text-xs">
                  Date To
                </Label>
                <Input
                  id="date-to"
                  type="date"
                  value={filters.dateTo || ""}
                  onChange={(e) => updateFilters({ ...filters, dateTo: e.target.value })}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="transaction-type" className="text-xs">
                  Transaction Type
                </Label>
                <Select
                  value={filters.transactionType || "all"}
                  onValueChange={(value) =>
                    updateFilters({ ...filters, transactionType: value === "all" ? "" : value })
                  }
                >
                  <SelectTrigger id="transaction-type" className="h-9 text-sm">
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    {TRANSACTION_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {formatTransactionType(type)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {!materialId && (
                <div className="space-y-1">
                  <Label htmlFor="material" className="text-xs">
                    Material
                  </Label>
                  <Input
                    id="material"
                    type="text"
                    placeholder="Search material..."
                    value={filters.material || ""}
                    onChange={(e) => updateFilters({ ...filters, material: e.target.value })}
                    className="h-9 text-sm"
                  />
                </div>
              )}
              <div className="space-y-1">
                <Label htmlFor="warehouse" className="text-xs">
                  Warehouse
                </Label>
                <Input
                  id="warehouse"
                  type="text"
                  placeholder="Search warehouse..."
                  value={filters.warehouse || ""}
                  onChange={(e) => updateFilters({ ...filters, warehouse: e.target.value })}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="reference-type" className="text-xs">
                  Reference Type
                </Label>
                <Select
                  value={filters.referenceType || "all"}
                  onValueChange={(value) =>
                    updateFilters({ ...filters, referenceType: value === "all" ? "" : value })
                  }
                >
                  <SelectTrigger id="reference-type" className="h-9 text-sm">
                    <SelectValue placeholder="All References" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All References</SelectItem>
                    {REFERENCE_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {formatTransactionType(type)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Failed to load transactions. Please try again.
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[140px]">Date</TableHead>
                  <TableHead className="w-[160px]">Type</TableHead>
                  {!materialId && <TableHead>Material</TableHead>}
                  <TableHead className="text-right w-[100px]">Quantity</TableHead>
                  <TableHead>Reference</TableHead>
                  <TableHead>Warehouse</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead className="text-right w-[120px]">Running Balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={materialId ? 7 : 8} className="text-center py-8">
                      Loading transactions...
                    </TableCell>
                  </TableRow>
                ) : data?.items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={materialId ? 7 : 8} className="text-center py-8 text-slate-500">
                      No transactions found matching your filters
                    </TableCell>
                  </TableRow>
                ) : (
                  data?.items.map((txn) => (
                    <TableRow key={txn.id}>
                      <TableCell className="text-sm">
                        {format(new Date(txn.timestamp), "MMM dd, yyyy HH:mm")}
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={TRANSACTION_TYPE_COLORS[txn.transaction_type] || "bg-gray-100 text-gray-700"}
                        >
                          {formatTransactionType(txn.transaction_type)}
                        </Badge>
                      </TableCell>
                      {!materialId && (
                        <TableCell className="text-sm">
                          <div className="font-medium">{txn.material_code}</div>
                          <div className="text-xs text-slate-500">{txn.material_name}</div>
                        </TableCell>
                      )}
                      <TableCell className="text-right">
                        <span
                          className={`font-medium ${
                            txn.quantity > 0 ? "text-green-600" : "text-red-600"
                          }`}
                        >
                          {txn.quantity > 0 ? "+" : ""}
                          {txn.quantity.toLocaleString()}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        {txn.reference_type !== "adjustment" ? (
                          <Link
                            to={getReferenceLink(txn.reference_type, txn.reference_id)}
                            className="text-blue-600 hover:underline"
                          >
                            {txn.reference_number || txn.reference_id}
                          </Link>
                        ) : (
                          <span className="text-slate-500">Manual Adjustment</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">
                        {txn.warehouse_name || "—"}
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">{txn.user_name || "—"}</TableCell>
                      <TableCell className="text-right font-medium">
                        {txn.running_balance.toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-600">
            Page {currentPage + 1} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0 || isFetching}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1 || isFetching}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// Main page export
export default function InventoryTransactionsPage() {
  return (
    <div className="p-6">
      <InventoryTransactionsContent />
    </div>
  )
}

// Named export for embedding in Material Detail Page
export function InventoryTransactionsTab({ materialId }: { materialId: string }) {
  return (
    <div className="py-4">
      <InventoryTransactionsContent
        materialId={materialId}
        showFilters={true}
        title="Transaction History"
      />
    </div>
  )
}
