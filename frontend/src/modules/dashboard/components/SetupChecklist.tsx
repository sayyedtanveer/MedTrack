/**
 * SetupChecklist
 *
 * Surfaces the Phase 0 → Phase 1 business-setup sequence for Admin users.
 * Number Series (Phase 0) is intentionally listed first — it must be configured
 * before any master data is created so that auto-generated codes use the
 * correct prefix/padding from day one.
 *
 * Gap #11 fix: this component ensures Number Series is the very first step
 * visible to an Admin in the setup flow.
 */

import { useNavigate } from "react-router-dom"
import { Hash, Building2, Users, ShieldCheck, Truck, Package, Box, LayoutGrid, ClipboardList, ChevronRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface SetupStep {
  phase: string
  label: string
  description: string
  href: string
  icon: React.ElementType
  badge: string
}

const SETUP_STEPS: SetupStep[] = [
  // Phase 0 — Must come first (Gap #11)
  {
    phase: "Phase 0",
    label: "Number Series",
    description: "Configure prefix & padding for all 9 entity types before creating any master data.",
    href: "/settings/business-config/number-series",
    icon: Hash,
    badge: "Start here",
  },
  // Phase 1
  {
    phase: "Phase 1",
    label: "Company Profile",
    description: "Set company name, address, GST number, and logo.",
    href: "/settings/company",
    icon: Building2,
    badge: "Setup",
  },
  {
    phase: "Phase 1",
    label: "Users",
    description: "Create user accounts for each role.",
    href: "/users",
    icon: Users,
    badge: "Setup",
  },
  {
    phase: "Phase 1",
    label: "Roles & Permissions",
    description: "Assign RBAC permissions before users access the system.",
    href: "/roles",
    icon: ShieldCheck,
    badge: "Setup",
  },
  {
    phase: "Phase 1",
    label: "Suppliers",
    description: "Create supplier records for procurement.",
    href: "/procurement/suppliers",
    icon: Truck,
    badge: "Master data",
  },
  {
    phase: "Phase 1",
    label: "Materials",
    description: "Create raw material and finished goods with opening stock.",
    href: "/inventory/materials",
    icon: Package,
    badge: "Master data",
  },
  {
    phase: "Phase 1",
    label: "Products & BOM",
    description: "Create product templates, variants, and bills of materials.",
    href: "/products",
    icon: Box,
    badge: "Master data",
  },
  {
    phase: "Phase 1",
    label: "Customers",
    description: "Create customer records for sales orders.",
    href: "/sales/clients",
    icon: LayoutGrid,
    badge: "Master data",
  },
  // Phase 2
  {
    phase: "Phase 2",
    label: "Sales Orders",
    description: "Create, approve, and confirm sales orders to begin the manufacturing cycle.",
    href: "/sales/orders",
    icon: ClipboardList,
    badge: "Operations",
  },
]

const BADGE_VARIANTS: Record<string, "default" | "secondary" | "outline"> = {
  "Start here": "default",
  Setup: "secondary",
  "Master data": "outline",
  Operations: "outline",
}

export function SetupChecklist() {
  const navigate = useNavigate()

  return (
    <Card className="col-span-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Setup Guide</CardTitle>
          <span className="text-xs text-muted-foreground">
            Complete steps in order — Number Series first
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {SETUP_STEPS.map((step, idx) => {
            const Icon = step.icon
            const isFirst = idx === 0

            return (
              <div
                key={step.href}
                className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors hover:bg-muted/50 cursor-pointer ${
                  isFirst ? "border-primary/40 bg-primary/5" : "border-border"
                }`}
                onClick={() => navigate(step.href)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && navigate(step.href)}
                aria-label={`Navigate to ${step.label}`}
              >
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                    isFirst
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-muted-foreground font-medium">
                      {step.phase}
                    </span>
                    <span className="text-sm font-medium leading-none">{step.label}</span>
                    <Badge
                      variant={BADGE_VARIANTS[step.badge] ?? "secondary"}
                      className="text-xs px-1.5 py-0"
                    >
                      {step.badge}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 truncate">
                    {step.description}
                  </p>
                </div>

                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </div>
            )
          })}
        </div>

        <p className="mt-3 text-xs text-muted-foreground text-center">
          Number Series (Phase 0) must be configured before any master data is created.
          See{" "}
          <Button
            variant="link"
            className="h-auto p-0 text-xs"
            onClick={() => navigate("/settings/business-config/number-series")}
          >
            Settings → Business Configuration → Number Series
          </Button>
          .
        </p>
      </CardContent>
    </Card>
  )
}
