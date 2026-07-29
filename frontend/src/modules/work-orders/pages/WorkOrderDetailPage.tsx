import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { REALTIME_EVENT_NAME } from '@/components/notifications/RealtimeNotificationsBridge';
import workOrderService, {
  type WorkOrderDetail,
  type WorkOrderMaterial,
  type JobCard,
} from '@/services/work-order.service';
import { documentService } from '@/services/document.service';
import { auditService } from '@/services/audit.service';
import { WO_STATUS_COLORS } from '../components/WorkOrderStatusConfig';
import { WO_STATUS_ACTIONS, type WorkOrderAction } from '../components/WorkOrderActionConfig';
import { useToast } from '@/hooks/use-toast';
import { AuditHistoryTab } from '@/components/shared/AuditHistoryTab';
import { usePermissions } from '@/hooks/usePermissions';
import { AssistantEngine } from '@/lib/assistant/AssistantEngine';
import { MedTrackAssistant } from '@/components/shared/assistant/MedTrackAssistant';
import { AssistantButton } from '@/components/shared/assistant/AssistantButton';

const STATUS_COLORS = WO_STATUS_COLORS;

const JC_STATUS: Record<string, string> = {
  PENDING: 'bg-slate-100 text-slate-600',
  IN_PROGRESS: 'bg-amber-100 text-amber-700',
  DONE: 'bg-emerald-100 text-emerald-700',
};

