import { AlertTriangle } from "lucide-react";
import { AssistantGuidance } from "./AssistantTypes";

export function WorkflowWarnings({ guidance }: { guidance: AssistantGuidance }) {
  if (!guidance.warnings || guidance.warnings.length === 0) return null;

  return (
    <div className="mt-4 flex flex-col gap-2">
      {guidance.warnings.map((warning, idx) => (
        <div key={idx} className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 shadow-sm">
          <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-amber-800">Cannot Proceed</h4>
            <p className="text-sm mt-1">{warning}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
