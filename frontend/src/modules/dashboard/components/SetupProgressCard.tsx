import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { AlertCircle, CheckCircle2, ArrowRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
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
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Company Setup</CardTitle>
          <span className="text-sm font-semibold text-primary">{status.progress}%</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">ERP readiness</span>
            <span className="font-medium">{isComplete ? "Ready" : "In progress"}</span>
          </div>
          <Progress value={status.progress} className="h-2" />
        </div>

        <div className="flex items-start gap-2 rounded-md border border-border/60 bg-background/70 p-3 text-sm">
          {isComplete ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
          ) : (
            <AlertCircle className="mt-0.5 h-4 w-4 text-amber-600" />
          )}
          <div>
            <p className="font-medium">{isComplete ? "ERP ready" : "Continue setup"}</p>
            <p className="text-muted-foreground">
              {isComplete
                ? "The required setup checks are complete."
                : "Complete the remaining company setup steps to prepare the ERP for daily operations."}
            </p>
          </div>
        </div>

        <Button className="w-full" onClick={() => navigate("/settings/company-setup")}>
          {isComplete ? "Review readiness" : "Resume setup"}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  )
}
