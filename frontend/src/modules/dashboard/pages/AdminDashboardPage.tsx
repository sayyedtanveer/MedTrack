/**
 * Admin Dashboard Page
 * Displays 8 cross-module KPI cards for ADMIN/TENANT_ADMIN roles:
 * - Pending Sales Orders
 * - Running Work Orders
 * - Delayed Work Orders
 * - QC Pending
 * - Low Stock Items
 * - Today's Dispatches
 * - Invoices Pending
 * - Payments Pending
 *
 * Each card shows value + trend indicator (vs 24h ago) and is clickable
 * to navigate to pre-filtered list pages. Auto-refreshes every 60 seconds.
 *
 * Full implementation tracked in task 12.1.
 * **Validates: Requirements 25.1–25.7**
 */

import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { KPICard, TrendDirection } from "@/components/shared/KPICard"
import { Button } from "@/components/ui/button"
import { RefreshCw, AlertTriangle } from "lucide-react"
import apiClient from "@/services/api-client"

interface AdminKPIData {
  pending_sales_orders: number
  running_work_orders: number
  delayed_work_orders: number
  qc_pending: number
  low_stock_items: number
  todays_dispatches: number
  invoices_pending: number
  payments_pending: number
  // Trend data (delta vs 24h ago, positive = up, negative = down)
  pending_sales_orders_trend?: number
  running_work_orders_trend?: number
  delayed_work_orders_trend?: number
  qc_pending_trend?: number
  low_stock_items_trend?: number
  todays_dispatches_trend?: number
  invoices_pending_trend?: number
  payments_pending_trend?: number
}

interface KPIConfig {
  title: string
  valueKey: keyof AdminKPIData
  trendKey: keyof AdminKPIData
  route: string
}

const kpiConfigs: KPIConfig[] = [
  {
    title: "Pending Sales Orders",
    valueKey: "pending_sales_orders",
    trendKey: "pending_sales_orders_trend",
    route: "/sales/orders?status=PENDING_APPROVAL",
  },
  {
    title: "Running Work Orders",
    valueKey: "running_work_orders",
    trendKey: "running_work_orders_trend",
    route: "/work-orders?status=IN_PRODUCTION",
  },
  {
    title: "Delayed Work Orders",
    valueKey: "delayed_work_orders",
    trendKey: "delayed_work_orders_trend",
    route: "/work-orders?filter=delayed",
  },
  {
    title: "QC Pending",
    valueKey: "qc_pending",
    trendKey: "qc_pending_trend",
    route: "/work-orders?status=QC_PENDING",
  },
  {
    title: "Low Stock Items",
    valueKey: "low_stock_items",
    trendKey: "low_stock_items_trend",
    route: "/inventory/materials?filter=low_stock",
  },
  {
    title: "Today's Dispatches",
    valueKey: "todays_dispatches",
    trendKey: "todays_dispatches_trend",
    route: "/delivery/dashboard",
  },
  {
    title: "Invoices Pending",
    valueKey: "invoices_pending",
    trendKey: "invoices_pending_trend",
    route: "/finance/invoices?status=DRAFT",
  },
  {
    title: "Payments Pending",
    valueKey: "payments_pending",
    trendKey: "payments_pending_trend",
    route: "/finance/invoices?status=PARTIAL",
  },
]

function getTrendDirection(trendValue: number | undefined): TrendDirection {
  if (trendValue === undefined || trendValue === 0) return "neutral"
  return trendValue > 0 ? "up" : "down"
}

function getTrendLabel(trendValue: number | undefined): string | undefined {
  if (trendValue === undefined || trendValue === 0) return undefined
  const prefix = trendValue > 0 ? "+" : ""
  return `${prefix}${trendValue} vs 24h ago`
}

export default function AdminDashboardPage() {
  const navigate = useNavigate()

  const { data, isLoading, isError, refetch, isFetching } = useQuery<AdminKPIData>({
    queryKey: ["admin-dashboard-kpis"],
    queryFn: async () => {
      const response = await apiClient.get("/reports/dashboard/kpis")
      return response.data
    },
    refetchInterval: 60_000, // Auto-refresh every 60 seconds
    retry: 1,
  })

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Admin Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">
            Cross-module KPIs and real-time operational metrics
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

      {isError && (
        <div className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span>Could not load dashboard data. Displaying last known values or empty state.</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {kpiConfigs.map((config) => {
          const value = isLoading ? "—" : (data?.[config.valueKey] ?? 0)
          const trendValue = data?.[config.trendKey] as number | undefined
          const trend = getTrendDirection(trendValue)
          const trendLabel = getTrendLabel(trendValue)

          return (
            <KPICard
              key={config.valueKey}
              title={config.title}
              value={value}
              trend={trend}
              trendLabel={trendLabel}
              onClick={() => navigate(config.route)}
            />
          )
        })}
      </div>
    </div>
  )
}
