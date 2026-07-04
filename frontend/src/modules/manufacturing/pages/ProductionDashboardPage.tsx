/**
 * Production Dashboard Page
 * Displays real-time production KPIs: running WOs, completed today,
 * delayed WOs, QC queue, material shortages, and production output.
 * 
 * Enhanced with date range, product, and work center filters.
 * 
 * Full implementation tracked in task 12.2.
 * **Validates: Requirements 22.1–22.8**
 */

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Factory, AlertTriangle, CheckCircle2, Clock, RefreshCw } from "lucide-react"
import { apiClient } from "@/services/api-client"

interface ProductionDashboardData {
  running_work_orders: number
  completed_today: number
  delayed_work_orders: number
  qc_queue: number
  material_shortages: number
  produced_today: number
  planned_today: number
}

export default function ProductionDashboardPage() {
  const navigate = useNavigate()

  // Date range defaults to today
  const today = new Date().toISOString().split("T")[0]
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(today)
  const [productFilter, setProductFilter] = useState("")
  const [workCenterFilter, setWorkCenterFilter] = useState("")

  const { data, isLoading, isError, refetch, isFetching } = useQuery<ProductionDashboardData>({
    queryKey: ["production-dashboard", dateFrom, dateTo, productFilter, workCenterFilter],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      if (productFilter) params.product = productFilter
      if (workCenterFilter) params.work_center = workCenterFilter

      const response = await apiClient.get("/reports/production/dashboard", { params })
      return response.data
    },
    refetchInterval: 60_000,
    retry: 1,
  })

  const outputPercent =
    data && data.planned_today > 0
      ? Math.round((data.produced_today / data.planned_today) * 100)
      : 0

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Production Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Real-time manufacturing KPIs and work order status</p>
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

      {/* Filter Controls */}
      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="space-y-1">
          <Label htmlFor="date-from" className="text-xs font-medium text-slate-600">
            From
          </Label>
          <Input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-8 w-40 text-sm"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="date-to" className="text-xs font-medium text-slate-600">
            To
          </Label>
          <Input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-8 w-40 text-sm"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="product-filter" className="text-xs font-medium text-slate-600">
            Product
          </Label>
          <Input
            id="product-filter"
            type="text"
            placeholder="Product name/code"
            value={productFilter}
            onChange={(e) => setProductFilter(e.target.value)}
            className="h-8 w-48 text-sm"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="work-center-filter" className="text-xs font-medium text-slate-600">
            Work Center
          </Label>
          <Input
            id="work-center-filter"
            type="text"
            placeholder="Work center"
            value={workCenterFilter}
            onChange={(e) => setWorkCenterFilter(e.target.value)}
            className="h-8 w-48 text-sm"
          />
        </div>
        <Button size="sm" onClick={() => refetch()} disabled={isFetching}>
          Apply
        </Button>
      </div>

      {isError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Could not load dashboard data. Displaying last known values or empty state.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Running Work Orders */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/work-orders?status=IN_PRODUCTION")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Factory className="h-4 w-4 text-blue-500" />
              Running Work Orders
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">
              {isLoading ? "—" : (data?.running_work_orders ?? 0)}
            </p>
            <p className="mt-1 text-xs text-slate-500">Currently in production</p>
          </CardContent>
        </Card>

        {/* Completed Today */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/work-orders?status=COMPLETED")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              Completed Today
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">
              {isLoading ? "—" : (data?.completed_today ?? 0)}
            </p>
            <p className="mt-1 text-xs text-slate-500">Work orders finished today</p>
          </CardContent>
        </Card>

        {/* Delayed Work Orders */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/work-orders?filter=delayed")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-red-500" />
              Delayed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.delayed_work_orders ?? 0)}
              </p>
              {!isLoading && (data?.delayed_work_orders ?? 0) > 0 && (
                <Badge variant="destructive" className="text-xs">Overdue</Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500">Past due date</p>
          </CardContent>
        </Card>

        {/* QC Queue */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/work-orders?status=QC_PENDING")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              QC Queue
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">
              {isLoading ? "—" : (data?.qc_queue ?? 0)}
            </p>
            <p className="mt-1 text-xs text-slate-500">Pending quality inspection</p>
          </CardContent>
        </Card>

        {/* Material Shortages */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/work-orders?status=MATERIAL_PENDING")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              Material Shortages
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.material_shortages ?? 0)}
              </p>
              {!isLoading && (data?.material_shortages ?? 0) > 0 && (
                <Badge className="bg-orange-100 text-orange-700 text-xs">Blocked</Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500">WOs waiting for materials</p>
          </CardContent>
        </Card>

        {/* Production Output */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Factory className="h-4 w-4 text-violet-500" />
              Production Output
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">
              {isLoading ? "—" : `${outputPercent}%`}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {isLoading
                ? "Loading..."
                : `${data?.produced_today ?? 0} produced / ${data?.planned_today ?? 0} planned`}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate("/reports/manufacturing-kpis")}>
          View Manufacturing KPIs
        </Button>
        <Button variant="outline" onClick={() => navigate("/work-orders")}>
          All Work Orders
        </Button>
      </div>
    </div>
  )
}
