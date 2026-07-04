/**
 * KPI Card — dashboard metric card with trend indicator, icon, and loading/error states.
 * Requirements: 55.1–55.6
 */
import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { TrendingUp, TrendingDown, Minus, LucideIcon, AlertCircle } from "lucide-react"

export type TrendDirection = "up" | "down" | "neutral"

interface KPICardProps {
  /** Lucide icon displayed in the top-right corner of the card */
  icon?: LucideIcon
  /** Title label displayed above the value */
  title: string
  /** The primary KPI value (number or formatted string) */
  value: string | number
  /** Trend direction indicator: up, down, or neutral */
  trend?: TrendDirection
  /** Optional trend label (e.g., "+12% vs yesterday") */
  trendLabel?: string
  /** Click handler for navigation */
  onClick?: () => void
  /** Additional className for styling */
  className?: string
  /** Show skeleton loading state */
  loading?: boolean
  /** Show an error indicator instead of the value */
  error?: boolean
  /** Error message shown on hover / as aria-label */
  errorMessage?: string
}

const trendConfig: Record<TrendDirection, { icon: typeof TrendingUp; colorClass: string }> = {
  up: { icon: TrendingUp, colorClass: "text-emerald-600" },
  down: { icon: TrendingDown, colorClass: "text-red-600" },
  neutral: { icon: Minus, colorClass: "text-slate-400" },
}

export function KPICard({
  icon: Icon,
  title,
  value,
  trend,
  trendLabel,
  onClick,
  className,
  loading = false,
  error = false,
  errorMessage = "Failed to load",
}: KPICardProps) {
  const TrendIcon = trend ? trendConfig[trend].icon : null
  const trendColor = trend ? trendConfig[trend].colorClass : ""

  // ── Loading skeleton ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <Card className={cn("relative overflow-hidden", className)}>
        <CardContent className="p-5 space-y-3">
          <div className="flex items-start justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-5 w-5 rounded" />
          </div>
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-32" />
        </CardContent>
      </Card>
    )
  }

  // ── Error state ──────────────────────────────────────────────────────────────
  if (error) {
    return (
      <Card className={cn("relative overflow-hidden border-red-200 bg-red-50", className)}>
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <p className="text-sm font-medium text-slate-500">{title}</p>
            <span title={errorMessage} aria-label={errorMessage}>
              <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
            </span>
          </div>
          <p className="mt-2 text-sm text-red-500">{errorMessage}</p>
        </CardContent>
      </Card>
    )
  }

  // ── Normal state ─────────────────────────────────────────────────────────────
  return (
    <Card
      className={cn(
        "relative overflow-hidden",
        onClick && "cursor-pointer hover:border-blue-200 hover:shadow-md active:scale-[0.98] transition-shadow",
        className
      )}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault()
                onClick()
              }
            }
          : undefined
      }
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1 min-w-0">
            <p className="text-sm font-medium text-slate-500 truncate">{title}</p>
            <p className="text-2xl font-bold text-slate-900">{value}</p>
          </div>
          <div className="flex flex-col items-end gap-1 flex-shrink-0 ml-2">
            {/* Metric icon */}
            {Icon && <Icon className="h-5 w-5 text-slate-400" aria-hidden />}
            {/* Trend icon */}
            {TrendIcon && (
              <div className={cn("flex items-center gap-1", trendColor)}>
                <TrendIcon className="h-4 w-4" aria-hidden />
              </div>
            )}
          </div>
        </div>
        {trendLabel && (
          <p className={cn("mt-2 text-xs", trendColor || "text-slate-400")}>
            {trendLabel}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
