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
import { Hash, Building2, Users, ShieldCheck, Truck, Package, Box, LayoutGrid, ClipboardList, ChevronRight, Database } from "lucide-react"
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
    href: "/settings/company-profile",
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
    label: "Master Data",
    description: "Configure unit of measure, material categories, and storage locations.",
    href: "/settings/master-data",
    icon: Database,
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
    <Card className="col-span-full border-white/60 bg-gradient-to-br from-indigo-50/90 via-white/80 to-blue-50/90 text-slate-900 backdrop-blur-2xl shadow-xl relative overflow-hidden">
      {/* Decorative gradient blob */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-primary/10 rounded-full blur-[80px] pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-48 h-48 bg-blue-400/10 rounded-full blur-[60px] pointer-events-none" />
      
      <CardHeader className="pb-3 border-b border-slate-200/50 bg-gradient-to-r from-blue-50/50 to-transparent relative z-10">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
            Setup Guide
          </CardTitle>
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-white/80 text-slate-600 border border-slate-200/80 shadow-sm backdrop-blur-sm">
            Complete steps in order
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {SETUP_STEPS.map((step, idx) => {
            const Icon = step.icon
            const isFirst = idx === 0

            return (
              <div
                key={step.href}
                className={`group flex items-start gap-4 rounded-xl border px-4 py-3 transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 cursor-pointer relative overflow-hidden h-full ${
                  isFirst 
                    ? "border-primary/30 bg-gradient-to-br from-primary/[0.05] to-primary/[0.02] hover:from-primary/[0.1] hover:to-primary/[0.05] shadow-sm shadow-primary/10 ring-1 ring-primary/20 ring-inset" 
                    : "border-slate-200/80 bg-white/60 hover:bg-gradient-to-br hover:from-white hover:to-slate-50"
                }`}
                onClick={() => navigate(step.href)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && navigate(step.href)}
                aria-label={`Navigate to ${step.label}`}
              >
                {/* Subtle highlight line for hover */}
                <div className={`absolute left-0 top-0 bottom-0 w-1 transition-transform duration-300 origin-left scale-y-0 group-hover:scale-y-100 ${
                  isFirst ? "bg-primary" : "bg-slate-300"
                }`} />

                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl shadow-sm transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3 ${
                    isFirst
                      ? "bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-primary/30"
                      : "bg-gradient-to-br from-slate-100 to-white text-slate-500 border border-slate-200/60"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-bold tracking-wider uppercase ${isFirst ? 'text-primary' : 'text-slate-400'}`}>
                      {step.phase}
                    </span>
                    <span className="text-sm font-semibold text-slate-800 leading-none">{step.label}</span>
                    <Badge
                      variant={BADGE_VARIANTS[step.badge] ?? "secondary"}
                      className={`text-[10px] px-2 py-0.5 font-semibold ${isFirst ? 'bg-primary text-primary-foreground' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                    >
                      {step.badge}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 mt-1.5 group-hover:text-slate-700 transition-colors">
                    {step.description}
                  </p>
                </div>

                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-all duration-300 ${
                  isFirst ? "bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white" : "bg-slate-100/50 text-slate-400 group-hover:bg-slate-200 group-hover:text-slate-600"
                }`}>
                  <ChevronRight className="h-4 w-4 shrink-0 transition-transform duration-300 group-hover:translate-x-0.5" />
                </div>
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
