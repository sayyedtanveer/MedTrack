import { useAuthStore } from "@/app/store/authStore"
import { DashboardReport, KPIData, ActivityItem } from "@/types/inventory.types"
import { apiClient } from "./api-client"

const roleDashboardPath: Record<string, string> = {
  ADMIN: "/dashboards/admin",
  TENANT_ADMIN: "/dashboards/admin",
  MANAGER: "/dashboards/manager",
  PLANNER: "/dashboards/planner",
  STOREKEEPER: "/dashboards/storekeeper",
  OPERATOR: "/dashboards/storekeeper",
  SALES: "/dashboards/sales",
  QC: "/dashboards/qc",
  WORKER: "/dashboards/worker",
  CLIENT: "/dashboards/client",
  SUPPLIER: "/dashboards/supplier",
}

function kpi(label: string, value: number | string, trend: KPIData["trend"] = "neutral", change = 0): KPIData {
  return { label, value, trend, change }
}

function countStatuses(statuses: Record<string, number> | undefined, keys: string[]) {
  if (!statuses) return 0
  return keys.reduce((total, key) => total + Number(statuses[key] ?? statuses[key.toLowerCase()] ?? 0), 0)
}

function mapRoleDashboard(data: any, role: string): KPIData[] {
  const normalizedRole = role.toUpperCase()

  if (normalizedRole === "ADMIN" || normalizedRole === "TENANT_ADMIN") {
    return [
      kpi("Open Orders", Number(data.open_orders ?? 0)),
      kpi("Open Work Orders", Number(data.open_work_orders ?? 0)),
      kpi("Low Stock Alerts", Number(data.inventory?.low_stock_alerts ?? 0), Number(data.inventory?.low_stock_alerts ?? 0) > 0 ? "down" : "neutral"),
      kpi("Revenue", Number(data.revenue ?? 0)),
    ]
  }

  if (normalizedRole === "MANAGER") {
    return [
      kpi("Pending Approvals", Number(data.pending_orders?.count ?? 0)),
      kpi("Orders in Execution", Number(data.orders_in_execution ?? 0)),
      kpi("Approval Queue", Number(data.pending_orders?.items?.length ?? 0)),
      kpi("Manager Actions", Number(data.pending_orders?.count ?? 0)),
    ]
  }

  if (normalizedRole === "PLANNER") {
    return [
      kpi("Open Work Orders", Number(data.open_work_orders ?? 0)),
      kpi("Capacity Load", `${Number(data.capacity_load ?? 0).toFixed(1)}%`),
      kpi("Shortage Items", Number(data.mrp_suggestions?.shortage_items ?? 0), Number(data.mrp_suggestions?.shortage_items ?? 0) > 0 ? "down" : "neutral"),
      kpi("Open POs", Number(data.mrp_suggestions?.open_purchase_orders ?? 0)),
    ]
  }

  if (normalizedRole === "STOREKEEPER" || normalizedRole === "OPERATOR") {
    return [
      kpi("Pending GRNs", Number(data.grn_pending ?? 0)),
      kpi("Low Stock Alerts", Number(data.low_stock_alerts?.count ?? 0), Number(data.low_stock_alerts?.count ?? 0) > 0 ? "down" : "neutral"),
      kpi("Inventory Value", Number(data.inventory?.total_value ?? 0)),
      kpi("Open POs", Number(data.open_purchase_orders ?? 0)),
    ]
  }

  if (normalizedRole === "SALES") {
    return [
      kpi("Pending Approvals", Number(data.pending_approvals ?? 0)),
      kpi("Monthly Sales", Number(data.monthly_sales ?? 0)),
      kpi("Top Clients", Number(data.top_clients?.length ?? 0)),
      kpi("Sales Actions", Number(data.pending_approvals ?? 0)),
    ]
  }

  if (normalizedRole === "QC") {
    return [
      kpi("Pending Inspections", Number(data.pending_inspections ?? 0)),
      kpi("NCRs This Month", Number(data.ncrs_this_month ?? 0), Number(data.ncrs_this_month ?? 0) > 0 ? "down" : "neutral"),
      kpi("Passed Inspections", Number(data.inspections?.passed ?? data.inspections?.PASSED ?? 0)),
      kpi("Failed Inspections", Number(data.inspections?.failed ?? data.inspections?.FAILED ?? 0), Number(data.inspections?.failed ?? data.inspections?.FAILED ?? 0) > 0 ? "down" : "neutral"),
    ]
  }

  if (normalizedRole === "WORKER") {
    return [
      kpi("Ready to Start", Number(data.ready_to_start ?? 0)),
      kpi("In Progress", Number(data.in_progress ?? 0)),
      kpi("Recent Work Orders", Number(data.recent_work_orders?.length ?? 0)),
      kpi("Open Work Orders", countStatuses(data.work_orders, ["PLANNED", "RELEASED", "MATERIAL_PENDING", "MATERIAL_RESERVED", "MATERIAL_ISSUED", "IN_PRODUCTION"])),
    ]
  }

  if (normalizedRole === "SUPPLIER") {
    return [
      kpi("Purchase Orders", Number(data.purchase_orders?.total ?? 0)),
      kpi("Quotations", Number(data.quotations?.total ?? 0)),
      kpi("Pending Action", Number(data.quotations?.pending_action ?? 0)),
      kpi("Performance Rating", data.performance?.rating ?? "N/A"),
    ]
  }

  if (normalizedRole === "CLIENT") {
    return [
      kpi("Pending Delivery", Number(data.pending_delivery ?? 0)),
      kpi("Shipped Orders", Number(data.shipped ?? 0)),
      kpi("Recent Orders", Number(data.recent_orders?.length ?? 0)),
      kpi("Open Orders", countStatuses(data.sales_orders, ["DRAFT", "PENDING_APPROVAL", "CONFIRMED", "READY", "SHIPPED"])),
    ]
  }

  return []
}

