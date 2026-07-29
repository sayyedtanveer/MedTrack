/**
 * AuditHistoryTab Component
 * 
 * Displays audit entries for a specific entity with client-side filtering.
 * Implements Task 13.3 requirements for manufacturing ERP audit trail.
 * 
 * Features:
 * - Sorted by timestamp descending
 * - Columns: Timestamp, User, Action, Previous Status, New Status, Reason
 * - Client-side filters: date range, user search, action type dropdown
 * - Loading state with skeleton rows
 * - Empty state messaging
 * - Error state (non-blocking inline error)
 * 
 * API: GET /audit-logs?entity_type={entityType}&entity_id={entityId}
 * Validates: Requirements 24.3, 24.4, 24.5, 24.6
 */

import { useEffect, useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/services/api-client"
import { format } from "date-fns"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"

// API Response Types
interface AuditLogEntry {
  id: string
  occurred_at: string
  user_id: string
  actor?: {
    email: string | null
    name: string | null
  }
  action: string
  entity_type: string
  entity_id: string
  before_value?: Record<string, any>
  after_value?: Record<string, any>
  summary?: string
}

interface AuditLogResponse {
  items: AuditLogEntry[]
  total: number
}

interface AuditHistoryTabProps {
  entityType: string
  entityId: string
}

/**
 * Safely format a timestamp string. Returns "Unknown Date" if the value is
 * missing, null, or not a valid ISO date string.
 */
const safeFormatDate = (timestamp: string | null | undefined): string => {
  if (!timestamp) return "Unknown Date"
  try {
    const d = new Date(timestamp)
    if (isNaN(d.getTime())) return "Unknown Date"
    return format(d, "MMM dd, yyyy HH:mm")
  } catch {
    return "Unknown Date"
  }
}

/**
 * Format action_type to human-readable form:
 * - Replace underscores with spaces
 * - Title case each word
 */
const formatActionType = (action?: string): string => {
  if (!action) return "Unknown"
  return action
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Extract status from state object, return "—" if not present
 */
const extractStatus = (state?: Record<string, any>): string => {
  if (!state || !state.status) return "—"
  return String(state.status)
}

export function AuditHistoryTab({ entityType, entityId }: AuditHistoryTabProps) {
  // Client-side filter states
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [userSearch, setUserSearch] = useState("")
  const [actionTypeFilter, setActionTypeFilter] = useState("all")

  // Fetch audit logs from API
  const { data, isLoading, error } = useQuery<AuditLogResponse>({
    queryKey: ['audit-logs', entityType, entityId],
    queryFn: async () => {
      const response = await apiClient.get<AuditLogResponse>('/audit-logs', {
        params: {
          entity_type: entityType,
          entity_id: entityId,
        },
      })
      return response.data
    },
  })

  // Extract unique action types for dropdown (once data loads)
  const uniqueActionTypes = useMemo(() => {
    if (!data?.items) return []
    const types = new Set(data.items.map(item => item.action).filter(Boolean))
    return Array.from(types).sort()
  }, [data])

  // Client-side filtering
  const filteredItems = useMemo(() => {
    if (!data?.items) return []
    
    let filtered = [...data.items]
    
    // Date range filter
    if (dateFrom) {
      const fromDate = new Date(dateFrom)
      filtered = filtered.filter(item => new Date(item.occurred_at) >= fromDate)
    }
    if (dateTo) {
      const toDate = new Date(dateTo)
      toDate.setHours(23, 59, 59, 999) // Include full day
      filtered = filtered.filter(item => new Date(item.occurred_at) <= toDate)
    }
    
    // User search filter (case-insensitive, matches user_name)
    if (userSearch.trim()) {
      const searchLower = userSearch.toLowerCase()
      filtered = filtered.filter(item => 
        item.actor?.name?.toLowerCase().includes(searchLower)
      )
    }
    
    // Action type filter
    if (actionTypeFilter !== 'all') {
      filtered = filtered.filter(item => item.action === actionTypeFilter)
    }
    
    // Sort by timestamp descending (most recent first)
    filtered.sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())
    
    return filtered
  }, [data, dateFrom, dateTo, userSearch, actionTypeFilter])

  // Reset filters when entity changes
  useEffect(() => {
    setDateFrom("")
    setDateTo("")
    setUserSearch("")
    setActionTypeFilter("all")
  }, [entityType, entityId])

  // Loading state: 3 skeleton rows
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex gap-4">
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-10 w-60" />
          <Skeleton className="h-10 w-60" />
        </div>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Previous Status</TableHead>
                <TableHead>New Status</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[1, 2, 3].map(i => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    )
  }

  // Error state: inline error message (not blocking)
  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-600">
          Failed to load audit history: {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Client-side filter controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1">
          <Label htmlFor="date-from" className="text-xs">Date From</Label>
          <Input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-9 w-40"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="date-to" className="text-xs">Date To</Label>
          <Input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-9 w-40"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="user-search" className="text-xs">User Search</Label>
          <Input
            id="user-search"
            type="text"
            placeholder="Search by user name..."
            value={userSearch}
            onChange={(e) => setUserSearch(e.target.value)}
            className="h-9 w-60"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="action-type" className="text-xs">Action Type</Label>
          <Select value={actionTypeFilter} onValueChange={setActionTypeFilter}>
            <SelectTrigger id="action-type" className="h-9 w-60">
              <SelectValue placeholder="All actions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All actions</SelectItem>
              {uniqueActionTypes.map(actionType => (
                <SelectItem key={actionType} value={actionType}>
                  {formatActionType(actionType)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Audit log table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="whitespace-nowrap">Timestamp</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Action</TableHead>
              <TableHead className="whitespace-nowrap">Previous Status</TableHead>
              <TableHead className="whitespace-nowrap">New Status</TableHead>
              <TableHead>Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredItems.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  No audit history found
                </TableCell>
              </TableRow>
            ) : (
              filteredItems.map(item => (
                <TableRow key={item.id}>
                  <TableCell className="whitespace-nowrap text-sm">
                    {safeFormatDate(item.occurred_at)}
                  </TableCell>
                  <TableCell className="text-sm">
                    {item.actor?.name || item.user_id}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-xs">
                      {formatActionType(item.action)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {extractStatus(item.before_value)}
                  </TableCell>
                  <TableCell className="text-sm">
                    {extractStatus(item.after_value)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {item.summary || "—"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      
      {/* Result count */}
      <div className="text-xs text-muted-foreground">
        Showing {filteredItems.length} of {data?.items.length || 0} entries
      </div>
    </div>
  )
}
