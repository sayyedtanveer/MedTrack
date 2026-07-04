/**
 * SalesWorkflowTimeline Component
 *
 * Visual timeline showing a Sales Order's progression through all lifecycle stages.
 * Fetches data from GET /workflow/sales-orders/{id}/status and renders:
 * - Completed stages with checkmarks and relative timestamps
 * - Current active stage with a filled indicator
 * - Pending future stages
 * - Sub-status beneath Production (aggregated WO status)
 * - CANCELLED status rendering all stages inactive
 * - Error fallback showing only current status
 *
 * Requirements: 4.1–4.7
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api-client';
import { CheckCircle2, Circle, XCircle, AlertCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ─── Types ──────────────────────────────────────────────────────────────────

/** Response shape from GET /workflow/sales-orders/{id}/status */
export interface WorkflowStatusResponse {
  sales_order_id: string;
  sales_order_status: string;
  sales_order_number: string;
  work_orders: WorkOrderStatusItem[];
  workflow_stage: string;
  estimated_completion_date?: string | null;
  expected_dispatch_date?: string | null;
  expected_delivery_date?: string | null;
}

export interface WorkOrderStatusItem {
  wo_id: string;
  wo_number: string;
  status: string;
  produced_quantity: number;
  planned_quantity: number;
}

// ─── Constants ──────────────────────────────────────────────────────────────

/**
 * Timeline stages in order. Each maps to one or more SO statuses.
 */
export const TIMELINE_STAGES = [
  { key: 'draft', label: 'Draft', statuses: ['DRAFT'] },
  { key: 'approval', label: 'Approval', statuses: ['PENDING_APPROVAL', 'APPROVED'] },
  { key: 'confirmed', label: 'Confirmed', statuses: ['CONFIRMED', 'WORK_ORDER_CREATED', 'PROCESSING'] },
  { key: 'production', label: 'Production', statuses: ['PRODUCTION'] },
  { key: 'ready', label: 'Ready', statuses: ['READY', 'READY_FOR_DISPATCH'] },
  { key: 'dispatched', label: 'Dispatched', statuses: ['SHIPPED'] },
  { key: 'delivered', label: 'Delivered', statuses: ['DELIVERED'] },
  { key: 'invoiced', label: 'Invoiced', statuses: ['INVOICED'] },
  { key: 'paid', label: 'Paid', statuses: ['PAYMENT_RECEIVED'] },
  { key: 'completed', label: 'Completed', statuses: ['COMPLETED'] },
] as const;

/**
 * Work Order status ordering from least-advanced to most-advanced.
 * Used to determine the aggregated sub-status for Production stage.
 */
const WO_STATUS_ORDER: string[] = [
  'PLANNED',
  'RELEASED',
  'MATERIAL_PENDING',
  'MATERIAL_RESERVED',
  'MATERIAL_ISSUED',
  'IN_PRODUCTION',
  'QC_PENDING',
  'QC_APPROVED',
  'FG_RECEIVED',
  'COMPLETED',
  'CLOSED',
];

const WO_STATUS_LABELS: Record<string, string> = {
  PLANNED: 'Planned',
  RELEASED: 'Released',
  MATERIAL_PENDING: 'Material Pending',
  MATERIAL_RESERVED: 'Material Reserved',
  MATERIAL_ISSUED: 'Material Issued',
  IN_PRODUCTION: 'In Production',
  QC_PENDING: 'QC Pending',
  QC_APPROVED: 'QC Approved',
  FG_RECEIVED: 'FG Received',
  COMPLETED: 'Completed',
  CLOSED: 'Closed',
  PRODUCTION_HOLD: 'Production Hold',
  REWORK: 'Rework',
  REJECTED: 'Rejected',
  QC_REJECTED: 'QC Rejected',
  CANCELLED: 'Cancelled',
};

// ─── Helpers ────────────────────────────────────────────────────────────────

/**
 * Find the index of the current stage given the SO status.
 * Returns -1 if CANCELLED or not found.
 */
