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
  MapPin,
  Package,
  Ruler,
  Tag,
  Users,
  Warehouse,
  Wrench,
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
  | "units"
  | "categories"
  | "locations"
  | "operations"
  | "users"
  | "supplier"
  | "customer"
  | "material"
  | "product"
  | "bom"
  | "openingStock"
  | "readyToStart"

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
    path: "/settings/company-profile",
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
    key: "units",
    title: "Unit Master",
    description: "Add at least one unit of measure (KG, Piece, Liter...) before creating materials.",
    path: "/settings/master-data/units",
    icon: Ruler,
  },
  {
    key: "categories",
    title: "Material Categories",
    description: "Add at least one material category (Metal, Packaging...) used by Materials and Products.",
    path: "/settings/master-data/categories",
    icon: Tag,
  },
  {
    key: "locations",
    title: "Storage Locations",
    description: "Configure your warehouse storage areas before assigning locations to materials.",
    path: "/settings/master-data/locations",
    icon: MapPin,
  },
  {
    key: "operations",
    title: "Operation Master",
    description: "Create and manage reusable manufacturing operations.",
    path: "/operations",
    icon: Wrench,
  },
  {
    key: "users",
    title: "Users",
    description: "Add at least one operational user so your team can use the ERP.",
    path: "/users",
    icon: Users,
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
  {
    key: "readyToStart",
    title: "Ready to Start Business",
    description: "Review your setup summary and confirm the ERP is ready for live operations.",
    path: "/settings/company-setup",
    icon: CheckCircle2,
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

          // ── Special card: Ready to Start Business ──────────────────────────
          if (step.key === "readyToStart") {
            const REQUIRED_ITEMS = [
              { key: "company" as SetupStepKey, label: "Company Profile", path: "/settings/company-profile" },
              { key: "numberSeries" as SetupStepKey, label: "Number Series", path: "/settings/business-config/number-series" },
              { key: "units" as SetupStepKey, label: "Units of Measure", path: "/settings/master-data/units" },
              { key: "categories" as SetupStepKey, label: "Material Categories", path: "/settings/master-data/categories" },
              { key: "locations" as SetupStepKey, label: "Storage Locations", path: "/settings/master-data/locations" },
              { key: "operations" as SetupStepKey, label: "Operation Master", path: "/operations" },
              { key: "supplier" as SetupStepKey, label: "Suppliers", path: "/procurement/suppliers" },
              { key: "customer" as SetupStepKey, label: "Customers", path: "/sales/clients" },
              { key: "material" as SetupStepKey, label: "Materials", path: "/inventory/materials" },
              { key: "product" as SetupStepKey, label: "Products", path: "/products" },
            ]
            const RECOMMENDED_ITEMS = [
              { key: "bom" as SetupStepKey, label: "Bill of Materials", path: "/bom" },
              { key: "openingStock" as SetupStepKey, label: "Opening Stock", path: "/inventory/transactions" },
              { key: "users" as SetupStepKey, label: "Users", path: "/users" },
            ]
            const requiredComplete = REQUIRED_ITEMS.filter(i => Boolean(status?.[i.key])).length

            return (
              <Card key={step.key} className="lg:col-span-2 border-primary/20">
                <CardHeader className="pb-3">
                  <div className="flex items-start gap-3">
                    <div className="rounded-full bg-background p-2 shadow-sm">
                      <CheckCircle2 className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1">
                      <CardTitle className="text-base">Ready to Start Business</CardTitle>
                      <CardDescription className="mt-1">Review your setup summary before going live.</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Summary bar */}
                  <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-700">
                        {requiredComplete} of {REQUIRED_ITEMS.length} required checks complete
                      </span>
                      <Badge variant={requiredComplete === REQUIRED_ITEMS.length ? "default" : "secondary"}>
                        {requiredComplete === REQUIRED_ITEMS.length ? "Ready" : "Pending"}
                      </Badge>
                    </div>
                    <Progress value={Math.round((requiredComplete / REQUIRED_ITEMS.length) * 100)} className="h-2" />
                  </div>

                  {/* Required section */}
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Required</p>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {REQUIRED_ITEMS.map(item => {
                        const done = Boolean(status?.[item.key])
                        return (
                          <div key={item.key} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2">
                            <div className="flex items-center gap-2">
                              <span className="text-sm">{done ? "✅" : "⏳"}</span>
                              <span className="text-sm text-slate-700">{item.label}</span>
                            </div>
                            {!done && (
                              <Button variant="ghost" size="sm" className="h-7 text-xs text-blue-600 hover:text-blue-700" onClick={() => navigate(item.path)}>
                                Configure
                              </Button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Recommended section */}
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Recommended</p>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {RECOMMENDED_ITEMS.map(item => {
                        const done = Boolean(status?.[item.key])
                        return (
                          <div key={item.key} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2">
                            <div className="flex items-center gap-2">
                              <span className="text-sm">{done ? "✅" : "⏳"}</span>
                              <span className="text-sm text-slate-700">{item.label}</span>
                            </div>
                            {!done && (
                              <Button variant="ghost" size="sm" className="h-7 text-xs text-blue-600 hover:text-blue-700" onClick={() => navigate(item.path)}>
                                Configure
                              </Button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Go to Dashboard */}
                  <div className="flex justify-end pt-2">
                    <Button onClick={() => navigate("/")} className="gap-2">
                      Go to Dashboard
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          }

          // ── Normal step card ───────────────────────────────────────────────
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
