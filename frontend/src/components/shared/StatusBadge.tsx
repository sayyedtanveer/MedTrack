import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export type StatusType = 
  | "active" 
  | "inactive" 
  | "low-stock" 
  | "out-of-stock" 
  | "expired" 
  | "pending" 
  | "completed"
  | string

/**
 * A mapping of status values to Tailwind CSS color classes.
 * Each value should include border, background, and text color classes.
 * Example: { "DRAFT": "border-slate-200 bg-slate-50 text-slate-700" }
 */
export type StatusColorMap = Record<string, string>

interface StatusBadgeProps {
  status: string
  label?: string
  className?: string
  /**
   * Optional color map to override the default color mappings.
   * Keys are status values, values are Tailwind CSS class strings.
   * When provided, this takes priority over the built-in status styles.
   */
  colorMap?: StatusColorMap
}

const DEFAULT_COLOR_MAP: StatusColorMap = {
  active: "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
  inactive: "border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200",
  pending: "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100",
  "low-stock": "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100",
  "out-of-stock": "border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
  expired: "border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
}

const DEFAULT_FALLBACK = "border-blue-200 bg-blue-50 text-blue-700"

export function StatusBadge({ status, label, className, colorMap }: StatusBadgeProps) {
  const getStatusStyles = (): string => {
    // If a custom colorMap is provided, use it first
    if (colorMap) {
      const customStyle = colorMap[status] || colorMap[status.toLowerCase()]
      if (customStyle) return customStyle
    }

    // Fall back to built-in defaults
    const normalizedStatus = status.toLowerCase()
    return DEFAULT_COLOR_MAP[normalizedStatus] || DEFAULT_FALLBACK
  }

  const defaultLabel = status
    .replace(/_/g, " ")
    .split("-")
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ")

  return (
    <Badge 
      variant="outline" 
      className={cn("font-medium transition-colors", getStatusStyles(), className)}
    >
      {label || defaultLabel}
    </Badge>
  )
}