function mapFinanceDashboard(data: any): KPIData[] {
  return [
    kpi("Total Billed", Number(data.ar?.total_billed ?? 0)),
    kpi("Collected", Number(data.ar?.total_collected ?? 0)),
    kpi("Outstanding AR", Number(data.ar?.total_outstanding ?? 0), Number(data.ar?.total_outstanding ?? 0) > 0 ? "down" : "neutral"),
    kpi("Outstanding AP", Number(data.ap?.outstanding ?? 0), Number(data.ap?.outstanding ?? 0) > 0 ? "down" : "neutral"),
  ]
}

async function getViewerDashboard(): Promise<KPIData[]> {
  const [inventory, sales] = await Promise.all([
    apiClient.get("/reports/inventory/summary").then((res) => res.data),
    apiClient.get("/reports/sales/summary").then((res) => res.data),
  ])

  return [
    kpi("Inventory Items", Number(inventory.total_items ?? inventory.items?.length ?? 0)),
    kpi("Low Stock Alerts", Number(inventory.low_stock_count ?? inventory.low_stock_items?.length ?? 0), Number(inventory.low_stock_count ?? 0) > 0 ? "down" : "neutral"),
    kpi("Sales Orders", Number(sales.total_orders ?? 0)),
    kpi("Sales Value", Number(sales.total_sales ?? sales.monthly_total ?? 0)),
  ]
}

async function getRecentActivities(): Promise<ActivityItem[]> {
  const response = await apiClient.get("/notifications/", { params: { page_size: 10 } })
  const items = Array.isArray(response.data?.items) ? response.data.items : []

  return items.map((item: any) => ({
    id: String(item.id),
    type: item.type?.includes("LOW_STOCK") ? "alert" : "system",
    description: `${item.title}: ${item.message}`,
    timestamp: item.sent_at,
  }))
}

export const reportsService = {
  async getDashboard(): Promise<DashboardReport> {
    const role = useAuthStore.getState().user?.role?.toUpperCase() || "VIEWER"
    const kpis =
      role === "ACCOUNTANT"
        ? mapFinanceDashboard((await apiClient.get("/finance/dashboard")).data)
        : role === "VIEWER"
          ? await getViewerDashboard()
          : mapRoleDashboard((await apiClient.get(roleDashboardPath[role] || "/dashboards/admin")).data, role)

    const recentActivities = await getRecentActivities().catch(() => [])
    return { kpis, recentActivities }
  },
}
