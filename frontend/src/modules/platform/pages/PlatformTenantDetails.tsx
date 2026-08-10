import { useMemo } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { usePlatformTenants } from "../hooks/usePlatformTenants"
import { TenantStatusBadge } from "../components/TenantStatusBadge"
import { TenantActionMenu } from "../components/TenantActionMenu"
import { TenantDetailsSkeleton } from "../components/PlatformSkeletons"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { format, formatDistanceToNow } from "date-fns"
import { ArrowLeft, Building, User, Globe, CreditCard, Calendar } from "lucide-react"

export default function PlatformTenantDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { data, isLoading } = usePlatformTenants()

  const tenant = useMemo(() => {
    return data?.tenants.find(t => t.id === id)
  }, [data, id])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="-ml-3 h-8 text-muted-foreground">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Tenants
        </Button>
        <TenantDetailsSkeleton />
      </div>
    )
  }

  if (!tenant) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate(`/platform/tenants?${searchParams.toString()}`)} className="-ml-3 h-8 text-muted-foreground">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Tenants
        </Button>
        <div className="flex flex-col items-center justify-center p-12 text-center border rounded-xl border-dashed">
          <Building className="h-10 w-10 text-slate-400 mb-4" />
          <h2 className="text-xl font-semibold">Tenant Not Found</h2>
          <p className="text-muted-foreground mt-2">The tenant you are looking for does not exist or you do not have permission to view it.</p>
        </div>
      </div>
    )
  }

  const handleBack = () => {
    navigate(`/platform/tenants?${searchParams.toString()}`)
  }

  return (
    <div className="space-y-6 pb-12">
      <Button variant="ghost" size="sm" onClick={handleBack} className="-ml-3 h-8 text-muted-foreground">
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Tenants
      </Button>

      {/* GitHub-Style Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between pb-6 border-b">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">{tenant.name}</h1>
            <TenantStatusBadge status={tenant.status} className="text-sm px-3 py-1" />
            <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-800 dark:bg-slate-800 dark:text-slate-300 capitalize">
              {tenant.plan || "Trial"} Plan
            </span>
          </div>
          
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-500">
            <div className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              Created {format(new Date(tenant.created_at), "MMM d, yyyy")} ({formatDistanceToNow(new Date(tenant.created_at))} ago)
            </div>
            <div className="flex items-center gap-1.5 font-mono text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
              ID: {tenant.id}
            </div>
            {/* Placeholders for actual data */}
            <div className="flex items-center gap-1.5">
              <User className="h-4 w-4" />
              Owner: Admin User
            </div>
            <div className="flex items-center gap-1.5">
              <Globe className="h-4 w-4" />
              {tenant.slug}.medtrack.io
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <TenantActionMenu tenant={tenant} variant="buttons" />
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="mb-4 h-auto flex-wrap justify-start gap-1 bg-transparent p-0">
          <TabsTrigger value="overview" className="data-[state=active]:bg-slate-100 dark:data-[state=active]:bg-slate-800 rounded-md px-4 py-2">Overview</TabsTrigger>
          <TabsTrigger value="users" className="data-[state=active]:bg-slate-100 dark:data-[state=active]:bg-slate-800 rounded-md px-4 py-2">Users</TabsTrigger>
          <TabsTrigger value="audit" className="data-[state=active]:bg-slate-100 dark:data-[state=active]:bg-slate-800 rounded-md px-4 py-2">Audit Logs</TabsTrigger>
          <TabsTrigger value="subscription" className="data-[state=active]:bg-slate-100 dark:data-[state=active]:bg-slate-800 rounded-md px-4 py-2">Subscription</TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-slate-100 dark:data-[state=active]:bg-slate-800 rounded-md px-4 py-2">Settings</TabsTrigger>
          <TabsTrigger value="usage" className="data-[state=active]:bg-slate-100 dark:data-[state=active]:bg-slate-800 rounded-md px-4 py-2">Usage</TabsTrigger>
          <TabsTrigger value="billing" className="data-[state=active]:bg-slate-100 dark:data-[state=active]:bg-slate-800 rounded-md px-4 py-2">Billing</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 outline-none">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Tenant Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-sm font-medium text-slate-500">Name</div>
                  <div className="col-span-2 text-sm font-medium">{tenant.name}</div>
                  
                  <div className="text-sm font-medium text-slate-500">Slug</div>
                  <div className="col-span-2 text-sm">{tenant.slug}</div>

                  <div className="text-sm font-medium text-slate-500">Status</div>
                  <div className="col-span-2 text-sm capitalize">{tenant.status}</div>

                  <div className="text-sm font-medium text-slate-500">Is System Tenant</div>
                  <div className="col-span-2 text-sm">{tenant.is_system_tenant ? "Yes" : "No"}</div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Contact Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-sm font-medium text-slate-500">Admin Name</div>
                  <div className="col-span-2 text-sm font-medium">Tenant Admin (Placeholder)</div>
                  
                  <div className="text-sm font-medium text-slate-500">Admin Email</div>
                  <div className="col-span-2 text-sm">admin@{tenant.slug}.com (Placeholder)</div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="users" className="outline-none">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Users</CardTitle>
              <CardDescription>All user accounts registered under this workspace.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-slate-500">
                User management list will be displayed here.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="outline-none">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Audit Logs</CardTitle>
              <CardDescription>Security and lifecycle events for this tenant.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>By</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>IP Address</TableHead>
                      <TableHead>Browser</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="text-slate-500 whitespace-nowrap">{format(new Date(tenant.created_at), "MMM d, yyyy HH:mm")}</TableCell>
                      <TableCell><span className="font-medium">Tenant Registered</span></TableCell>
                      <TableCell>System</TableCell>
                      <TableCell className="text-muted-foreground">-</TableCell>
                      <TableCell className="text-muted-foreground font-mono text-xs">192.168.1.1</TableCell>
                      <TableCell className="text-muted-foreground">Chrome / Windows</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="subscription" className="outline-none">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-indigo-500" />
                Subscription & Plan Details
              </CardTitle>
              <CardDescription>Manage this tenant's access tier and billing cycle.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div>
                  <div className="text-sm font-medium text-slate-500 mb-1">Current Plan</div>
                  <div className="text-lg font-semibold capitalize">{tenant.plan || "Trial"}</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-500 mb-1">Status</div>
                  <div className="text-lg font-semibold text-emerald-600">Active</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-500 mb-1">Billing Cycle</div>
                  <div className="text-lg font-semibold">Monthly</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-500 mb-1">Renewal Date</div>
                  <div className="text-lg font-semibold">{format(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), "MMM d, yyyy")}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="outline-none">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Settings</CardTitle>
              <CardDescription>Platform-level overrides and configurations for this tenant.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-slate-500">
                Configuration options placeholder.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="usage" className="outline-none">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Usage Metrics</CardTitle>
              <CardDescription>Resource utilization against plan limits.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-slate-500">
                Storage, user counts, and API call metrics will be displayed here.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="billing" className="outline-none">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Billing History</CardTitle>
              <CardDescription>Past invoices and payment methods.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-slate-500">
                Invoices and payment method management placeholder.
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
