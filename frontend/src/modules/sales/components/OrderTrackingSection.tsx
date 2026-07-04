/**
 * Order Tracking Section Component
 * Displays estimated completion, dispatch, and delivery dates for a sales order.
 * Shows warnings when expected delivery exceeds customer promise date.
 * 
 * Requirements validated: 28.1–28.7
 */

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Skeleton } from '@/components/ui/skeleton';
import { apiClient } from '@/services/api-client';
import { format, parseISO, isAfter } from 'date-fns';
import { AlertTriangle, Calendar, Truck, Package, CheckCircle } from 'lucide-react';
import { SO_STATUS_COLOR_MAP } from './SalesOrderStatusConfig';

interface OrderTrackingData {
  sales_order_id: string;
  current_status: string;
  estimated_completion_date: string | null;
  expected_dispatch_date: string | null;
  expected_delivery_date: string | null;
  customer_promise_date: string | null;
  is_at_risk: boolean;
  linked_work_orders: Array<{
    id: string;
    work_order_number: string;
    status: string;
    due_date: string | null;
  }>;
}

interface OrderTrackingSectionProps {
  salesOrderId: string;
}

async function fetchOrderTracking(salesOrderId: string): Promise<OrderTrackingData> {
  const response = await apiClient.get(`/workflow/sales-orders/${salesOrderId}/tracking`);
  return response.data;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return 'Not available';
  try {
    return format(parseISO(dateString), 'MMM dd, yyyy');
  } catch {
    return 'Invalid date';
  }
}

export default function OrderTrackingSection({ salesOrderId }: OrderTrackingSectionProps) {
  const {
    data: tracking,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['order-tracking', salesOrderId],
    queryFn: () => fetchOrderTracking(salesOrderId),
    retry: 1,
    staleTime: 60000, // 1 minute
  });

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-gray-600">Order Tracking</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (isError || !tracking) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-gray-600">Order Tracking</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-500 py-4 text-center">
            {isError
              ? `Failed to load tracking information: ${error instanceof Error ? error.message : 'Unknown error'}`
              : 'Tracking information unavailable'}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Check if expected delivery is at risk
  const isDeliveryAtRisk =
    tracking.expected_delivery_date &&
    tracking.customer_promise_date &&
    isAfter(parseISO(tracking.expected_delivery_date), parseISO(tracking.customer_promise_date));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-gray-600">Order Tracking</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Delivery Risk Warning */}
        {isDeliveryAtRisk && (
          <Alert className="border-amber-200 bg-amber-50">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-800">
              <strong>Delivery at Risk:</strong> Expected delivery date (
              {formatDate(tracking.expected_delivery_date)}) exceeds customer promise date (
              {formatDate(tracking.customer_promise_date)}).
            </AlertDescription>
          </Alert>
        )}

        {/* Current Stage */}
        <div className="flex items-start gap-3 pb-3 border-b">
          <div className="p-2 rounded-lg bg-blue-50">
            <CheckCircle className="h-5 w-5 text-blue-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-gray-500 mb-1">Current Stage</p>
            <StatusBadge status={tracking.current_status} colorMap={SO_STATUS_COLOR_MAP} />
          </div>
        </div>

        {/* Estimated Completion Date */}
        <div className="flex items-start gap-3 pb-3 border-b">
          <div className="p-2 rounded-lg bg-purple-50">
            <Calendar className="h-5 w-5 text-purple-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-gray-500 mb-1">Estimated Completion Date</p>
            <p className="text-sm font-semibold text-gray-900">
              {formatDate(tracking.estimated_completion_date)}
            </p>
            {tracking.linked_work_orders && tracking.linked_work_orders.length > 0 && (
              <p className="text-xs text-gray-500 mt-1">
                Based on {tracking.linked_work_orders.length} linked work order
                {tracking.linked_work_orders.length > 1 ? 's' : ''}
              </p>
            )}
          </div>
        </div>

        {/* Expected Dispatch Date */}
        <div className="flex items-start gap-3 pb-3 border-b">
          <div className="p-2 rounded-lg bg-teal-50">
            <Package className="h-5 w-5 text-teal-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-gray-500 mb-1">Expected Dispatch Date</p>
            <p className="text-sm font-semibold text-gray-900">
              {formatDate(tracking.expected_dispatch_date)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Completion date + dispatch lead time
            </p>
          </div>
        </div>

        {/* Expected Delivery Date */}
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-green-50">
            <Truck className="h-5 w-5 text-green-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-gray-500 mb-1">Expected Delivery Date</p>
            <p
              className={`text-sm font-semibold ${
                isDeliveryAtRisk ? 'text-amber-600' : 'text-gray-900'
              }`}
            >
              {formatDate(tracking.expected_delivery_date)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Dispatch date + delivery lead time
            </p>
            {tracking.customer_promise_date && (
              <p className="text-xs text-gray-500 mt-1">
                Promise date: {formatDate(tracking.customer_promise_date)}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
