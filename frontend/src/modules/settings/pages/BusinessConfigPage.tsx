import { useNavigate } from "react-router-dom"
import { Hash, GitBranch, Workflow, ShieldCheck, Flag, FileText } from "lucide-react"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

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

export default function BusinessConfigPage() {
  const navigate = useNavigate()

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Business Configuration"
        description="Manage system-wide configuration modules for your organization."
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
