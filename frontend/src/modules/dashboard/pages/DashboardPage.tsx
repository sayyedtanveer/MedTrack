import { usePermissions } from "@/hooks/usePermissions"
import { useQuery } from "@tanstack/react-query"
import { reportsService } from "@/services/reports.service"
import { PageHeader } from "@/components/layout/PageHeader"
import { KPICard } from "../components/KPICard"
import { ActivityFeed } from "../components/ActivityFeed"
import { QuickActions } from "../components/QuickActions"
import { LowStockAlert } from "../components/LowStockAlert"
import { SetupChecklist } from "../components/SetupChecklist"
import { Skeleton } from "@/components/ui/skeleton"

export default function DashboardPage() {
  const { isAdmin } = usePermissions()
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-data"],
    queryFn: reportsService.getDashboard,
  })

  const lowStockKpi = data?.kpis.find((k) => k.label.includes("Low Stock"))
  const lowStockCount = lowStockKpi ? Number(lowStockKpi.value) : 0

  if (error) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center p-8 text-center bg-destructive/10 rounded-lg">
        <h2 className="text-xl font-semibold text-destructive mb-2">Failed to load dashboard</h2>
        <p className="text-muted-foreground">Please check your connection and try again.</p>
      </div>
    )
  }

  return (
    <div className="grid w-full items-start gap-6">
      <PageHeader 
        title="Dashboard" 
        description="Overview of your manufacturing and inventory operations."
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      ) : (
        <>
          <LowStockAlert count={lowStockCount} />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {data?.kpis.map((kpi, index) => (
              <KPICard
                key={index}
                data={kpi}
                tone={(["primary", "secondary", "soft", "glass"] as const)[index % 4]}
              />
            ))}
          </div>

          <div className="mt-2 grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ActivityFeed activities={data?.recentActivities || []} />
            <QuickActions />
          </div>

          {/* Setup Guide — Phase 0 (Number Series) first, visible to admins only (Gap #11) */}
          {isAdmin() && (
            <div className="mt-2 grid grid-cols-1 gap-4">
              <SetupChecklist />
            </div>
          )}
        </>
      )}
    </div>
  )
}
