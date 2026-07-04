/**
 * Manufacturing KPIs Page
 * Displays OEE, yield rate, scrap rate, rework rate, and inventory turnover
 * with date range filter, product/work center filters, and report sub-sections.
 *
 * Requirements validated: 15.1–15.8, 32.1–32.10
 */

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { BarChart3, RefreshCw, TrendingUp, TrendingDown, Minus, FileText } from "lucide-react"
import apiClient from "@/services/api-client"

interface ManufacturingKPIs {
  oee_percent: number
  yield_rate_percent: number
  scrap_rate_percent: number
  rework_rate_percent: number
  inventory_turnover: number
  date_from: string
  date_to: string
}

function TrendIcon({ value, threshold = 0 }: { value: number; threshold?: number }) {
  if (value > threshold) return <TrendingUp className="h-4 w-4 text-emerald-500" />
  if (value < threshold) return <TrendingDown className="h-4 w-4 text-red-500" />
  return <Minus className="h-4 w-4 text-slate-400" />
}

export default function ManufacturingKPIsPage() {
  const today = new Date()
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)

  const [dateFrom, setDateFrom] = useState(firstOfMonth.toISOString().split("T")[0])
  const [dateTo, setDateTo] = useState(today.toISOString().split("T")[0])
  const [productFilter, setProductFilter] = useState("")
  const [workCenterFilter, setWorkCenterFilter] = useState("")

  const { data, isLoading, isError, refetch, isFetching } = useQuery<ManufacturingKPIs>({
    queryKey: ["manufacturing-kpis", dateFrom, dateTo, productFilter, workCenterFilter],
    queryFn: async () => {
      const params: any = { date_from: dateFrom, date_to: dateTo }
      if (productFilter) params.product_id = productFilter
      if (workCenterFilter) params.work_center = workCenterFilter
      
      const response = await apiClient.get("/reports/manufacturing-kpis", { params })
      return response.data
    },
    retry: 1,
  })

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Manufacturing KPIs</h1>
          <p className="mt-1 text-sm text-slate-500">
            OEE, yield, scrap, rework rate, and inventory turnover
          </p>
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
      <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="space-y-1">
            <Label htmlFor="date-from" className="text-xs font-medium text-slate-600">From</Label>
            <Input
              id="date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="h-8 w-40 text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="date-to" className="text-xs font-medium text-slate-600">To</Label>
            <Input
              id="date-to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="h-8 w-40 text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="product-filter" className="text-xs font-medium text-slate-600">Product</Label>
            <Input
              id="product-filter"
              type="text"
              placeholder="Search product..."
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
              className="h-8 w-48 text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="work-center-filter" className="text-xs font-medium text-slate-600">Work Center</Label>
            <Input
              id="work-center-filter"
              type="text"
              placeholder="Search work center..."
              value={workCenterFilter}
              onChange={(e) => setWorkCenterFilter(e.target.value)}
              className="h-8 w-48 text-sm"
            />
          </div>
          <Button size="sm" onClick={() => refetch()} disabled={isFetching}>
            Apply
          </Button>
        </div>
        
        {/* Record count and date range display */}
        {data && !isLoading && (
          <p className="text-xs text-slate-600">
            Showing data for {dateFrom} – {dateTo}
          </p>
        )}
      </div>

      {/* Report Sub-sections Navigation */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <FileText className="h-4 w-4" />
            Detailed Reports
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Link to="/reports/production/cycle-time">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3" size="sm">
                <BarChart3 className="h-4 w-4" />
                <div className="text-left">
                  <div className="font-medium">Cycle Time Report</div>
                  <div className="text-xs text-slate-500">Time per product</div>
                </div>
              </Button>
            </Link>
            <Link to="/reports/production/qc-rate">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3" size="sm">
                <BarChart3 className="h-4 w-4" />
                <div className="text-left">
                  <div className="font-medium">QC Pass/Fail Report</div>
                  <div className="text-xs text-slate-500">Quality metrics</div>
                </div>
              </Button>
            </Link>
            <Link to="/reports/production/output">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3" size="sm">
                <BarChart3 className="h-4 w-4" />
                <div className="text-left">
                  <div className="font-medium">Production Output Report</div>
                  <div className="text-xs text-slate-500">Produced vs planned</div>
                </div>
              </Button>
            </Link>
            <Link to="/reports/production/material-variance">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3" size="sm">
                <BarChart3 className="h-4 w-4" />
                <div className="text-left">
                  <div className="font-medium">Material Variance Report</div>
                  <div className="text-xs text-slate-500">Planned vs actual</div>
                </div>
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {isError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Could not load KPI data. Please try refreshing or adjusting the date range.
        </div>
      )}

      {!isLoading && !isError && data && (data.oee_percent === 0 && data.yield_rate_percent === 0) && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 text-center">
          No data found for the selected date range and filters
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* OEE */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-500" />
              OEE
            </CardDescription>
            <CardTitle className="text-sm text-slate-500">Overall Equipment Effectiveness</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : `${data?.oee_percent?.toFixed(1) ?? 0}%`}
              </p>
              {!isLoading && data && <TrendIcon value={data.oee_percent} threshold={85} />}
            </div>
            <div className="mt-2">
              {!isLoading && data && (
                <Badge
                  className={
                    data.oee_percent >= 85
                      ? "bg-emerald-100 text-emerald-700"
                      : data.oee_percent >= 65
                        ? "bg-amber-100 text-amber-700"
                        : "bg-red-100 text-red-700"
                  }
                >
                  {data.oee_percent >= 85 ? "World Class" : data.oee_percent >= 65 ? "Average" : "Below Target"}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Yield Rate */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-500" />
              Yield Rate
            </CardDescription>
            <CardTitle className="text-sm text-slate-500">Good units / Total produced</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : `${data?.yield_rate_percent?.toFixed(1) ?? 0}%`}
              </p>
              {!isLoading && data && <TrendIcon value={data.yield_rate_percent} threshold={95} />}
            </div>
          </CardContent>
        </Card>

        {/* Scrap Rate */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-red-500" />
              Scrap Rate
            </CardDescription>
            <CardTitle className="text-sm text-slate-500">Scrapped / Total produced</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : `${data?.scrap_rate_percent?.toFixed(1) ?? 0}%`}
              </p>
              {!isLoading && data && (
                <Badge
                  className={
                    (data.scrap_rate_percent ?? 0) <= 2
                      ? "bg-emerald-100 text-emerald-700"
                      : (data.scrap_rate_percent ?? 0) <= 5
                        ? "bg-amber-100 text-amber-700"
                        : "bg-red-100 text-red-700"
                  }
                >
                  {(data.scrap_rate_percent ?? 0) <= 2 ? "Good" : (data.scrap_rate_percent ?? 0) <= 5 ? "Monitor" : "High"}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Rework Rate */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-orange-500" />
              Rework Rate
            </CardDescription>
            <CardTitle className="text-sm text-slate-500">Rework count / Completed WOs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : `${data?.rework_rate_percent?.toFixed(1) ?? 0}%`}
              </p>
              {!isLoading && data && (
                <Badge
                  className={
                    (data.rework_rate_percent ?? 0) <= 3
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-amber-100 text-amber-700"
                  }
                >
                  {(data.rework_rate_percent ?? 0) <= 3 ? "Good" : "High"}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Inventory Turnover */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-violet-500" />
              Inventory Turnover
            </CardDescription>
            <CardTitle className="text-sm text-slate-500">COGS / Average inventory value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.inventory_turnover?.toFixed(2) ?? "—")}
              </p>
              {!isLoading && data && <TrendIcon value={data.inventory_turnover} threshold={4} />}
            </div>
            <p className="mt-1 text-xs text-slate-500">turns per period</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
