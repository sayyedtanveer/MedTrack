import { ReactNode } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ArrowLeft } from "lucide-react"

interface PageHeaderProps {
  title: string
  description?: string
  action?: ReactNode
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const fromSetup = location.state?.fromSetup

  return (
    <div className="mb-6 flex flex-col gap-4 md:mb-8 md:flex-row md:items-end md:justify-between">
      <div className="space-y-2">
        {fromSetup ? (
          <button 
            onClick={() => navigate("/settings/company-setup")}
            className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-blue-600 hover:text-blue-800 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Setup
          </button>
        ) : (
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Workspace</p>
        )}
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{title}</h1>
        {description && <p className="max-w-2xl text-sm text-slate-500 sm:text-base">{description}</p>}
      </div>
      {action && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {action}
        </div>
      )}
    </div>
  )
}
