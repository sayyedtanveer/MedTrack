import { useNavigate } from "react-router-dom"
import { Hash, GitBranch, Workflow, ShieldCheck, Flag, FileText } from "lucide-react"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BusinessAssistantPanel } from "@/components/shared/BusinessAssistantPanel"
import type { BusinessAssistantConfig } from "@/components/shared/BusinessAssistantPanel"

interface ConfigModuleCard {
  title: string
  description: string
  icon: React.ElementType
  href: string
  status: "active" | "coming_soon"
}

const CONFIG_MODULES: ConfigModuleCard[] = [
  {
    title: "Number Series",
    description:
      "Configure how item codes and document numbers are generated for each entity type.",
    icon: Hash,
    href: "/settings/business-config/number-series",
    status: "active",
  },
  {
    title: "Business Rules",
    description:
      "Define conditional logic and validation rules that enforce business policies.",
    icon: GitBranch,
    href: "#",
    status: "coming_soon",
  },
  {
    title: "Workflow Engine",
    description:
      "Design multi-step approval and processing workflows for documents and transactions.",
    icon: Workflow,
    href: "#",
    status: "coming_soon",
  },
  {
    title: "Approval Matrix",
    description:
      "Set up approval hierarchies and thresholds for purchase orders, invoices, and more.",
    icon: ShieldCheck,
    href: "#",
    status: "coming_soon",
  },
  {
    title: "Feature Flags",
    description:
      "Toggle experimental features on or off for your tenant without redeploying.",
    icon: Flag,
    href: "#",
    status: "coming_soon",
  },
  {
    title: "Document Templates",
    description:
      "Customize PDF and email templates for invoices, purchase orders, and reports.",
    icon: FileText,
    href: "#",
    status: "coming_soon",
  },
]

const businessConfigAssistant: BusinessAssistantConfig = {
  pageTitle: "Business Configuration",
  about:
    "Business Configuration is the central control panel for system-wide ERP settings that affect how your entire organization operates in MedTrack. " +
    "Currently, Number Series is the active module — it controls how every document code is generated. " +
    "Additional modules (Business Rules, Workflow Engine, Approval Matrix, Feature Flags, Document Templates) are planned for future releases.",
  businessPurpose:
    "Before your team can create materials, products, purchase orders or any other records, the ERP must know how to number them. " +
    "Business Configuration is where administrators establish these foundations so the rest of the system can operate correctly.",
  erpFlow: [
    { label: "Company Setup" },
    { label: "Business Configuration", active: true, description: "You are here" },
    { label: "Number Series" },
    { label: "Material Master" },
    { label: "Product Master" },
    { label: "Purchase Orders / Sales Orders" },
    { label: "Manufacturing" },
    { label: "Finance" },
  ],
  canDo: [
    "Access Number Series configuration (active)",
    "View upcoming configuration modules (coming soon)",
  ],
  screenWalkthrough: [
    {
      section: "Number Series card",
      purpose: "Opens the Number Series configuration — the only active module currently.",
      impact: "Must be configured before creating any records in the system.",
    },
    {
      section: "Coming Soon cards",
      purpose: "Business Rules, Workflow Engine, Approval Matrix, Feature Flags, Document Templates are not yet implemented.",
      impact: "Not currently available — shown for roadmap visibility only.",
    },
  ],
  fieldGuide: [],
  buttonGuide: [
    {
      button: "Number Series card (click)",
      what: "Navigates to the Number Series configuration page.",
      continues: "Configure how codes are generated for materials, products, orders and more.",
      reversible: true,
    },
  ],
  beforeYouStart: [
    "Company profile created (Settings → Company Setup)",
    "You have ADMIN role",
  ],
  afterSave: [
    { label: "Configure Number Series" },
    { label: "Create Materials & Products" },
    { label: "Start purchasing and manufacturing" },
  ],
  bestPractices: [
    "Complete Number Series configuration before any data entry",
    "Review all number format previews before going live",
  ],
  commonMistakes: [
    "Skipping Number Series configuration — causes failures when creating the first material or order",
    "Assuming Coming Soon modules are available — they are not yet implemented",
  ],
  relatedScreens: [
    { label: "Number Series", href: "/settings/business-config/number-series" },
    { label: "Company Setup", href: "/settings/company-setup" },
  ],
  faqs: [
    {
      question: "Why are most modules showing 'Coming Soon'?",
      answer: "Business Rules, Workflow Engine, Approval Matrix, Feature Flags and Document Templates are planned features not yet implemented in MedTrack.",
    },
    {
      question: "What should I configure first?",
      answer: "Number Series must be configured before creating any materials, products or business documents.",
    },
  ],
  tips: [
    "Start with Number Series — it is the only module you need before going live",
    "Check back later for Business Rules and Workflow Engine as they are added",
  ],
  warnings: [
    "Do not skip Number Series configuration — the ERP cannot generate document codes without it",
  ],
  successResult: [
    "Number Series configured for all entity types",
    "Team can now create materials, products and orders",
    "Codes auto-generate consistently across all document types",
  ],
}

export default function BusinessConfigPage() {
  const navigate = useNavigate()

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Business Configuration"
        description="Manage system-wide configuration modules for your organization."
        action={
          <BusinessAssistantPanel
            config={businessConfigAssistant}
            triggerLabel="Business Assistant"
          />
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CONFIG_MODULES.map((mod) => {
          const Icon = mod.icon
          const isActive = mod.status === "active"

          return (
            <Card
              key={mod.title}
              className={`relative transition-shadow ${
                isActive
                  ? "cursor-pointer hover:shadow-md"
                  : "opacity-60 cursor-default"
              }`}
              onClick={() => isActive && navigate(mod.href)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className="h-5 w-5 text-primary" />
                    <CardTitle className="text-base">{mod.title}</CardTitle>
                  </div>
                  <Badge variant={isActive ? "default" : "secondary"}>
                    {isActive ? "Active" : "Coming Soon"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{mod.description}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
