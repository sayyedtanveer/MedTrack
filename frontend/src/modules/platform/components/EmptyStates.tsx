import { LucideIcon, PartyPopper, CheckCircle } from "lucide-react"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: React.ReactNode
}

export function PlatformEmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center rounded-xl border border-dashed bg-slate-50/50 px-6 py-12 text-center dark:bg-slate-900/20">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800">
        <Icon className="h-10 w-10 text-slate-500 dark:text-slate-400" />
      </div>
      <h3 className="mt-6 text-xl font-semibold text-slate-900 dark:text-white">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
        {description}
      </p>
      {action && <div className="mt-8">{action}</div>}
    </div>
  )
}

export function AllClearEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-emerald-200 bg-emerald-50/30 px-6 py-12 text-center dark:border-emerald-900/30 dark:bg-emerald-900/10">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/40">
        <PartyPopper className="h-10 w-10 text-emerald-600 dark:text-emerald-400" />
      </div>
      <h3 className="mt-6 text-xl font-semibold text-slate-900 dark:text-white">
        All workspaces have been reviewed
      </h3>
      <p className="mt-2 flex items-center justify-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
        <CheckCircle className="h-4 w-4" />
        No pending approvals or suspended tenants requiring immediate attention.
      </p>
    </div>
  )
}