export function getCurrentStageIndex(status: string): number {
  if (status === 'CANCELLED' || status === 'REJECTED') return -1;
  for (let i = 0; i < TIMELINE_STAGES.length; i++) {
    // Cast to readonly string[] to allow arbitrary string comparison
    if ((TIMELINE_STAGES[i].statuses as readonly string[]).includes(status)) {
      return i;
    }
  }
  return -1;
}

/**
 * Get the least-advanced WO status from a list of work orders.
 * Returns null if no work orders.
 */
export function getAggregatedWOStatus(workOrders: WorkOrderStatusItem[]): string | null {
  if (!workOrders || workOrders.length === 0) return null;

  // Filter out cancelled/rejected WOs for aggregation
  const activeWOs = workOrders.filter(
    (wo) => wo.status !== 'CANCELLED' && wo.status !== 'REJECTED'
  );
  if (activeWOs.length === 0) return null;

  let leastAdvancedIdx = WO_STATUS_ORDER.length;
  let leastAdvancedStatus = activeWOs[0].status;

  for (const wo of activeWOs) {
    const idx = WO_STATUS_ORDER.indexOf(wo.status);
    if (idx === -1) {
      // Unknown status (e.g. REWORK, PRODUCTION_HOLD) — treat as earlier than most
      // Just use the first one encountered that's not in the ordered list
      if (leastAdvancedIdx > 0) {
        leastAdvancedIdx = 0;
        leastAdvancedStatus = wo.status;
      }
    } else if (idx < leastAdvancedIdx) {
      leastAdvancedIdx = idx;
      leastAdvancedStatus = wo.status;
    }
  }

  return leastAdvancedStatus;
}

/**
 * Format a timestamp as relative time (e.g., "2 hours ago").
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString();
}

/**
 * Format a timestamp as absolute date-time string for tooltip.
 */
function formatAbsoluteTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

// ─── Component Props ────────────────────────────────────────────────────────

interface SalesWorkflowTimelineProps {
  /** Sales Order ID to fetch workflow status for */
  salesOrderId: string;
  /** Optional: current status for fallback rendering if API fails */
  currentStatus?: string;
  /** Optional: stage completion timestamps keyed by stage key */
  stageTimestamps?: Record<string, string>;
}

// ─── API Fetcher ────────────────────────────────────────────────────────────

