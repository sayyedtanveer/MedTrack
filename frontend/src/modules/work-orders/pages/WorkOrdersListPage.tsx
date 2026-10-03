import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { REALTIME_EVENT_NAME } from '@/components/notifications/RealtimeNotificationsBridge';
import workOrderService, { type WorkOrderSummary } from '@/services/work-order.service';
import ResponsiveDataList from '@/components/shared/ResponsiveDataList';

const STATUS_COLORS: Record<string, string> = {
  PLANNED: 'bg-slate-100 text-slate-700',
  RELEASED: 'bg-blue-100 text-blue-700',
  IN_PRODUCTION: 'bg-amber-100 text-amber-700',
  COMPLETED: 'bg-emerald-100 text-emerald-700',
  CLOSED: 'bg-zinc-100 text-zinc-600',
};

const PRIORITY_COLORS: Record<string, string> = {
  LOW: 'text-slate-500',
  NORMAL: 'text-slate-700',
  HIGH: 'text-amber-600',
  URGENT: 'text-red-600',
};

const STATUS_OPTIONS = ['', 'PLANNED', 'RELEASED', 'MATERIAL_PENDING', 'MATERIAL_RESERVED', 'MATERIAL_ISSUED', 'IN_PRODUCTION', 'QC_PENDING', 'FG_RECEIVED', 'COMPLETED', 'CLOSED'];

export default function WorkOrdersListPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<WorkOrderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const res = await workOrderService.list(statusFilter ? { status: statusFilter } : undefined);
      setOrders(res.data);
    } catch {
      setError('Failed to load work orders.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const handleRealtime = () => {
      void load(true);
    };
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime);
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime);
  }, [load]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="erp-surface flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Manufacturing</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">Work Orders</h1>
          <p className="mt-1 text-sm text-slate-500">Manufacturing execution management</p>
        </div>
        <button
          id="btn-create-work-order"
          onClick={() => navigate('new')}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:from-blue-700 hover:to-blue-800 hover:shadow-md sm:w-auto"
        >
          <span className="text-lg leading-none">+</span> New Work Order
        </button>
      </div>

      {/* Filters */}
      <div className="erp-surface flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:px-6">
        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Filter by status</span>
        <div className="flex gap-2 flex-wrap">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s || 'ALL'}
              onClick={() => setStatusFilter(s)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="erp-surface p-5 sm:p-6">
        {loading && (
          <div className="flex h-40 items-center justify-center text-sm text-slate-500 animate-pulse">
            Loading work orders…
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && orders.length === 0 && (
          <div className="flex h-48 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50">
            <div className="text-4xl">📋</div>
            <p className="text-sm text-slate-500">No work orders found.</p>
            <button
              onClick={() => navigate('new')}
              className="text-xs font-medium text-blue-600 hover:underline"
            >
              Create your first work order
            </button>
          </div>
        )}

        {!loading && orders.length > 0 && (
          <ResponsiveDataList
            data={orders}
            getRowKey={(wo) => wo.id}
            onRowClick={(wo) => navigate(wo.id)}
            columns={[
              {
                key: 'wo_number',
                header: 'WO #',
                cell: (wo) => <span className="font-mono font-medium text-blue-700">{wo.wo_number}</span>,
              },
              {
                key: 'product',
                header: 'Product',
                cell: (wo) => (
                  <div>
                    <div className="font-medium text-slate-900">{wo.product_name || 'N/A'}</div>
                    {wo.product_code && <div className="text-xs text-slate-500">{wo.product_code}</div>}
                  </div>
                ),
              },
              {
                key: 'status',
                header: 'Status',
                cell: (wo) => (
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[wo.status]}`}>
                    {wo.status.replace('_', ' ')}
                  </span>
                ),
              },
              {
                key: 'priority',
                header: 'Priority',
                cell: (wo) => <span className={`text-xs font-medium ${PRIORITY_COLORS[wo.priority]}`}>{wo.priority}</span>,
              },
              {
                key: 'planned_quantity',
                header: 'Qty Planned',
                cell: (wo) => <span className="tabular-nums">{Number(wo.planned_quantity).toFixed(3)}</span>,
              },
              {
                key: 'produced_quantity',
                header: 'Qty Produced',
                cell: (wo) => <span className="tabular-nums text-emerald-600">{Number(wo.produced_quantity).toFixed(3)}</span>,
              },
              {
                key: 'due_date',
                header: 'Due Date',
                cell: (wo) => <span className="text-slate-600">{wo.due_date}</span>,
              },
              {
                key: 'created_at',
                header: 'Created',
                cell: (wo) => <span className="text-xs text-slate-500">{new Date(wo.created_at).toLocaleDateString()}</span>,
              },
            ]}
            renderMobileCard={(wo) => (
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:shadow-md" onClick={() => navigate(wo.id)}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-base font-semibold text-blue-700">{wo.wo_number}</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{wo.product_name || 'N/A'}</p>
                    {wo.product_code && <p className="text-xs text-slate-500">{wo.product_code}</p>}
                    <p className={`mt-1 text-xs font-medium ${PRIORITY_COLORS[wo.priority]}`}>{wo.priority} priority</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[wo.status]}`}>
                    {wo.status.replace('_', ' ')}
                  </span>
                </div>
                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between gap-3">
                    <span className="text-slate-500">Qty planned</span>
                    <span className="tabular-nums">{Number(wo.planned_quantity).toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-slate-500">Qty produced</span>
                    <span className="tabular-nums text-emerald-600">{Number(wo.produced_quantity).toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-slate-500">Due date</span>
                    <span>{wo.due_date}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-slate-500">Created</span>
                    <span>{new Date(wo.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            )}
          />
        )}
      </div>
    </div>
  );
}
