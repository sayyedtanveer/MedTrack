import { cn } from "@/lib/utils"
import { Check } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export type StageStatus = "completed" | "current" | "pending" | "inactive"

export interface TimelineStage {
  key: string
  label: string
  /** ISO timestamp of when this stage was completed */
  completedAt?: string | null
  /** Optional sub-status label shown beneath this stage (e.g., aggregated WO status) */
  subStatus?: string | null
}

interface WorkflowTimelineProps {
  /** Ordered list of workflow stages */
  stages: TimelineStage[]
  /** The key of the currently active stage */
  currentStage: string
  /** If true, all stages are marked inactive (e.g., for CANCELLED status) */
  inactive?: boolean
  className?: string
}

function getStageStatus(
  stageIndex: number,
  currentIndex: number,
  inactive: boolean
): StageStatus {
  if (inactive) return "inactive"
  if (stageIndex < currentIndex) return "completed"
  if (stageIndex === currentIndex) return "current"
  return "pending"
}

function formatRelativeTime(isoString: string): string {
  try {
    return formatDistanceToNow(new Date(isoString), { addSuffix: true })
  } catch {
    return isoString
  }
}

function formatAbsoluteTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString()
  } catch {
    return isoString
  }
}

export function WorkflowTimeline({
  stages,
  currentStage,
  inactive = false,
  className,
}: WorkflowTimelineProps) {
  const currentIndex = stages.findIndex((s) => s.key === currentStage)

  return (
    <TooltipProvider>
      <div className={cn("w-full", className)}>
        <div className="flex items-center justify-between">
          {stages.map((stage, index) => {
            const status = getStageStatus(
              index,
              currentIndex >= 0 ? currentIndex : stages.length,
              inactive
            )

            return (
              <div key={stage.key} className="flex flex-1 items-center">
                {/* Stage indicator */}
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors",
                      status === "completed" &&
                        "border-emerald-500 bg-emerald-500 text-white",
                      status === "current" &&
                        "border-blue-500 bg-blue-500 text-white",
                      status === "pending" &&
                        "border-slate-300 bg-white text-slate-400",
                      status === "inactive" &&
                        "border-slate-200 bg-slate-100 text-slate-300"
                    )}
                    aria-label={`${stage.label}: ${status}`}
                  >
                    {status === "completed" ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </div>

                  <span
                    className={cn(
                      "mt-2 max-w-[80px] text-center text-[10px] leading-tight",
                      status === "completed" && "text-emerald-700 font-medium",
                      status === "current" && "text-blue-700 font-semibold",
                      status === "pending" && "text-slate-400",
                      status === "inactive" && "text-slate-300"
                    )}
                  >
                    {stage.label}
                  </span>

                  {/* Completion timestamp with tooltip for absolute time */}
                  {status === "completed" && stage.completedAt && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="mt-0.5 max-w-[80px] cursor-default text-center text-[9px] text-emerald-600 leading-tight">
                          {formatRelativeTime(stage.completedAt)}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{formatAbsoluteTime(stage.completedAt)}</p>
                      </TooltipContent>
                    </Tooltip>
                  )}

                  {/* Sub-status beneath current stage */}
                  {status === "current" && stage.subStatus && (
                    <span className="mt-0.5 max-w-[80px] text-center text-[9px] text-blue-500 leading-tight italic">
                      {stage.subStatus}
                    </span>
                  )}
                </div>

                {/* Connector line (skip after last stage) */}
                {index < stages.length - 1 && (
                  <div
                    className={cn(
                      "mx-1 h-0.5 flex-1 self-start mt-4",
                      status === "completed" && "bg-emerald-500",
                      status === "current" && "bg-blue-300",
                      status === "pending" && "bg-slate-200",
                      status === "inactive" && "bg-slate-100"
                    )}
                  />
                )}
              </div>
            )
          })}
        </div>
      </div>
    </TooltipProvider>
  )
}
