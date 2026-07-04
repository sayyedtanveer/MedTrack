/**
 * ProductionTrackerPanel Component
 *
 * Embedded in SalesOrderDetailPage when a Sales Order has linked Work Orders.
 * Shows per-WO progress (produced / planned), aggregated overall progress,
 * material shortage warnings, overdue indicators, summary banners, and a
 * "Production Complete" notice when all WOs are done.
 *
 * Hides itself entirely when no linked WOs exist.
 * Handles API errors inline without blocking the page.
 *
 * Requirements: 5.1–5.8, 21.1–21.7
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { StatusBadge } from '@/components/shared';
import { apiClient } from '@/services/api-client';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Factory,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Types ────────────────────────────────────────────────────────────────────

/** Per-WO item from GET /workflow/sales-orders/{id}/status */
export interface LinkedWorkOrder {
  wo_id: string;
  wo_number: string;
  status: string;
  produced_quantity: number;
  planned_quantity: number;
  /** ISO date string, optional — populated when available */
  due_date?: string | null;
}

/** Response shape from GET /workflow/sales-orders/{id}/status (partial) */
interface WorkflowStatusResponse {
  sales_order_id: string;
  sales_order_status: string;
  work_orders: LinkedWorkOrder[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

/** WO statuses considered "complete" — no further progress expected. Req 5.7 */
const COMPLETE_STATUSES = new Set(['FG_RECEIVED', 'COMPLETED', 'CLOSED']);

/** WO statuses that indicate a material shortage warning. Req 5.5 */
const SHORTAGE_STATUSES = new Set(['MATERIAL_PENDING']);

/** WO statuses that indicate a blocked state (banner). Req 5.8 */
const BLOCKED_STATUSES = new Set(['MATERIAL_PENDING', 'REWORK']);

/** Color map for WO status badges. */
const WO_STATUS_COLORS: Record<string, string> = {
  PLANNED: 'border-gray-200 bg-gray-50 text-gray-700',
  RELEASED: 'border-blue-200 bg-blue-50 text-blue-700',
  MATERIAL_PENDING: 'border-amber-200 bg-amber-50 text-amber-700',
  MATERIAL_RESERVED: 'border-indigo-200 bg-indigo-50 text-indigo-700',
  MATERIAL_ISSUED: 'border-purple-200 bg-purple-50 text-purple-700',
  IN_PRODUCTION: 'border-yellow-200 bg-yellow-50 text-yellow-700',
  QC_PENDING: 'border-orange-200 bg-orange-50 text-orange-700',
  QC_APPROVED: 'border-green-200 bg-green-50 text-green-700',
  QC_REJECTED: 'border-red-200 bg-red-50 text-red-700',
  FG_RECEIVED: 'border-teal-200 bg-teal-50 text-teal-700',
  COMPLETED: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  CLOSED: 'border-slate-200 bg-slate-100 text-slate-600',
  REWORK: 'border-orange-200 bg-orange-50 text-orange-700',
  REJECTED: 'border-red-200 bg-red-50 text-red-700',
  PRODUCTION_HOLD: 'border-rose-200 bg-rose-50 text-rose-700',
  CANCELLED: 'border-gray-200 bg-gray-100 text-gray-500',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Calculate progress percentage for a single WO.
 * Property 8: round((Q / P) × 100) when P > 0, else 0.
 * Req 5.3, 21.1
 */
export function calcProgress(produced: number, planned: number): number {
  if (planned <= 0) return 0;
  return Math.round((produced / planned) * 100);
}

/**
 * Calculate overall progress across multiple WOs.
 * Property 8: round(sum_produced / sum_planned × 100).
 * Req 5.4, 21.1
 */
export function calcOverallProgress(workOrders: LinkedWorkOrder[]): number {
  const sumPlanned = workOrders.reduce((acc, wo) => acc + Number(wo.planned_quantity), 0);
  const sumProduced = workOrders.reduce((acc, wo) => acc + Number(wo.produced_quantity), 0);
  if (sumPlanned <= 0) return 0;
  return Math.round((sumProduced / sumPlanned) * 100);
}

/**
 * Check whether a WO is overdue: due_date is a past date.
 * Returns days overdue (> 0) or 0 if not overdue.
 * Req 5.6
 */
export function daysOverdue(dueDateStr: string | null | undefined): number {
  if (!dueDateStr) return 0;
  const due = new Date(dueDateStr);
  // Normalize to midnight so we compare full days
  due.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffMs = today.getTime() - due.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  return diffDays > 0 ? diffDays : 0;
}

/**
 * Format a due date string for display.
 */
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// ─── API Fetcher ──────────────────────────────────────────────────────────────

async function fetchWorkflowStatus(salesOrderId: string): Promise<WorkflowStatusResponse> {
  const { data } = await apiClient.get<WorkflowStatusResponse>(
    `/workflow/sales-orders/${salesOrderId}/status`
  );
  return data;
}

// ─── Component Props ──────────────────────────────────────────────────────────

interface ProductionTrackerPanelProps {
  /** Sales Order ID — used to fetch linked work orders */
  salesOrderId: string;
}

// ─── Sub-Components ───────────────────────────────────────────────────────────

/** Progress bar with percentage label. */
function ProgressRow({
  label,
  percent,
  className,
}: {
  label: string;
  percent: number;
  className?: string;
}) {
  const clamped = Math.min(100, Math.max(0, percent));
  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span className="font-semibold tabular-nums">{clamped}%</span>
      </div>
      <Progress
        value={clamped}
        className="h-1.5"
        aria-label={`${label}: ${clamped}%`}
      />
    </div>
  );
}

/** Inline loading skeleton for a single WO row. */
function WORowSkeleton() {
  return (
    <div className="flex items-center gap-3 py-3 border-b last:border-0">
      <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
      <div className="h-5 w-24 bg-gray-100 rounded animate-pulse" />
      <div className="flex-1 h-3 bg-gray-100 rounded animate-pulse" />
    </div>
  );
}

// ─── WO Row ───────────────────────────────────────────────────────────────────

interface WORowProps {
  wo: LinkedWorkOrder;
}

function WORow({ wo }: WORowProps) {
  const progress = calcProgress(Number(wo.produced_quantity), Number(wo.planned_quantity));
  const overdue = daysOverdue(wo.due_date);
  const hasMaterialShortage = SHORTAGE_STATUSES.has(wo.status);
  const isComplete = COMPLETE_STATUSES.has(wo.status);

  return (
    <div
      className="py-3 border-b last:border-0 space-y-2"
      data-testid={`wo-row-${wo.wo_id}`}
    >
      {/* Row header: WO link + status badge + quantities */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Req 5.1: WO number as clickable link */}
        <Link
          to={`/work-orders/${wo.wo_id}`}
          className="font-semibold text-sm text-blue-700 hover:underline shrink-0"
          data-testid={`wo-link-${wo.wo_id}`}
        >
          {wo.wo_number}
        </Link>

        {/* Req 5.1: Status badge */}
        <StatusBadge
          status={wo.status}
          colorMap={WO_STATUS_COLORS}
        />

        {/* Req 5.1: Planned / Produced qty */}
        <span className="text-xs text-gray-500 shrink-0">
          {Number(wo.produced_quantity)} / {Number(wo.planned_quantity)} produced
        </span>

        {/* Req 5.1: Due date */}
        {wo.due_date && (
          <span className="text-xs text-gray-500 shrink-0">
            Due: {formatDate(wo.due_date)}
          </span>
        )}
      </div>

      {/* Req 5.3: Progress bar */}
      {!isComplete && (
        <ProgressRow
          label={`Progress`}
          percent={progress}
          className="max-w-xs"
        />
      )}

      {/* Req 5.5: Material shortage warning (amber) */}
      {hasMaterialShortage && (
        <div
          className="flex items-center gap-1.5 text-amber-700 text-xs font-medium"
          data-testid={`shortage-warning-${wo.wo_id}`}
          role="alert"
          aria-label="Material shortage warning"
        >
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>Material shortage — awaiting procurement</span>
        </div>
      )}

      {/* Req 5.6: Overdue indicator (red) */}
      {overdue > 0 && !isComplete && (
        <div
          className="flex items-center gap-1.5 text-red-600 text-xs font-medium"
          data-testid={`overdue-indicator-${wo.wo_id}`}
          role="alert"
          aria-label={`Overdue by ${overdue} day${overdue !== 1 ? 's' : ''}`}
        >
          <Clock className="h-3.5 w-3.5 shrink-0" />
          <span>
            Overdue by {overdue} day{overdue !== 1 ? 's' : ''}
          </span>
        </div>
      )}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function ProductionTrackerPanel({ salesOrderId }: ProductionTrackerPanelProps) {
  const {
    data: workflowData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['workflow-status', salesOrderId],
    queryFn: () => fetchWorkflowStatus(salesOrderId),
    enabled: Boolean(salesOrderId),
    refetchOnWindowFocus: false,
    staleTime: 30_000,
  });

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <Card data-testid="production-tracker-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Factory className="h-5 w-5 text-yellow-600" />
            Production Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <WORowSkeleton />
          <WORowSkeleton />
        </CardContent>
      </Card>
    );
  }

  // ── Req 5.2 + error handling: inline error, don't block page ─────────────
  if (isError) {
    return (
      <Card data-testid="production-tracker-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Factory className="h-5 w-5 text-yellow-600" />
            Production Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {(error as Error)?.message || 'Could not load production data.'}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const workOrders = workflowData?.work_orders ?? [];

  // ── Req 5.2: Hide panel entirely when no linked WOs ───────────────────────
  if (workOrders.length === 0) {
    return null;
  }

  // ── Compute aggregated state ───────────────────────────────────────────────

  // Req 5.7: "Production Complete" when all WOs are FG_RECEIVED or COMPLETED
  const allComplete = workOrders.every((wo) => COMPLETE_STATUSES.has(wo.status));

  // Req 5.8: Summary banner for blocked WOs
  const blockedWOs = workOrders.filter((wo) => BLOCKED_STATUSES.has(wo.status));
  const shortageWOs = workOrders.filter((wo) => SHORTAGE_STATUSES.has(wo.status));
  const reworkWOs = workOrders.filter((wo) => wo.status === 'REWORK');

  // Overall progress (Req 5.4, 21.1)
  const overallProgress = calcOverallProgress(workOrders);

  return (
    <Card data-testid="production-tracker-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Factory className="h-5 w-5 text-yellow-600" />
          Production Progress
          {allComplete && (
            <span
              className="ml-auto flex items-center gap-1 text-emerald-600 text-sm font-semibold"
              data-testid="production-complete-badge"
            >
              <CheckCircle2 className="h-4 w-4" />
              Production Complete
            </span>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">

        {/* Req 5.8: Summary banner for blocked WOs */}
        {blockedWOs.length > 0 && !allComplete && (
          <Alert
            className="border-amber-200 bg-amber-50 text-amber-800"
            data-testid="blocked-wo-banner"
            role="alert"
          >
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-sm">
              {shortageWOs.length > 0 && reworkWOs.length > 0 && (
                <>
                  {shortageWOs.length} WO{shortageWOs.length !== 1 ? 's' : ''} blocked on material shortage
                  {' '}and {reworkWOs.length} in rework.
                </>
              )}
              {shortageWOs.length > 0 && reworkWOs.length === 0 && (
                <>
                  {shortageWOs.length} work order{shortageWOs.length !== 1 ? 's' : ''} blocked on material shortage.
                </>
              )}
              {reworkWOs.length > 0 && shortageWOs.length === 0 && (
                <>
                  {reworkWOs.length} work order{reworkWOs.length !== 1 ? 's' : ''} currently in rework.
                </>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Overall progress (Req 5.4, 21.1) — only shown when multiple WOs */}
        {workOrders.length > 1 && (
          <ProgressRow
            label="Overall Progress"
            percent={overallProgress}
            data-testid="overall-progress"
          />
        )}

        {/* Per-WO rows */}
        <div>
          {workOrders.map((wo) => (
            <WORow key={wo.wo_id} wo={wo} />
          ))}
        </div>

      </CardContent>
    </Card>
  );
}