async function fetchWorkflowStatus(salesOrderId: string): Promise<WorkflowStatusResponse> {
  const { data } = await apiClient.get<WorkflowStatusResponse>(
    `/workflow/sales-orders/${salesOrderId}/status`
  );
  return data;
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function SalesWorkflowTimeline({
  salesOrderId,
  currentStatus,
  stageTimestamps,
}: SalesWorkflowTimelineProps) {
  const {
    data: workflowData,
    isError,
    isLoading,
  } = useQuery({
    queryKey: ['workflow-status', salesOrderId],
    queryFn: () => fetchWorkflowStatus(salesOrderId),
    enabled: Boolean(salesOrderId),
    refetchOnWindowFocus: false,
    staleTime: 30_000,
  });

  // Error fallback: show only current status (Req 4.6)
  if (isError) {
    return <TimelineFallback status={currentStatus || 'UNKNOWN'} />;
  }

  // Loading state
  if (isLoading) {
    return <TimelineSkeleton />;
  }

  if (!workflowData) {
    return <TimelineFallback status={currentStatus || 'UNKNOWN'} />;
  }

  const soStatus = workflowData.sales_order_status;
  const isCancelled = soStatus === 'CANCELLED' || soStatus === 'REJECTED';
  const currentStageIdx = getCurrentStageIndex(soStatus);
  const aggregatedWOStatus = getAggregatedWOStatus(workflowData.work_orders);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="w-full" data-testid="sales-workflow-timeline">
        {/* CANCELLED indicator */}
        {isCancelled && (
          <div className="flex items-center gap-2 mb-3 text-red-600 text-sm font-medium">
            <XCircle className="h-4 w-4" />
            <span>Order {soStatus === 'REJECTED' ? 'Rejected' : 'Cancelled'}</span>
          </div>
        )}

        {/* Timeline */}
        <div role="list" className="flex items-start justify-between gap-1 overflow-x-auto py-2">
          {TIMELINE_STAGES.map((stage, idx) => {
            const isCompleted = !isCancelled && currentStageIdx > idx;
            const isCurrent = !isCancelled && currentStageIdx === idx;
            const isPending = isCancelled || currentStageIdx < idx;

            // Determine timestamp (from provided timestamps or we don't have per-stage timestamps from API)
            const timestamp = stageTimestamps?.[stage.key] ?? null;

            return (
              <div key={stage.key} role="listitem" className="flex flex-col items-center flex-1 min-w-0">
                {/* Connector + Icon */}
                <div className="flex items-center w-full">
                  {/* Left connector line */}
                  {idx > 0 && (
                    <div
                      className={cn(
                        'h-0.5 flex-1',
                        isCompleted || isCurrent
                          ? 'bg-blue-500'
                          : isCancelled
                            ? 'bg-gray-200'
                            : 'bg-gray-200'
                      )}
                    />
                  )}

                  {/* Stage icon */}
                  <StageIcon
                    isCompleted={isCompleted}
                    isCurrent={isCurrent}
                    isCancelled={isCancelled}
                  />

                  {/* Right connector line */}
                  {idx < TIMELINE_STAGES.length - 1 && (
                    <div
                      className={cn(
                        'h-0.5 flex-1',
                        isCompleted ? 'bg-blue-500' : 'bg-gray-200'
                      )}
                    />
                  )}
                </div>

                {/* Stage label */}
                <span
                  className={cn(
                    'text-xs mt-1.5 text-center truncate max-w-full px-0.5',
                    isCurrent && 'font-bold text-blue-700',
                    isCompleted && 'text-gray-700',
                    isPending && !isCancelled && 'text-gray-400',
                    isCancelled && 'text-gray-300'
                  )}
                >
                  {stage.label}
                </span>

                {/* Sub-status for Production stage (Req 4.3) */}
                {stage.key === 'production' && isCurrent && aggregatedWOStatus && (
                  <span className="text-[10px] text-amber-600 font-medium mt-0.5 truncate max-w-full">
                    {WO_STATUS_LABELS[aggregatedWOStatus] || aggregatedWOStatus}
                  </span>
                )}

                {/* Timestamp for completed stages (Req 4.5) */}
                {isCompleted && timestamp && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="text-[10px] text-gray-400 mt-0.5 cursor-default">
                        {formatRelativeTime(timestamp)}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="text-xs">
                      {formatAbsoluteTime(timestamp)}
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </TooltipProvider>
  );
}

// ─── Sub-Components ─────────────────────────────────────────────────────────

function StageIcon({
  isCompleted,
  isCurrent,
  isCancelled,
}: {
  isCompleted: boolean;
  isCurrent: boolean;
  isCancelled: boolean;
}) {
  if (isCompleted) {
    return (
      <CheckCircle2
        className="h-5 w-5 text-blue-500 shrink-0"
        data-testid="stage-completed"
      />
    );
  }
  if (isCurrent) {
    return (
      <div
        className="h-5 w-5 rounded-full bg-blue-600 border-2 border-blue-600 shrink-0 flex items-center justify-center"
        data-testid="stage-current"
      >
        <div className="h-2 w-2 rounded-full bg-white" />
      </div>
    );
  }
  // Pending or cancelled
  return (
    <Circle
      className={cn(
        'h-5 w-5 shrink-0',
        isCancelled ? 'text-gray-200' : 'text-gray-300'
      )}
      data-testid="stage-pending"
    />
  );
}

function TimelineFallback({ status }: { status: string }) {
  return (
    <div
      className="flex items-center gap-2 py-3 px-4 bg-gray-50 border rounded text-sm text-gray-600"
      data-testid="timeline-fallback"
    >
      <AlertCircle className="h-4 w-4 text-amber-500" />
      <span>
        Current status: <span className="font-medium">{status.replace(/_/g, ' ')}</span>
      </span>
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="flex items-center justify-between gap-1 py-2" data-testid="timeline-skeleton">
      {TIMELINE_STAGES.map((stage) => (
        <div key={stage.key} className="flex flex-col items-center flex-1">
          <div className="h-5 w-5 rounded-full bg-gray-100 animate-pulse" />
          <div className="h-3 w-12 mt-1.5 bg-gray-100 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}
