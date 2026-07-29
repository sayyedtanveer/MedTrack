import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { AssistantGuidance } from "./AssistantTypes";

export function WorkflowProgress({ guidance }: { guidance: AssistantGuidance }) {
  const stages = guidance.progress;

  if (!stages || stages.length === 0) return null;

  return (
    <div className="py-4">
      <div className="flex items-center justify-between relative">
        {/* Background Line */}
        <div className="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 w-full bg-slate-200 z-0 rounded-full" />
        
        {/* Progress Line */}
        <div 
          className="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 bg-blue-600 z-0 transition-all duration-500 rounded-full" 
          style={{ 
            width: `${(stages.findIndex(s => s.status === 'current') / (stages.length - 1)) * 100}%` 
          }} 
        />

        {stages.map((stage, index) => {
          const isCompleted = stage.status === 'completed';
          const isCurrent = stage.status === 'current';

          return (
            <div key={stage.id} className="relative z-10 flex flex-col items-center gap-2">
              <div 
                className={cn(
                  "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition-all duration-300 bg-white",
                  isCompleted ? "border-blue-600 text-blue-600" :
                  isCurrent ? "border-blue-600 ring-4 ring-blue-100 text-blue-600" :
                  "border-slate-300 text-slate-400"
                )}
              >
                {isCompleted ? <Check className="w-3.5 h-3.5" /> : (index + 1)}
              </div>
              <span 
                className={cn(
                  "text-[10px] font-medium absolute -bottom-6 w-24 text-center",
                  isCompleted ? "text-slate-700" :
                  isCurrent ? "text-blue-700 font-semibold" :
                  "text-slate-400"
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
      <div className="h-6" /> {/* Spacer for the absolute positioned labels */}
    </div>
  );
}
