import { usePermissions } from "@/hooks/usePermissions"
import { useQuery } from "@tanstack/react-query"
import { reportsService } from "@/services/reports.service"
import { PageHeader } from "@/components/layout/PageHeader"
import { KPICard } from "../components/KPICard"
import { ActivityFeed } from "../components/ActivityFeed"
import { QuickActions } from "../components/QuickActions"
import { LowStockAlert } from "../components/LowStockAlert"
import { SetupChecklist } from "../components/SetupChecklist"
import { SetupProgressCard } from "../components/SetupProgressCard"
import { Skeleton } from "@/components/ui/skeleton"
import { MedTrackInbox } from "@/components/shared/assistant/MedTrackInbox"

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
    <div className="grid w-full items-start gap-6 relative">
      {/* Premium Background Elements */}
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-background to-background pointer-events-none" />
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
          <div className="animate-in fade-in slide-in-from-top-4 duration-500 delay-100 fill-mode-both">
            <MedTrackInbox />
          </div>

          <div className="animate-in fade-in slide-in-from-top-4 duration-500 delay-150 fill-mode-both">
            <LowStockAlert count={lowStockCount} />
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {data?.kpis.map((kpi, index) => (
              <div 
                key={index}
                className="animate-in fade-in slide-in-from-bottom-6 duration-700 fill-mode-both"
                style={{ animationDelay: `${200 + index * 100}ms` }}
              >
                <KPICard
                  data={kpi}
                  tone={(["primary", "secondary", "soft", "glass"] as const)[index % 4]}
                />
              </div>
            ))}
          </div>

          <div className="mt-2 grid grid-cols-1 gap-6 lg:grid-cols-2 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-500 fill-mode-both">
            <ActivityFeed activities={data?.recentActivities || []} />
            <div className="space-y-6">
              <SetupProgressCard />
              <QuickActions />
            </div>
          </div>

          {/* Setup Guide — Phase 0 (Number Series) first, visible to admins only (Gap #11) */}
          {isAdmin() && (
            <div className="mt-2 grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-bottom-10 duration-700 delay-700 fill-mode-both">
              <SetupChecklist />
            </div>
          )}
        </>
      )}
    </div>
  )
}
