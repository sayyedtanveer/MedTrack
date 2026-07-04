/**
 * AuditHistoryTab Component
 * 
 * Displays audit entries for a specific entity with:
 * - Timestamp (formatted as "MMM DD, YYYY HH:mm")
 * - User (user name)
 * - Action (action_type, formatted as human-readable)
 * - Previous Status (from before_state.status if available)
 * - New Status (from after_state.status if available)
 * - Reason (reason field if present)
 * 
 * Validates: Requirements 24.3, 24.4, 24.5, 24.6
 */

import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { auditService, type AuditLogItem } from '@/services/audit.service';
import { useToast } from '@/hooks/use-toast';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Search, RefreshCw } from 'lucide-react';

interface AuditHistoryTabProps {
  entityType: string;
  entityId: string;
}

/**
 * Formats action_type to human-readable format
 * e.g., "release_wo" → "Release WO"
 */
const formatActionType = (action: string): string => {
  return action
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

/**
 * Formats timestamp as "MMM DD, YYYY HH:mm"
 */
const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    return format(date, 'MMM dd, yyyy HH:mm');
  } catch {
    return timestamp;
  }
};

/**
 * Extracts status from state object
 */
const extractStatus = (state: Record<string, unknown> | null | undefined): string => {
  if (!state) return '-';
  if (typeof state.status === 'string') return state.status;
  return '-';
};

/**
 * Determines if client-side or server-side filtering should be used
 */
const THRESHOLD = 500;

export function AuditHistoryTab({ entityType, entityId }: AuditHistoryTabProps) {
  const { toast } = useToast();
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filter state
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [userSearch, setUserSearch] = useState('');
  const [actionType, setActionType] = useState('');
  
  // Determine filtering mode
  const useClientSideFilter = total < THRESHOLD;

  // Extract unique action types for dropdown
  const actionTypes = Array.from(new Set(items.map(item => item.action))).sort();

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        entity_type: entityType,
        entity_id: entityId,
        limit: 1000, // Load all for client-side filtering if < 500
      };

      // Server-side filtering when >= 500 entries
      if (!useClientSideFilter) {
        if (dateFrom) params.date_from = dateFrom;
        if (dateTo) params.date_to = dateTo;
        if (userSearch) params.search = userSearch;
        if (actionType) params.action = actionType;
      }

      const result = await auditService.getAuditLogs(params);
      setItems(result.items);
      setTotal(result.total);
      
      // Apply client-side filters if needed
      if (useClientSideFilter) {
        applyClientSideFilters(result.items);
      } else {
        setFilteredItems(result.items);
      }
    } catch (err: any) {
      const message = err?.message || 'Failed to load audit history';
      setError(message);
      toast({
        title: 'Error loading audit history',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const applyClientSideFilters = (data: AuditLogItem[]) => {
    let filtered = [...data];

    // Date range filter
    if (dateFrom) {
      const fromDate = new Date(dateFrom);
      filtered = filtered.filter(item => new Date(item.occurred_at) >= fromDate);
    }
    if (dateTo) {
      const toDate = new Date(dateTo);
      toDate.setHours(23, 59, 59, 999); // Include entire day
      filtered = filtered.filter(item => new Date(item.occurred_at) <= toDate);
    }

    // User search filter
    if (userSearch) {
      const searchLower = userSearch.toLowerCase();
      filtered = filtered.filter(item => {
        const userName = item.actor?.name?.toLowerCase() || '';
        const userEmail = item.actor?.email?.toLowerCase() || '';
        return userName.includes(searchLower) || userEmail.includes(searchLower);
      });
    }

    // Action type filter
    if (actionType) {
      filtered = filtered.filter(item => item.action === actionType);
    }

    setFilteredItems(filtered);
  };

  const handleFilter = () => {
    if (useClientSideFilter) {
      applyClientSideFilters(items);
    } else {
      loadAuditLogs();
    }
  };

  const handleReset = () => {
    setDateFrom('');
    setDateTo('');
    setUserSearch('');
    setActionType('');
    if (useClientSideFilter) {
      setFilteredItems(items);
    } else {
      loadAuditLogs();
    }
  };

  useEffect(() => {
    loadAuditLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityType, entityId]);

  if (loading) {
    return (
      <Card className="p-6">
        <div className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center text-red-600">
          <p className="font-medium">Error loading audit history</p>
          <p className="text-sm mt-2">{error}</p>
          <Button 
            variant="outline" 
            onClick={loadAuditLogs} 
            className="mt-4"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Filter Controls */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <Label htmlFor="date-from" className="text-xs">Date From</Label>
            <Input
              id="date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="date-to" className="text-xs">Date To</Label>
            <Input
              id="date-to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="user-search" className="text-xs">User</Label>
            <Input
              id="user-search"
              type="text"
              placeholder="Search user..."
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="action-type" className="text-xs">Action Type</Label>
            <Select value={actionType} onValueChange={setActionType}>
              <SelectTrigger id="action-type" className="mt-1">
                <SelectValue placeholder="All actions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All actions</SelectItem>
                {actionTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {formatActionType(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end gap-2">
            <Button onClick={handleFilter} size="sm" className="flex-1">
              <Search className="mr-2 h-4 w-4" />
              Filter
            </Button>
            <Button onClick={handleReset} variant="outline" size="sm">
              Reset
            </Button>
          </div>
        </div>

        {/* Filtering mode indicator */}
        <div className="text-xs text-gray-500">
          {total} {total === 1 ? 'entry' : 'entries'} total
          {useClientSideFilter ? ' (client-side filtering)' : ' (server-side filtering)'}
        </div>

        {/* Audit History Table */}
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="whitespace-nowrap">Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Previous Status</TableHead>
                <TableHead>New Status</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                    No audit history found
                  </TableCell>
                </TableRow>
              ) : (
                filteredItems.map((item) => {
                  const beforeStatus = extractStatus(item.before_value);
                  const afterStatus = extractStatus(item.after_value);
                  const userName = item.actor?.name || item.actor?.email || 'System';
                  const reason = (item.extra?.reason as string) || '-';

                  return (
                    <TableRow key={item.id}>
                      <TableCell className="whitespace-nowrap text-sm">
                        {formatTimestamp(item.occurred_at)}
                      </TableCell>
                      <TableCell className="text-sm">{userName}</TableCell>
                      <TableCell className="text-sm">
                        <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium">
                          {formatActionType(item.action)}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        {beforeStatus !== '-' && (
                          <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                            {beforeStatus}
                          </span>
                        )}
                        {beforeStatus === '-' && <span className="text-gray-400">-</span>}
                      </TableCell>
                      <TableCell className="text-sm">
                        {afterStatus !== '-' && (
                          <span className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs">
                            {afterStatus}
                          </span>
                        )}
                        {afterStatus === '-' && <span className="text-gray-400">-</span>}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {reason}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </Card>
  );
}
