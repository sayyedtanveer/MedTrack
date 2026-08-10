import { Badge } from "@/components/ui/badge"
import { TenantStatus } from "../types/platform"
import { cn } from "@/lib/utils"
import { CheckCircle2, Clock, XCircle, Ban, Archive } from "lucide-react"

interface TenantStatusBadgeProps {
  status: TenantStatus | string
  className?: string
  showIcon?: boolean
}

export function TenantStatusBadge({ status, className, showIcon = true }: TenantStatusBadgeProps) {
  const normalizedStatus = status.toLowerCase() as TenantStatus

  const getStatusConfig = () => {
    switch (normalizedStatus) {
      case "active":
        return {
          label: "Active",
          className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/25 border-emerald-500/20",
          icon: CheckCircle2,
        }
      case "pending":
        return {
          label: "Pending",
          className: "bg-amber-500/15 text-amber-600 dark:text-amber-400 hover:bg-amber-500/25 border-amber-500/20",
          icon: Clock,
        }
      case "suspended":
        return {
          label: "Suspended",
          className: "bg-rose-500/15 text-rose-600 dark:text-rose-400 hover:bg-rose-500/25 border-rose-500/20",
          icon: Ban,
        }
      case "rejected":
        return {
          label: "Rejected",
          className: "bg-slate-500/15 text-slate-600 dark:text-slate-400 hover:bg-slate-500/25 border-slate-500/20",
          icon: XCircle,
        }
      case "archived":
        return {
          label: "Archived",
          className: "bg-slate-800/15 text-slate-400 dark:text-slate-500 hover:bg-slate-800/25 border-slate-700/20",
          icon: Archive,
        }
      default:
        return {
          label: status,
          className: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300",
          icon: null,
        }
    }
  }

  const config = getStatusConfig()
  const Icon = config.icon

  return (
    <Badge
      variant="outline"
      className={cn(
        "font-medium transition-colors gap-1.5 whitespace-nowrap",
        config.className,
        className
      )}
    >
      {showIcon && Icon && <Icon className="h-3.5 w-3.5" />}
      {config.label}
    </Badge>
  )
}
