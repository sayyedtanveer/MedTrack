import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { AssistantGuidance, AssistantAction } from "./AssistantTypes";
import { NavigationRegistry } from "../../../lib/assistant/NavigationRegistry";
import { cn } from "@/lib/utils";

const ACTION_LABELS: Record<AssistantAction, string> = {
  [AssistantAction.SUBMIT_FOR_APPROVAL]: 'Submit for Approval',
  [AssistantAction.APPROVE_ORDER]: 'Approve Order',
  [AssistantAction.CONFIRM_ORDER]: 'Confirm Order',
  [AssistantAction.EDIT_ORDER]: 'Edit Order',
  [AssistantAction.CREATE_WORK_ORDER]: 'Create Work Order',
  [AssistantAction.ALLOCATE_STOCK]: 'Allocate Stock',
  [AssistantAction.VIEW_WORK_ORDERS]: 'View Work Orders',
  [AssistantAction.GO_TO_DISPATCH]: 'Go to Dispatch Queue',
  [AssistantAction.VIEW_INVOICE]: 'View Invoice',
  [AssistantAction.GO_BACK]: 'Go Back',
  [AssistantAction.SEND_PO]: 'Send to Supplier',
  [AssistantAction.ACKNOWLEDGE_PO]: 'Acknowledge PO',
  [AssistantAction.RECEIVE_PO]: 'Receive Materials',
  [AssistantAction.RECEIVE_REMAINING]: 'Receive Remaining',

  // Manufacturing Phase 3
  [AssistantAction.RELEASE_WO]: 'Release Work Order',
  [AssistantAction.ALLOCATE_MATERIALS]: 'Allocate Materials',
  [AssistantAction.REVIEW_MATERIAL_SHORTAGE]: 'Review Material Shortage',
  [AssistantAction.START_PRODUCTION]: 'Start Production',
  [AssistantAction.COMPLETE_PRODUCTION]: 'Complete Production',
  [AssistantAction.REVIEW_BLOCKERS]: 'Review Blockers',
  
  [AssistantAction.CREATE_INVOICE]: 'Create Invoice',
  [AssistantAction.RECORD_PAYMENT]: 'Record Payment',
  [AssistantAction.GO_TO_QUALITY]: 'Go to Quality Control',
  [AssistantAction.RECEIVE_FG]: 'Receive Finished Goods',
  [AssistantAction.COMPLETE_WO]: 'Complete Work Order',
  [AssistantAction.RESUME_PRODUCTION]: 'Resume Production',

  // Phase 4
  [AssistantAction.VIEW_INSPECTIONS]: 'View QC Inspections',
  [AssistantAction.RECEIVE_GOODS]: 'Receive Goods',
  [AssistantAction.DISPATCH_ORDERS]: 'Dispatch Orders'
};

export function NextActionCard({ guidance, isInbox }: { guidance: AssistantGuidance, isInbox?: boolean }) {
  const navigate = useNavigate();

  // If there's no route and priority is low, it might be just informational (like Cancelled or Completed)
  if (guidance.priority === 'low' && !guidance.route && !guidance.actionId) return null;

  const isCompleted = guidance.completedStages.length > 0;

  return (
    <div className={cn(
      "rounded-xl border p-5 shadow-sm transition-all duration-300",
      isCompleted ? "border-emerald-200 bg-gradient-to-br from-emerald-50/50 to-white" : "border-blue-100 bg-gradient-to-br from-blue-50/50 to-white"
    )}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-blue-600 mb-1">
            Recommended Next Step
          </p>
          <h4 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            {guidance.recommendedAction}
          </h4>
          <p className="text-sm text-slate-600 mt-1 max-w-xl">
            {guidance.reason}
          </p>
        </div>

        {guidance.actionId && (
          (isInbox || (guidance.route && !guidance.pulseActionId)) ? (
            <Button 
              onClick={() => {
                if (guidance.route) {
                  const url = NavigationRegistry.resolveUrl(guidance.route);
                  if (url) navigate(url);
                } else if (!isInbox) {
                  const btn = document.getElementById(guidance.pulseActionId || '');
                  if (btn) btn.click();
                }
              }}
              className="shrink-0 gap-2 shadow-sm bg-blue-600 hover:bg-blue-700"
            >
              {ACTION_LABELS[guidance.actionId] || 'Continue'}
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <div className="shrink-0 flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-700 rounded-md text-sm font-medium">
              <span className="relative flex h-2 w-2 mr-1">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
              </span>
              Click '{ACTION_LABELS[guidance.actionId] || 'Action'}' below
            </div>
          )
        )}
      </div>
    </div>
  );
}