export default function WorkOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [wo, setWo] = useState<WorkOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [productionPending, setProductionPending] = useState(false);
  const [tab, setTab] = useState<'materials' | 'job-cards' | 'audit'>('materials');
  const [productionDraft, setProductionDraft] = useState({
    produced_quantity: '',
    scrap_quantity: '0',
    notes: '',
  });
  const [documentLoading, setDocumentLoading] = useState(false);
  
  // Dialog states for QC actions
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [scrapDialogOpen, setScrapDialogOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [scrapReason, setScrapReason] = useState('');
  
  // Production Hold Dialog (Requirement 26.1, 26.2)
  const [holdDialogOpen, setHoldDialogOpen] = useState(false);
  const [holdReason, setHoldReason] = useState('');
  
  // Cancellation Dialog (Requirement 18.5, 18.6, 18.7)
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  
  // Rework count
  const [reworkCount, setReworkCount] = useState(0);

  // Material availability preview for pending state
  const [availabilityPreview, setAvailabilityPreview] = useState<any>(null);

  const { isAdmin, isQc, isOperator, isManager } = usePermissions();

  const load = useCallback(async (silent = false) => {
    if (!id) return;
    if (!silent) setLoading(true);
    setError(null);
    try {
      const res = await workOrderService.get(id);
      setWo(res.data);
      
      // Load availability preview if pending
      if (res.data.status === 'MATERIAL_PENDING') {
        try {
          const availRes = await workOrderService.checkMaterialAvailability({
            product_id: res.data.product_id,
            bom_id: res.data.bom_id,
            quantity: Number(res.data.planned_quantity),
          });
          setAvailabilityPreview(availRes.data);
        } catch {
          // Ignore
        }
      }

      // Load rework count from audit logs (Requirement 12.4)
      if (res.data.status === 'REWORK' || res.data.status === 'QC_REJECTED') {
        try {
          const auditRes = await auditService.getAuditLogs({
            entity_id: id,
            entity_type: 'work_order',
            action: 'qc_rework',
            limit: 100,
          });
          const count = auditRes.items.length;
          setReworkCount(Math.min(count, 99)); // Cap at 99 per requirement 12.4
        } catch {
          // Ignore audit log errors, just keep count at 0
        }
      }
    } catch {
      setError('Failed to load work order.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const handleRealtime = () => {
      void load(true);
    };
    window.addEventListener(REALTIME_EVENT_NAME, handleRealtime);
    return () => window.removeEventListener(REALTIME_EVENT_NAME, handleRealtime);
  }, [load]);

  const handleAction = async (actionKey: string) => {
    if (!id || actionPending) return;
    
    // Show dialogs for actions that need input
    if (actionKey === 'qc_reject') {
      setRejectDialogOpen(true);
      return;
    }
    if (actionKey === 'scrap') {
      setScrapDialogOpen(true);
      return;
    }
    // Production Hold: show reason dialog (Requirement 26.1)
    if (actionKey === 'hold') {
      setHoldDialogOpen(true);
      return;
    }
    // Cancellation: show confirmation dialog (Requirement 18.5, 18.6)
    if (actionKey === 'cancel') {
      setCancelDialogOpen(true);
      return;
    }
    
    setActionPending(true);
    setError(null);
    
    try {
      switch (actionKey) {
        case 'release':
          await workOrderService.release(id);
          break;
        case 'allocate_materials':
          const { data: allocateRes } = await workOrderService.allocateMaterials(id);
          if (allocateRes.status === 'MATERIAL_PENDING') {
            toast({ title: 'Allocation Incomplete', description: 'Insufficient stock in warehouse to allocate all materials. Please add stock.', variant: 'destructive' });
          } else {
            toast({ title: 'Materials Allocated', description: 'Stock has been successfully reserved for this work order.' });
          }
          break;
        case 'start':
          await workOrderService.start(id);
          break;
        case 'complete':
          await workOrderService.complete(id);
          break;
        case 'close':
          await workOrderService.close(id);
          break;
        case 'qc_approve':
          await workOrderService.qcApprove(id);
          toast({ title: 'QC Approved', description: 'Work order passed quality inspection.' });
          break;
        case 'send_to_rework':
          await workOrderService.sendToRework(id);
          toast({ title: 'Sent to Rework', description: 'Work order status updated to REWORK.' });
          break;
        case 'receive_fg':
          await workOrderService.receiveFG(id);
          toast({ title: 'FG Received', description: 'Finished goods have been received into inventory.' });
          break;
        case 'start_rework':
          // Rework production uses same form as regular production
          toast({ title: 'Rework Production', description: 'Use the production form below to record rework quantities.' });
          setActionPending(false);
          return;
        case 'resume':
          await workOrderService.resume(id);
          toast({ title: 'Production Resumed', description: 'Work order is back in production.' });
          break;
        default:
          setError(`Unknown action: ${actionKey}`);
          setActionPending(false);
          return;
      }
      
      // Reload WO status within 2 seconds (Requirement 6.2)
      setTimeout(() => {
        void load();
      }, 500);
      
    } catch (e: any) {
      const msg = e?.response?.data?.error_code === 'MATERIAL_NOT_ISSUED'
        ? 'Record production before completing this work order.'
        : e?.response?.data?.message || 'Action failed.';
      setError(msg);
      toast({ 
        title: 'Action Failed', 
        description: msg,
        variant: 'destructive' 
      });
    } finally {
      setActionPending(false);
    }
  };

  const handleQCReject = async () => {
    if (!id || !rejectReason.trim()) {
      setError('Rejection reason is required (1-500 characters).');
      return;
    }
    
    if (rejectReason.length < 1 || rejectReason.length > 500) {
      setError('Rejection reason must be between 1 and 500 characters.');
      return;
    }
    
    setActionPending(true);
    setError(null);
    
    try {
      await workOrderService.qcReject(id, { reason: rejectReason });
      toast({ title: 'QC Rejected', description: 'Work order has been rejected and requires rework or scrapping.' });
      setRejectDialogOpen(false);
      setRejectReason('');
      setTimeout(() => {
        void load();
      }, 500);
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to reject QC.';
      setError(msg);
      toast({ title: 'QC Reject Failed', description: msg, variant: 'destructive' });
    } finally {
      setActionPending(false);
    }
  };

  const handleScrap = async () => {
    if (!id || !scrapReason.trim()) {
      setError('Scrap reason is required (1-500 characters).');
      return;
    }
    
    if (scrapReason.length < 1 || scrapReason.length > 500) {
      setError('Scrap reason must be between 1 and 500 characters.');
      return;
    }
    
    setActionPending(true);
    setError(null);
    
    try {
      await workOrderService.scrap(id, { reason: scrapReason });
      toast({ title: 'Batch Scrapped', description: 'Work order has been scrapped and closed.' });
      setScrapDialogOpen(false);
      setScrapReason('');
      setTimeout(() => {
        void load();
      }, 500);
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to scrap batch.';
      setError(msg);
      toast({ title: 'Scrap Failed', description: msg, variant: 'destructive' });
    } finally {
      setActionPending(false);
    }
  };

  // Handle Production Hold (Report Machine Breakdown) — Requirement 26.1
  const handleHold = async () => {
    if (!id || !holdReason.trim()) {
      setError('Hold reason is required.');
      return;
    }
    setActionPending(true);
    setError(null);
    try {
      await workOrderService.hold(id, { reason: holdReason });
      toast({ title: 'Production Hold', description: 'Work order has been put on hold.' });
      setHoldDialogOpen(false);
      setHoldReason('');
      setTimeout(() => void load(), 500);
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to put work order on hold.';
      setError(msg);
      toast({ title: 'Hold Failed', description: msg, variant: 'destructive' });
    } finally {
      setActionPending(false);
    }
  };

  // Handle Cancellation — Requirement 18.5, 18.6, 18.7
  const handleCancel = async () => {
    if (!id) return;
    setActionPending(true);
    setError(null);
    try {
      await workOrderService.cancel(id, cancelReason || undefined);
      toast({ title: 'Work Order Cancelled', description: 'Reservations released and work order cancelled.' });
      setCancelDialogOpen(false);
      setCancelReason('');
      setTimeout(() => void load(), 500);
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to cancel work order.';
      setError(msg);
      toast({ title: 'Cancel Failed', description: msg, variant: 'destructive' });
    } finally {
      setActionPending(false);
    }
  };

  const handleIssueMaterial = async (material: WorkOrderMaterial) => {
    if (!id || actionPending) return;
    
    const remainingQty = Number(material.required_quantity) - Number(material.issued_quantity);
    
    if (remainingQty <= 0) {
      toast({ title: 'Already Issued', description: 'This material has been fully issued.', variant: 'destructive' });
      return;
    }
    
    setActionPending(true);
    setError(null);
    
    try {
      await workOrderService.issueMaterial(id, {
        material_id: material.material_id,
        quantity: remainingQty,
        unit_id: material.unit_id,
      });
      toast({ title: 'Material Issued', description: `${remainingQty.toFixed(3)} units issued successfully.` });
      // Refresh materials table without full page reload (Requirement 9.3)
      setTimeout(() => {
        void load(true);
      }, 500);
    } catch (e: any) {
      const msg = e?.response?.data?.error_code === 'INSUFFICIENT_STOCK'
        ? 'Insufficient stock available for this material.'
        : e?.response?.data?.error_code === 'INVALID_STATUS_TRANSITION'
        ? 'Work order is not in the correct status for material issue.'
        : e?.response?.data?.message || 'Failed to issue material.';
      setError(msg);
      toast({ title: 'Material Issue Failed', description: msg, variant: 'destructive' });
    } finally {
      setActionPending(false);
    }
  };

  const handleRecordProduction = async () => {
    if (!id || productionPending) return;

    const producedQuantity = Number(productionDraft.produced_quantity);
    const scrapQuantity = Number(productionDraft.scrap_quantity || 0);

    // Client-side validation (Requirement 8.7)
    if (!Number.isFinite(producedQuantity) || producedQuantity <= 0) {
      setError('Produced quantity must be greater than zero.');
      toast({ title: 'Validation Error', description: 'Produced quantity must be greater than zero.', variant: 'destructive' });
      return;
    }

    if (!Number.isFinite(scrapQuantity) || scrapQuantity < 0) {
      setError('Scrap quantity cannot be negative.');
      toast({ title: 'Validation Error', description: 'Scrap quantity cannot be negative.', variant: 'destructive' });
      return;
    }
    
    // Notes max 500 chars (Requirement 10.4)
    if (productionDraft.notes.length > 500) {
      setError('Notes cannot exceed 500 characters.');
      toast({ title: 'Validation Error', description: 'Notes cannot exceed 500 characters.', variant: 'destructive' });
      return;
    }

    setProductionPending(true);
    setError(null);
    try {
      await workOrderService.recordProduction(id, {
        produced_quantity: producedQuantity,
        scrap_quantity: scrapQuantity,
        notes: productionDraft.notes.trim() || undefined,
      });
      // Clear form on success (Requirement 8.2)
      setProductionDraft({
        produced_quantity: '',
        scrap_quantity: '0',
        notes: '',
      });
      toast({ title: 'Production Recorded', description: 'Production quantities have been saved successfully.' });
      await load();
    } catch (e: any) {
      // Preserve form on failure (Requirement 8.3)
      const msg = e?.response?.data?.message || 'Failed to record production.';
      setError(msg);
      toast({ title: 'Production Recording Failed', description: msg, variant: 'destructive' });
    } finally {
      setProductionPending(false);
    }
  };

  const handleSubmitForQC = async () => {
    if (!id || actionPending) return;
    
    if (!wo || Number(wo.produced_quantity) <= 0) {
      setError('Record production before submitting for QC.');
      toast({ title: 'Cannot Submit for QC', description: 'Record production before submitting for QC.', variant: 'destructive' });
      return;
    }
    
    setActionPending(true);
    setError(null);
    
    try {
      await workOrderService.complete(id); // This transitions to QC_PENDING (Requirement 8.5)
      toast({ title: 'Submitted for QC', description: 'Work order is now pending quality inspection.' });
      setTimeout(() => {
        void load();
      }, 500);
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to submit for QC.';
      setError(msg);
      toast({ title: 'QC Submission Failed', description: msg, variant: 'destructive' });
    } finally {
      setActionPending(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!id || documentLoading) return;
    setDocumentLoading(true);
    setError(null);
    try {
      // Generate document
      const document = await documentService.generateDocument('work_order', id);
      // Download the PDF
      await documentService.downloadDocumentByUrl(document.id, `WO-${wo?.wo_number}.pdf`);
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to generate PDF.';
      setError(msg);
    } finally {
      setDocumentLoading(false);
    }
  };

  const handlePrintPDF = async () => {
    if (!id || documentLoading) return;
    setDocumentLoading(true);
    setError(null);
    try {
      // Generate document
      const document = await documentService.generateDocument('work_order', id);
      // Get preview URL
      const previewUrl = await documentService.previewDocument(document.id);
      // Open in new window for printing
      const printWindow = window.open(previewUrl, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
        };
      }
    } catch (e: any) {
      const msg = e?.response?.data?.message || 'Failed to generate PDF for printing.';
      setError(msg);
    } finally {
      setDocumentLoading(false);
    }
  };

  if (loading) return (
    <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-200 bg-white text-sm text-slate-500 shadow-sm animate-pulse">
      Loading…
    </div>
  );

  if (!wo) return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      {error || 'Work order not found.'}
    </div>
  );

  // Get actions from WO_STATUS_ACTIONS config (Requirement 10.1)
  let actions = WO_STATUS_ACTIONS[wo.status] || [];
  
  // Filter actions based on roles
  actions = actions.filter((action) => {
    if (isAdmin()) return true; // Admin can do everything

    // QC specific actions
    if (action.actionKey === 'qc_approve' || action.actionKey === 'qc_reject') {
      return isQc();
    }
    
    // Rework / scrap actions
    if (action.actionKey === 'send_to_rework' || action.actionKey === 'scrap') {
      return isQc() || isManager();
    }

    // Default: allow operator and manager to do other production steps
    return isOperator() || isManager();
  });

  // Calculate expected FG quantity (Requirement 10.5)
  const expectedFGQty = Number(wo.produced_quantity) - Number(wo.scrap_quantity);
  
  // Apply dynamic disabled states (Task 10.8)
  actions = actions.map((action) => {
    // Receive FG button: disabled when FG qty <= 0 (Property 9)
    if (action.actionKey === 'receive_fg' && expectedFGQty <= 0) {
      return { ...action, disabled: true };
    }
    // Complete button: disabled when produced <= 0
    if (action.actionKey === 'complete' && Number(wo.produced_quantity) <= 0) {
      return { ...action, disabled: true };
    }
    return { ...action, disabled: false };
  });
  
  // Check if all materials issued (Requirement 9.4)
  const allMaterialsIssued = wo.materials.length > 0 && wo.materials.every(
    (m) => Number(m.issued_quantity) >= Number(m.required_quantity)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="erp-surface px-5 py-5 sm:px-6">
        <div className="flex items-center gap-3 mb-1">
          <button onClick={() => navigate('/work-orders')} className="text-xs font-medium text-slate-500 hover:text-slate-900">
            Back to Work Orders
          </button>
        </div>
        
        {(() => {
          const guidance = AssistantEngine.getGuidance(wo);
          return guidance ? (
            <div className="mb-4">
              <MedTrackAssistant guidance={guidance} />
            </div>
          ) : null;
        })()}

        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Manufacturing execution</p>
            <h1 className="mt-2 text-2xl font-semibold font-mono text-slate-900">{wo.wo_number}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[wo.status]}`}>
                {wo.status.replace(/_/g, ' ')}
              </span>
              {(wo.status === 'REWORK' || wo.status === 'QC_REJECTED') && reworkCount > 0 && (
                <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold bg-orange-100 text-orange-700">
                  Rework #{reworkCount}
                </span>
              )}
              <span className="text-xs text-slate-500">Priority: <span className="text-slate-800">{wo.priority}</span></span>
              <span className="text-xs text-slate-500">Due: <span className="text-slate-800">{wo.due_date}</span></span>
            </div>
            {(wo.status === 'REWORK' || wo.status === 'QC_REJECTED') && reworkCount >= 10 && (
              <div className="mt-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
                ⚠️ This batch has been sent to rework {reworkCount} times. Consider scrapping it.
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handlePrintPDF}
              disabled={documentLoading}
              className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              {documentLoading ? '…' : 'Print'}
            </button>
            <button
              onClick={handleDownloadPDF}
              disabled={documentLoading}
              className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              {documentLoading ? '…' : 'Download PDF'}
            </button>
      {/* Action Buttons per status config */}
            {actions.map((a: WorkOrderAction) => (
              <AssistantButton
                key={a.actionKey}
                id={`btn-wo-${a.actionKey}`}
                onClick={() => handleAction(a.actionKey)}
                disabled={actionPending}
                className={a.color}
                pulse={AssistantEngine.getGuidance(wo)?.pulseActionId === a.actionKey}
              >
                {actionPending ? '…' : a.label}
              </AssistantButton>
            ))}
            {/* Submit for QC - shown when IN_PRODUCTION and has produced qty */}
            {wo.status === 'IN_PRODUCTION' && Number(wo.produced_quantity) > 0 && (isAdmin() || isOperator() || isManager()) && (
              <AssistantButton
                id="btn-wo-submit-qc"
                onClick={handleSubmitForQC}
                disabled={actionPending}
                className="bg-cyan-600 hover:bg-cyan-700 text-white"
                pulse={AssistantEngine.getGuidance(wo)?.pulseActionId === 'submit_qc'}
              >
                {actionPending ? '…' : 'Submit for QC'}
              </AssistantButton>
            )}
            {/* Report Machine Breakdown - shown when IN_PRODUCTION (Requirement 26.1) */}
            {wo.status === 'IN_PRODUCTION' && (isAdmin() || isOperator() || isManager()) && (
              <AssistantButton
                id="btn-wo-hold"
                onClick={() => handleAction('hold')}
                disabled={actionPending}
                className="bg-rose-600 hover:bg-rose-700 text-white"
              >
                {actionPending ? '…' : 'Report Machine Breakdown'}
              </AssistantButton>
            )}
            {/* Cancel button for cancellable statuses (Requirement 18.5) */}
            {(wo.status === 'PLANNED' || wo.status === 'RELEASED' || wo.status === 'MATERIAL_PENDING' || wo.status === 'MATERIAL_RESERVED') && (isAdmin() || isManager()) && (
              <AssistantButton
                variant="outline"
                id="btn-wo-cancel"
                onClick={() => handleAction('cancel')}
                disabled={actionPending}
                className="border-red-300 text-red-700 hover:bg-red-50"
              >
                Cancel
              </AssistantButton>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'Planned Qty', value: Number(wo.planned_quantity).toFixed(3), color: 'text-slate-900' },
          { label: 'Produced', value: Number(wo.produced_quantity).toFixed(3), color: 'text-emerald-600' },
          { label: 'Scrap', value: Number(wo.scrap_quantity).toFixed(3), color: 'text-red-600' },
          { label: 'Expected FG', value: expectedFGQty.toFixed(3), color: wo.status === 'QC_APPROVED' ? 'text-teal-600' : 'text-blue-600' },
        ].map((c) => (
          <div key={c.label} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{c.label}</p>
            <p className={`text-2xl font-semibold mt-1 tabular-nums ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      {/* Production Hold Display (Requirement 26.2, 26.7) */}
      {wo.status === 'PRODUCTION_HOLD' && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 rounded-full bg-rose-100 p-2">
              <svg className="h-5 w-5 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-rose-900">Production Hold</h3>
              <p className="text-sm text-rose-700 mt-1">
                <span className="font-medium">Reason:</span> {wo.hold_reason || 'No reason specified'}
              </p>
              {wo.hold_started_at && (
                <p className="text-xs text-rose-600 mt-1">
                  On hold since: {new Date(wo.hold_started_at).toLocaleString()} ({Math.floor((Date.now() - new Date(wo.hold_started_at).getTime()) / (1000 * 60 * 60))} hours ago)
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Material Issue UI (Requirement 10.3) */}
      {(wo.status === 'MATERIAL_RESERVED' || wo.status === 'MATERIAL_PENDING') && wo.materials.length > 0 && (
        <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
            <h2 className="text-sm font-semibold text-slate-900">Material Issue</h2>
            <p className="mt-1 text-xs text-slate-500">Issue materials to work order before starting production</p>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.18em] text-slate-500">
              <tr>
                <th className="px-4 py-3">Material Code</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Required</th>
                {wo.status === 'MATERIAL_PENDING' && <th className="px-4 py-3 text-amber-600">Shortage</th>}
                <th className="px-4 py-3">Issued</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {wo.materials.map((m: WorkOrderMaterial) => {
                const remaining = Number(m.required_quantity) - Number(m.issued_quantity);
                const canIssue = remaining > 0 && wo.status === 'MATERIAL_RESERVED';
                const availLine = availabilityPreview?.lines?.find((l: any) => l.material_id === m.material_id);
                
                return (
                  <tr key={m.id}>
                    <td className="px-4 py-3 font-mono text-xs">{m.material_code}</td>
                    <td className="px-4 py-3 text-xs">{m.material_name}</td>
                    <td className="px-4 py-3 tabular-nums">{Number(m.required_quantity).toFixed(3)}</td>
                    {wo.status === 'MATERIAL_PENDING' && (
                      <td className="px-4 py-3 tabular-nums text-amber-600 font-medium">
                        {availLine && Number(availLine.shortage_quantity) > 0 ? Number(availLine.shortage_quantity).toFixed(3) : '0.000'}
                      </td>
                    )}
                    <td className="px-4 py-3 tabular-nums text-emerald-600">{Number(m.issued_quantity).toFixed(3)}</td>
                    <td className="px-4 py-3">
                      {canIssue ? (
                        <button
                          onClick={() => handleIssueMaterial(m)}
                          disabled={actionPending}
                          className="rounded-lg px-3 py-1.5 text-xs font-medium bg-violet-600 hover:bg-violet-700 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Issue {remaining.toFixed(3)}
                        </button>
                      ) : remaining > 0 ? (
                        <span className="text-xs text-slate-500 font-medium italic">Pending Allocation</span>
                      ) : (
                        <span className="text-xs text-emerald-600 font-medium">✓ Issued</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {allMaterialsIssued && (
            <div className="px-4 py-3 bg-emerald-50 border-t border-emerald-200">
              <p className="text-xs text-emerald-700">✓ All materials issued. You can now start production.</p>
            </div>
          )}
        </div>
      )}

      {/* Production Recording UI (Requirement 10.4) */}
      {(wo.status === 'IN_PRODUCTION' || wo.status === 'MATERIAL_ISSUED' || wo.status === 'REWORK') && (
        <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                {wo.status === 'REWORK' ? 'Record Rework Production' : 'Record Production'}
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                {wo.status === 'MATERIAL_ISSUED' 
                  ? 'Start production before recording output'
                  : 'Enter produced and scrap quantities (max 500 chars for notes)'}
              </p>
            </div>
            {wo.status === 'MATERIAL_ISSUED' && (
              <button
                onClick={() => handleAction('start')}
                disabled={actionPending}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-purple-600 hover:bg-purple-700 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              >
                {actionPending ? '…' : 'Start Production'}
              </button>
            )}
          </div>

          {(wo.status === 'IN_PRODUCTION' || wo.status === 'REWORK') && (
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400">Produced Qty*</label>
                <input
                  id="wo-produced-quantity"
                  type="number"
                  min="0.001"
                  step="0.001"
                  value={productionDraft.produced_quantity}
                  onChange={(e) =>
                    setProductionDraft((curr) => ({
                      ...curr,
                      produced_quantity: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                  placeholder="Must be > 0"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400">Scrap Qty</label>
                <input
                  id="wo-scrap-quantity"
                  type="number"
                  min="0"
                  step="0.001"
                  value={productionDraft.scrap_quantity}
                  onChange={(e) =>
                    setProductionDraft((curr) => ({
                      ...curr,
                      scrap_quantity: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                  placeholder="Must be ≥ 0"
                />
              </div>
              <div className="flex items-end">
                <button
                  id="btn-record-production"
                  onClick={handleRecordProduction}
                  disabled={productionPending}
                  className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:from-blue-700 hover:to-blue-800 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {productionPending ? 'Saving…' : 'Record Production'}
                </button>
              </div>
              <div className="md:col-span-3">
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400">Notes (optional, max 500 chars)</label>
                <textarea
                  id="wo-production-notes"
                  value={productionDraft.notes}
                  onChange={(e) =>
                    setProductionDraft((curr) => ({
                      ...curr,
                      notes: e.target.value,
                    }))
                  }
                  maxLength={500}
                  rows={3}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                  placeholder="Optional production notes"
                />
                <p className="mt-1 text-xs text-slate-400">{productionDraft.notes.length}/500</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tabs — ARIA role="tablist" for screen reader navigation (Req 56.1) */}
      <div>
        <div role="tablist" aria-label="Work order sections" className="flex gap-1 border-b border-slate-200">
          {(['materials', 'job-cards', 'audit'] as const).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              aria-controls={`tabpanel-${t}`}
              id={`tab-${t}`}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                tab === t ? 'border-b-2 border-blue-600 text-slate-900' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {t === 'materials' ? 'Materials' : t === 'job-cards' ? 'Job Cards' : 'Audit'}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="pt-1">
        {tab === 'materials' && (
          <div role="tabpanel" id="tabpanel-materials" aria-labelledby="tab-materials" className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm">
            {wo.materials.length === 0 ? (
              <p className="p-6 text-center text-sm text-slate-500">No materials attached.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.18em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Material Code</th>
                    <th className="px-4 py-3">Required</th>
                    <th className="px-4 py-3">Issued</th>
                    <th className="px-4 py-3">Remaining</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {wo.materials.map((m: WorkOrderMaterial) => {
                    const remaining = Number(m.required_quantity) - Number(m.issued_quantity);
                    const fullyIssued = remaining <= 0;
                    return (
                      <tr key={m.id}>
                        <td className="px-4 py-3">
                          <div className="font-mono text-xs text-slate-900">{m.material_code}</div>
                          <div className="text-xs text-slate-500">{m.material_name}</div>
                        </td>
                        <td className="px-4 py-3 tabular-nums">{Number(m.required_quantity).toFixed(3)}</td>
                        <td className="px-4 py-3 tabular-nums text-emerald-600">{Number(m.issued_quantity).toFixed(3)}</td>
                        <td className={`px-4 py-3 tabular-nums ${remaining > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                          {remaining.toFixed(3)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs ${fullyIssued ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                            {fullyIssued ? 'Fully Issued' : 'Pending'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === 'job-cards' && (
          <div className="space-y-3">
            {wo.job_cards.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">No job cards attached.</p>
            ) : (
              wo.job_cards.map((jc: JobCard) => (
                <div key={jc.id} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
                      {jc.sequence}
                    </span>
                    <div>
                      <p className="font-mono text-sm font-medium text-slate-900">OP-{jc.sequence} {jc.operation_name}</p>
                      {jc.started_at && (
                        <p className="text-xs text-slate-500">
                          Started: {new Date(jc.started_at).toLocaleString()}
                        </p>
                      )}
                      {jc.completed_at && (
                        <p className="text-xs text-emerald-600">
                          Done: {new Date(jc.completed_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold shrink-0 ${JC_STATUS[jc.status]}`}>
                    {jc.status.replace('_', ' ')}
                  </span>
                </div>
              ))
            )}
            {wo.status === 'IN_PRODUCTION' && (
              <p className="mt-2 text-center text-xs text-slate-500">
                Go to <button onClick={() => navigate(`/shop-floor/${id}/job-cards`)} className="font-medium text-blue-600 hover:underline">Shop Floor</button> to start or complete individual operations.
              </p>
            )}
          </div>
        )}

        {/* Audit Tab Content (Req 24.3, 24.4, 24.5, 24.6) */}
        {tab === 'audit' && (
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
            <AuditHistoryTab entityType="work_order" entityId={id || ''} />
          </div>
        )}
      </div>

      {/* QC Reject Dialog (Requirement 10.5) */}
      {rejectDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900">Reject QC</h3>
              <p className="text-sm text-slate-500 mt-1">Provide a reason for rejection (1-500 characters)</p>
            </div>
            <div className="px-6 py-4">
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={4}
                maxLength={500}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                placeholder="Enter rejection reason..."
                autoFocus
              />
              <p className="mt-1 text-xs text-slate-400">{rejectReason.length}/500</p>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex gap-2 justify-end">
              <button
                onClick={() => {
                  setRejectDialogOpen(false);
                  setRejectReason('');
                }}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleQCReject}
                disabled={!rejectReason.trim() || actionPending}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              >
                {actionPending ? 'Rejecting…' : 'Reject QC'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Scrap Dialog (Requirement 10.5) */}
      {scrapDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900">Scrap Batch</h3>
              <p className="text-sm text-slate-500 mt-1">Provide a reason for scrapping (1-500 characters)</p>
            </div>
            <div className="px-6 py-4">
              <textarea
                value={scrapReason}
                onChange={(e) => setScrapReason(e.target.value)}
                rows={4}
                maxLength={500}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                placeholder="Enter scrap reason..."
                autoFocus
              />
              <p className="mt-1 text-xs text-slate-400">{scrapReason.length}/500</p>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex gap-2 justify-end">
              <button
                onClick={() => {
                  setScrapDialogOpen(false);
                  setScrapReason('');
                }}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleScrap}
                disabled={!scrapReason.trim() || actionPending}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              >
                {actionPending ? 'Scrapping…' : 'Scrap Batch'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Production Hold Dialog (Requirement 26.1) */}
      {holdDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900">Report Machine Breakdown</h3>
              <p className="text-sm text-slate-500 mt-1">Enter reason for production hold</p>
            </div>
            <div className="px-6 py-4">
              <textarea
                value={holdReason}
                onChange={(e) => setHoldReason(e.target.value)}
                rows={3}
                maxLength={500}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                placeholder="E.g., Machine breakdown, maintenance required..."
                autoFocus
              />
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex gap-2 justify-end">
              <button
                onClick={() => {
                  setHoldDialogOpen(false);
                  setHoldReason('');
                }}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleHold}
                disabled={!holdReason.trim() || actionPending}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-rose-600 hover:bg-rose-700 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              >
                {actionPending ? 'Processing…' : 'Put on Hold'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancellation Confirmation Dialog (Requirement 18.5, 18.6, 18.7) */}
      {cancelDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900">Cancel Work Order</h3>
              <p className="text-sm text-slate-500 mt-1">
                This will release all material reservations ({wo && wo.materials ? wo.materials.reduce((sum, m) => sum + Number(m.required_quantity) - Number(m.issued_quantity), 0).toFixed(3) : '0'} units total).
              </p>
            </div>
            <div className="px-6 py-4">
              <label className="text-sm font-medium text-gray-700 block mb-2">Cancellation Reason (optional)</label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                rows={3}
                maxLength={500}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none placeholder:text-slate-400"
                placeholder="Enter reason for cancellation (optional)..."
              />
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex gap-2 justify-end">
              <button
                onClick={() => {
                  setCancelDialogOpen(false);
                  setCancelReason('');
                }}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCancel}
                disabled={actionPending}
                className="rounded-lg px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              >
                {actionPending ? 'Cancelling…' : 'Cancel Work Order'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
