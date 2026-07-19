import { HelpCircle } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface FieldHelpIconProps {
  purpose: string
  meaning: string
  example?: string
  recommendation?: string
}

/**
 * A small (?) icon that reveals field-level help on hover.
 * Drop it next to any <Label> — no Business Assistant panel needed.
 *
 * Usage:
 *   <Label>Prefix <FieldHelpIcon purpose="..." meaning="..." example="RM" recommendation="..." /></Label>
 */
export function FieldHelpIcon({ purpose, meaning, example, recommendation }: FieldHelpIconProps) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex cursor-help items-center">
            <HelpCircle className="ml-1 h-3.5 w-3.5 text-muted-foreground hover:text-primary transition-colors" />
          </span>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          className="z-50 max-w-xs rounded-xl border border-slate-200 bg-white p-3 shadow-lg"
        >
          <div className="space-y-1.5 text-xs">
            <p className="font-semibold text-slate-900">{purpose}</p>
            <p className="text-slate-600">{meaning}</p>
            {example && (
              <p className="text-slate-500">
                <span className="font-medium">Example: </span>
                <code className="rounded bg-slate-100 px-1 py-0.5 font-mono">{example}</code>
              </p>
            )}
            {recommendation && (
              <p className="text-blue-600">
                <span className="font-medium">💡 </span>
                {recommendation}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
