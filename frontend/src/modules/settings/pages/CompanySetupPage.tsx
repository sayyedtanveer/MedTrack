import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  ArrowRight,
  Building2,
  Box,
  CheckCircle2,
  Circle,
  FileStack,
  Hash,
  Package,
  Users,
  Warehouse,
} from "lucide-react"
import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { setupStatusService, type CompanySetupStatusResponse } from "@/services/setup-status.service"

type SetupStepKey =
  | "company"
  | "numberSeries"
  | "supplier"
  | "customer"
  | "material"
  | "product"
  | "bom"
  | "openingStock"

interface SetupStepDefinition {
  key: SetupStepKey
  title: string
  description: string
  path: string
  icon: typeof Building2
}

const setupStepDefinitions: SetupStepDefinition[] = [
  {
    key: "company",
    title: "Company Profile",
    description: "Confirm your company identity and basic tenant details.",
    path: "/settings/business-config",
    icon: Building2,
  },
  {
    key: "numberSeries",
    title: "Number Series",
    description: "Set prefix and sequence formats for documents and items.",
    path: "/settings/business-config/number-series",
    icon: Hash,
  },
  {
    key: "supplier",
    title: "Suppliers",
    description: "Add at least one active supplier to start procurement.",
    path: "/procurement/suppliers",
    icon: Users,
  },
  {
    key: "customer",
    title: "Customers",
    description: "Create your first customer or client record for sales.",
    path: "/sales/clients",
    icon: Users,
  },
  {
    key: "material",
    title: "Materials",
    description: "Register BOM ingredients and stock components.",
    path: "/inventory/materials",
    icon: Box,
  },
  {
    key: "product",
    title: "Products",
    description: "Create finished products or templates for manufacturing.",
    path: "/products",
    icon: Package,
  },
  {
    key: "bom",
    title: "Bill of Materials",
    description: "Define BOM structures for your products.",
    path: "/bom",
    icon: FileStack,
  },
  {
    key: "openingStock",
    title: "Opening Stock",
    description: "Record the initial inventory balance for the first period.",
    path: "/inventory/transactions",
    icon: Warehouse,
  },
]

export default function CompanySetupPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<CompanySetupStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true

    setupStatusService
      .getStatus()
      .then((response) => {
        if (active) setStatus(response)
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  const nextStep = useMemo(() => {
    if (!status) return null
    return setupStepDefinitions.find((step) => !status[step.key]) ?? null
  }, [status])

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="First Time Company Setup"
        description="Complete the essential setup steps so your ERP is ready for daily operations."
      />

      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <CardTitle>Setup progress</CardTitle>
              <CardDescription>
                Follow the guided checklist below to move from onboarding to production readiness.
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={status?.progress === 100 ? "default" : "secondary"}>
                {isLoading ? "Checking..." : `${status?.progress ?? 0}% complete`}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress value={status?.progress ?? 0} className="h-2" />
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>Recommended next step:</span>
            <span className="font-medium text-foreground">
              {nextStep?.title ?? "Everything looks ready"}
            </span>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {setupStepDefinitions.map((step) => {
          const Icon = step.icon
          const isComplete = Boolean(status?.[step.key])

          return (
            <Card key={step.key} className={isComplete ? "border-emerald-200 bg-emerald-50/70" : ""}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="rounded-full bg-background p-2 shadow-sm">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{step.title}</CardTitle>
                      <CardDescription className="mt-1">{step.description}</CardDescription>
                    </div>
                  </div>
                  {isComplete ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <Circle className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
              </CardHeader>
              <CardContent className="flex items-center justify-between gap-3">
                <Badge variant={isComplete ? "default" : "secondary"}>
                  {isComplete ? "Complete" : "Pending"}
                </Badge>
                <Button variant="outline" size="sm" onClick={() => navigate(step.path)}>
                  {isComplete ? "Review" : "Open"}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
