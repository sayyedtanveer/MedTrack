import { usePlatformTenants } from "../hooks/usePlatformTenants"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { TenantStatusBadge } from "../components/TenantStatusBadge"
import { TenantActionMenu } from "../components/TenantActionMenu"
import { DashboardStatsSkeleton } from "../components/PlatformSkeletons"
import { AllClearEmptyState } from "../components/EmptyStates"
import { formatDistanceToNow } from "date-fns"
import { Building, Clock, Ban, Archive, Activity } from "lucide-react"

export default function PlatformDashboard() {
  const { data, isLoading } = usePlatformTenants()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Berynx Platform Console</h1>
        <DashboardStatsSkeleton />
      </div>
    )
  }

  const tenants = data?.tenants || []
  
  // Calculate stats MVP
  const pending = tenants.filter(t => t.status === "pending").length
  const active = tenants.filter(t => t.status === "active").length
  const suspended = tenants.filter(t => t.status === "suspended").length
  const archived = tenants.filter(t => t.status === "archived").length

  const needsAttention = tenants.filter(t => t.status === "pending" || t.status === "suspended")

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">MedTrack Platform Console</h1>
        <p className="mt-2 text-muted-foreground">
          Overview of your platform health, active workspaces, and pending actions.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Pending Approvals" value={pending} icon={Clock} valueClass="text-amber-600 dark:text-amber-500" />
        <StatCard title="Suspended Tenants" value={suspended} icon={Ban} valueClass="text-rose-600 dark:text-rose-500" />
        <StatCard title="Active Tenants" value={active} icon={Building} />
        <StatCard title="Archived" value={archived} icon={Archive} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="col-span-1 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-amber-500" />
              Needs Attention
            </CardTitle>
            <CardDescription>
              Workspaces requiring manual intervention or review.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {needsAttention.length === 0 ? (
              <AllClearEmptyState />
            ) : (
              <div className="space-y-4">
                {needsAttention.map((tenant) => (
                  <div key={tenant.id} className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between transition-colors hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-slate-900 dark:text-slate-100">{tenant.name}</h4>
                        <TenantStatusBadge status={tenant.status} />
                      </div>
                      <p className="mt-1 text-sm text-slate-500">
                        {tenant.status === "pending" ? (
                          `Registered ${formatDistanceToNow(new Date(tenant.created_at))} ago`
                        ) : (
                          "Suspended. Manual reactivation required."
                        )}
                      </p>
                    </div>
                    <div className="mt-2 sm:mt-0">
                      <TenantActionMenu tenant={tenant} variant="buttons" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="col-span-1 shadow-sm">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest tenant lifecycle events and changes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Future Placeholder for real audit events */}
            <div className="space-y-6">
              {tenants.slice(0, 5).map((tenant) => (
                <div key={tenant.id} className="flex gap-4">
                  <div className="mt-0.5 relative">
                    <div className="h-2 w-2 rounded-full bg-slate-300 dark:bg-slate-700 ring-4 ring-slate-100 dark:ring-slate-950" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                      {tenant.name} {tenant.status === "active" ? "registered" : `was ${tenant.status}`}
                    </p>
                    <p className="text-xs text-slate-500">
                      {formatDistanceToNow(new Date(tenant.created_at))} ago
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon: Icon, valueClass = "text-slate-900 dark:text-slate-50" }: any) {
  return (
    <Card className="shadow-sm transition-all hover:shadow-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${valueClass}`}>{value}</div>
      </CardContent>
    </Card>
  )
}
