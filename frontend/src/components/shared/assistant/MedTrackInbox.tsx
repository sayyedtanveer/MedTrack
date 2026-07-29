import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { InboxProvider } from '@/lib/assistant/providers/InboxProvider';
import { NextActionCard } from './NextActionCard';
import { usePermissions } from '@/hooks/usePermissions';
import { Inbox, CheckCircle } from 'lucide-react';
import apiClient from '@/services/api-client';

export function MedTrackInbox() {
  const { role } = usePermissions();

  // Parallel fetch all major queue items
  // Note: For a true scalable ERP, these would be lightweight summary endpoints or a dedicated '/inbox' BFF endpoint.
  // We use the existing endpoints here for the demonstration.

  const { data: salesOrders = [] } = useQuery({
    queryKey: ['sales-orders-inbox'],
    queryFn: async () => {
      const res = await apiClient.get('/sales/orders');
      return res.data?.items || res.data || [];
    },
    staleTime: 30000
  });

  const { data: purchaseOrders = [] } = useQuery({
    queryKey: ['purchase-orders-inbox'],
    queryFn: async () => {
      const res = await apiClient.get('/purchase-orders');
      return res.data?.items || res.data || [];
    },
    staleTime: 30000
  });

  const { data: workOrders = [] } = useQuery({
    queryKey: ['work-orders-inbox'],
    queryFn: async () => {
      const res = await apiClient.get('/work-orders');
      return res.data?.items || res.data || [];
    },
    staleTime: 30000
  });

  const { data: qcInspection = [] } = useQuery({
    queryKey: ['qc-inspection-inbox'],
    queryFn: async () => {
      const res = await apiClient.get('/work-orders/qc/inspection-queue');
      return res.data?.items || res.data || [];
    },
    staleTime: 30000
  });

  const { data: qcRejected = [] } = useQuery({
    queryKey: ['qc-rejected-inbox'],
    queryFn: async () => {
      const res = await apiClient.get('/work-orders/qc/rejected-queue');
      return res.data?.items || res.data || [];
    },
    staleTime: 30000
  });

  const { data: dispatchQueue = [] } = useQuery({
    queryKey: ['dispatch-queue-inbox'],
    queryFn: async () => {
      const res = await apiClient.get('/delivery/dispatch-queue');
      const data = res.data?.items || res.data || [];
      // If endpoint doesn't pre-filter, filter here
      return data.filter((so: any) => so.status === 'CONFIRMED' || so.status === 'PARTIAL_DISPATCH');
    },
    staleTime: 30000
  });

  const allGuidance = useMemo(() => {
    // Decorate items with type identifiers so providers can recognize them
    const mappedSO = salesOrders.map((so: any) => ({ ...so, type: 'sales_order' }));
    const mappedPO = purchaseOrders
      .filter((po: any) => {
        if (['sent', 'acknowledged', 'partial'].includes(po.status?.toLowerCase())) {
          if (po.lines && po.lines.length > 0) {
            return po.lines.some((l: any) => (l.received_quantity || 0) < l.quantity);
          }
        }
        return true;
      })
      .map((po: any) => ({ ...po, type: 'purchase_order' }));
    
    const mappedWO = workOrders.map((wo: any) => ({ ...wo, type: 'work_order' }));
    const mappedQCInsp = qcInspection.map((qc: any) => ({ ...qc, type: 'qc_batch', status: 'QC_PENDING' }));
    const mappedQCRej = qcRejected.map((qc: any) => ({ ...qc, type: 'qc_batch', status: 'QC_REJECTED' }));
    const mappedDispatch = dispatchQueue.map((so: any) => ({ ...so, type: 'dispatch_order' }));

    const allEntities = [
      ...mappedSO,
      ...mappedPO,
      ...mappedWO,
      ...mappedQCInsp,
      ...mappedQCRej,
      ...mappedDispatch
    ];

    const userRoles = role ? [role] : [];
    
    const filteredGuidance = InboxProvider.getInbox(allEntities, userRoles)
      .filter(g => g.priority !== 'low' && g.priority !== 'info');

    return filteredGuidance;
  }, [salesOrders, purchaseOrders, workOrders, qcInspection, qcRejected, dispatchQueue, role]);

  if (allGuidance.length === 0) {
    return (
      <div className="erp-surface p-6 flex flex-col items-center justify-center text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
          <CheckCircle className="w-6 h-6 text-emerald-500" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-900">Inbox Zero</h3>
          <p className="text-sm text-slate-500">You have no pending tasks requiring your attention today.</p>
        </div>
      </div>
    );
  }

  // Take top 4 highest priority items for the dashboard
  const topGuidance = allGuidance.slice(0, 4);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Inbox className="w-5 h-5 text-blue-600" />
          Today's Inbox
          <span className="bg-blue-100 text-blue-700 text-xs py-0.5 px-2 rounded-full font-medium">
            {allGuidance.length} Tasks
          </span>
        </h2>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {topGuidance.map((guidance, idx) => (
          <NextActionCard key={`inbox-item-${idx}`} guidance={guidance} isInbox={true} />
        ))}
      </div>
      
      {allGuidance.length > 4 && (
        <div className="text-center pt-2">
          <button className="text-sm font-medium text-blue-600 hover:text-blue-700">
            View All {allGuidance.length} Tasks &rarr;
          </button>
        </div>
      )}
    </div>
  );
}
