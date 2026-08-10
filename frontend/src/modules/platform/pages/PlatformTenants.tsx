import { useState, useMemo } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { usePlatformTenants, useApproveTenant, useRejectTenant, useSuspendTenant } from "../hooks/usePlatformTenants"
import { TenantStatusBadge } from "../components/TenantStatusBadge"
import { TenantActionMenu } from "../components/TenantActionMenu"
import { TenantListSkeleton } from "../components/PlatformSkeletons"
import { PlatformEmptyState } from "../components/EmptyStates"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import { format } from "date-fns"
import { Search, FilterX, Users } from "lucide-react"

export default function PlatformTenants() {
  const navigate = useNavigate()
  const { data, isLoading } = usePlatformTenants()
  const [searchParams, setSearchParams] = useSearchParams()

  const searchQuery = searchParams.get("search") || ""
  const statusFilter = searchParams.get("status") || "all"
  const planFilter = searchParams.get("plan") || "all"
  const dateFilter = searchParams.get("date") || "all"

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const updateFilters = (updates: Record<string, string | null>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === "all" || value === "") {
        newParams.delete(key)
      } else {
        newParams.set(key, value)
      }
    })
    setSearchParams(newParams)
  }

  const clearFilters = () => {
    setSearchParams(new URLSearchParams())
  }

  const tenants = data?.tenants || []

  const filteredTenants = useMemo(() => {
    return tenants.filter(t => {
      // Status Filter
      if (statusFilter !== "all" && t.status !== statusFilter) return false

      // Plan Filter (Placeholder logic since `plan` exists on `SystemTenant`)
      if (planFilter !== "all" && t.plan !== planFilter) return false

      // Date Filter
      if (dateFilter !== "all") {
        const createdDate = new Date(t.created_at)
        const now = new Date()
        const diffTime = Math.abs(now.getTime() - createdDate.getTime())
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        
        if (dateFilter === "today" && diffDays > 1) return false
        if (dateFilter === "7days" && diffDays > 7) return false
        if (dateFilter === "30days" && diffDays > 30) return false
      }

      // Search Query
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        return (
          t.name.toLowerCase().includes(q) ||
          t.id.toLowerCase().includes(q) ||
          t.slug.toLowerCase().includes(q)
        )
      }

      return true
    })
  }, [tenants, searchQuery, statusFilter, planFilter, dateFilter])

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredTenants.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredTenants.map(t => t.id)))
    }
  }

  const toggleSelect = (id: string) => {
    const newSet = new Set(selectedIds)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setSelectedIds(newSet)
  }

  const approveMutation = useApproveTenant()
  const rejectMutation = useRejectTenant()
  const suspendMutation = useSuspendTenant()

  const handleBulkApprove = async () => {
    if (!window.confirm(`Are you sure you want to approve ${selectedIds.size} tenant(s)?`)) return
    
    // Process approvals sequentially or Promise.all. Promise.all is faster.
    try {
      await Promise.all(Array.from(selectedIds).map(id => approveMutation.mutateAsync(id)))
      setSelectedIds(new Set())
    } catch (error) {
      // Errors handled by useShowError inside the mutation
    }
  }

  const handleBulkReject = async () => {
    const reason = window.prompt(`Please provide a reason to reject ${selectedIds.size} tenant(s):`)
    if (!reason) return
    
    try {
      await Promise.all(Array.from(selectedIds).map(id => rejectMutation.mutateAsync({ tenantId: id, data: { reason } })))
      setSelectedIds(new Set())
    } catch (error) {
      // Errors handled by useShowError inside the mutation
    }
  }

  const handleBulkSuspend = async () => {
    const reason = window.prompt(`Please provide a reason to suspend ${selectedIds.size} tenant(s):`)
    if (!reason) return
    
    try {
      await Promise.all(Array.from(selectedIds).map(id => suspendMutation.mutateAsync({ tenantId: id, data: { reason } })))
      setSelectedIds(new Set())
    } catch (error) {
      // Errors handled by useShowError inside the mutation
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Tenant Management</h1>
        <TenantListSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Tenant Management</h1>
          <p className="text-muted-foreground mt-1">Manage and monitor workspaces across the platform.</p>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-4 sm:p-6">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-1 items-center gap-4">
              <div className="relative max-w-sm flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by name, ID, or slug..."
                  value={searchQuery}
                  onChange={(e) => updateFilters({ search: e.target.value })}
                  className="pl-9"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Select value={statusFilter} onValueChange={(val) => updateFilters({ status: val })}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>

              <Select value={planFilter} onValueChange={(val) => updateFilters({ plan: val })}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Subscription" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Plans</SelectItem>
                  <SelectItem value="trial">Trial</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                </SelectContent>
              </Select>

              <Select value={dateFilter} onValueChange={(val) => updateFilters({ date: val })}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Created Date" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Time</SelectItem>
                  <SelectItem value="today">Today</SelectItem>
                  <SelectItem value="7days">Last 7 Days</SelectItem>
                  <SelectItem value="30days">Last 30 Days</SelectItem>
                </SelectContent>
              </Select>

              {(searchQuery || statusFilter !== "all" || planFilter !== "all" || dateFilter !== "all") && (
                <Button variant="ghost" size="sm" onClick={clearFilters} className="h-9 px-3">
                  <FilterX className="mr-2 h-4 w-4" />
                  Reset
                </Button>
              )}
            </div>
          </div>

          {selectedIds.size > 0 && (
            <div className="mb-4 flex items-center gap-3 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-lg border">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {selectedIds.size} tenant(s) selected
              </span>
              <div className="flex items-center gap-2 ml-auto">
                <Button variant="outline" size="sm" className="h-8" onClick={handleBulkApprove}>Approve Selected</Button>
                <Button variant="outline" size="sm" className="h-8 text-destructive hover:bg-destructive/10" onClick={handleBulkReject}>Reject Selected</Button>
                <Button variant="outline" size="sm" className="h-8 text-destructive hover:bg-destructive/10" onClick={handleBulkSuspend}>Suspend Selected</Button>
              </div>
            </div>
          )}

          {filteredTenants.length === 0 ? (
            <PlatformEmptyState 
              icon={Users} 
              title="No tenants found" 
              description="No workspaces match your current filters and search criteria."
              action={
                <Button variant="outline" onClick={clearFilters}>Clear Filters</Button>
              }
            />
          ) : (
            <>
              {/* Desktop Table */}
              <div className="hidden rounded-md border md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12 text-center">
                        <Checkbox 
                          checked={selectedIds.size > 0 && selectedIds.size === filteredTenants.length}
                          onCheckedChange={toggleSelectAll}
                        />
                      </TableHead>
                      <TableHead>Tenant</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Active State</TableHead>
                      <TableHead>Subscription</TableHead>
                      <TableHead>Created Date</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTenants.map((tenant) => (
                      <TableRow key={tenant.id} className="cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/50" onClick={(e) => {
                        // Prevent navigation if clicking on checkbox or action menu
                        if ((e.target as HTMLElement).closest('button') || (e.target as HTMLElement).closest('[role="checkbox"]')) return;
                        navigate(`/platform/tenants/${tenant.id}?${searchParams.toString()}`)
                      }}>
                        <TableCell className="text-center" onClick={(e) => e.stopPropagation()}>
                          <Checkbox 
                            checked={selectedIds.has(tenant.id)}
                            onCheckedChange={() => toggleSelect(tenant.id)}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-semibold text-slate-900 dark:text-slate-100">{tenant.name}</span>
                            <span className="text-xs text-muted-foreground font-mono">{tenant.id}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <TenantStatusBadge status={tenant.status} />
                        </TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${tenant.is_active ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-400'}`}>
                            {tenant.is_active ? "Active" : "Inactive"}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="capitalize">{tenant.plan || "Trial"}</span>
                        </TableCell>
                        <TableCell className="text-slate-500 text-sm">
                          {format(new Date(tenant.created_at), "MMM d, yyyy")}
                        </TableCell>
                        <TableCell className="text-right">
                          <TenantActionMenu tenant={tenant} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile Cards */}
              <div className="grid gap-4 md:hidden">
                {filteredTenants.map((tenant) => (
                  <Card key={tenant.id} className="overflow-hidden" onClick={() => navigate(`/platform/tenants/${tenant.id}?${searchParams.toString()}`)}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3">
                          <div onClick={(e) => e.stopPropagation()} className="mt-1">
                            <Checkbox 
                              checked={selectedIds.has(tenant.id)}
                              onCheckedChange={() => toggleSelect(tenant.id)}
                            />
                          </div>
                          <div>
                            <h4 className="font-semibold text-slate-900 dark:text-slate-100">{tenant.name}</h4>
                            <p className="mt-1 text-xs text-muted-foreground font-mono truncate max-w-[200px]">{tenant.id}</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <TenantStatusBadge status={tenant.status} />
                              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${tenant.is_active ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-400'}`}>
                                {tenant.is_active ? "Active" : "Inactive"}
                              </span>
                              <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800 dark:bg-slate-800 dark:text-slate-300 capitalize">
                                {tenant.plan || "Trial"}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div onClick={(e) => e.stopPropagation()}>
                          <TenantActionMenu tenant={tenant} />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
