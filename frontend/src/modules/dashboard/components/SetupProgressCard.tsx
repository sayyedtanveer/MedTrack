import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { AlertCircle, CheckCircle2, ArrowRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

import { setupStatusService, type CompanySetupStatusResponse } from "@/services/setup-status.service"

export function SetupProgressCard() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<CompanySetupStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    setupStatusService
      .getStatus()
      .then((data) => {
        if (active) setStatus(data)
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  if (isLoading) {
    return null
  }

  if (!status) {
    return null
  }

  const isComplete = status.progress >= 100

  return (
    <Card className="border-primary/20 bg-gradient-to-b from-primary/10 to-transparent backdrop-blur-xl shadow-lg relative overflow-hidden group">
      {/* Background flare */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2 transition-transform duration-700 group-hover:scale-150" />
      
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
            Company Setup
          </CardTitle>
          <span className="text-sm font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">{status.progress}%</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-500 font-medium">ERP readiness</span>
            <span className="font-semibold text-slate-700">{isComplete ? "Ready" : "In progress"}</span>
          </div>
          <div className="h-2.5 w-full bg-slate-100/50 rounded-full overflow-hidden shadow-inner backdrop-blur-sm">
            <div 
              className="h-full bg-gradient-to-r from-primary/80 to-primary rounded-full transition-all duration-1000 ease-out relative overflow-hidden"
              style={{ width: `${status.progress}%` }}
            >
              <div className="absolute top-0 bottom-0 left-0 w-full bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.4),transparent)] -translate-x-full animate-[shimmer_2s_infinite]" />
            </div>
          </div>
        </div>

        <div className="flex items-start gap-3 rounded-xl border border-slate-200/50 bg-white/60 p-4 shadow-sm backdrop-blur-md transition-all duration-300 hover:shadow-md hover:bg-white/80">
          {isComplete ? (
            <div className="rounded-full bg-emerald-100/50 p-1">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            </div>
          ) : (
            <div className="rounded-full bg-amber-100/50 p-1">
              <AlertCircle className="h-5 w-5 text-amber-600" />
            </div>
          )}
          <div>
            <p className="font-semibold text-slate-800">{isComplete ? "ERP ready" : "Continue setup"}</p>
            <p className="text-xs text-slate-500 mt-1">
              {isComplete
                ? "The required setup checks are complete."
                : "Complete the remaining company setup steps to prepare the ERP for daily operations."}
            </p>
          </div>
        </div>

        <Button 
          className="w-full shadow-md transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 group/btn" 
          onClick={() => navigate("/settings/company-setup")}
        >
          {isComplete ? "Review readiness" : "Resume setup"}
          <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover/btn:translate-x-1" />
        </Button>
      </CardContent>
    </Card>
  )
}
