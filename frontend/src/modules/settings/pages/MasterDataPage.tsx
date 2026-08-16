/**
 * Master Data Hub Page
 * Dashboard that links to all foundational master data sections.
 * Uses isolated query keys (prefixed with "hub:") to avoid polluting
 * the shared React Query cache used by the individual management pages.
 */

import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Ruler, Tag, MapPin, Wrench, Factory, ChevronRight, Loader2 } from "lucide-react"
import { materialService } from "@/services/material.service"
import { operationService } from "@/services/operation.service"
import { workstationsService } from "@/services/workstations.service"
import { cn } from "@/lib/utils"

// ── Hub card config ────────────────────────────────────────────────────────────

interface HubSection {
  title: string
  description: string
  href: string
  icon: React.ElementType
  color: string
  bgColor: string
  /** Isolated query key — MUST NOT match any key used by the management pages */
  queryKey: string[]
  queryFn: () => Promise<number>
}

const HUB_SECTIONS: HubSection[] = [
  {
    title: "Units of Measure",
    description: "Define measurement units used across products, materials, and BOMs (e.g. kg, pcs, ltr).",
    href: "/settings/master-data/units",
    icon: Ruler,
    color: "text-blue-600 dark:text-blue-400",
    bgColor: "bg-blue-50 dark:bg-blue-950/40",
    queryKey: ["hub:units-count"],
    queryFn: async () => {
      const res = await materialService.getUnits()
      return Array.isArray(res) ? res.length : (res as any)?.items?.length ?? 0
    },
  },
  {
    title: "Material Categories",
    description: "Organise materials into categories for filtering, item code generation, and reporting.",
    href: "/settings/master-data/categories",
    icon: Tag,
    color: "text-emerald-600 dark:text-emerald-400",
    bgColor: "bg-emerald-50 dark:bg-emerald-950/40",
    queryKey: ["hub:categories-count"],
    queryFn: async () => {
      const res = await materialService.getCategories()
      return Array.isArray(res) ? res.length : (res as any)?.items?.length ?? 0
    },
  },
  {
    title: "Storage Locations",
    description: "Configure warehouses, bins, racks, and storage areas for inventory management.",
    href: "/settings/master-data/locations",
    icon: MapPin,
    color: "text-violet-600 dark:text-violet-400",
    bgColor: "bg-violet-50 dark:bg-violet-950/40",
    queryKey: ["hub:locations-count"],
    queryFn: async () => {
      const res = await materialService.getLocations()
      return Array.isArray(res) ? res.length : (res as any)?.items?.length ?? 0
    },
  },
  {
    title: "Operation Master",
    description: "Define manufacturing operations such as Cutting, Assembly, and Inspection used in BOMs.",
    href: "/manufacturing/operations-master",
    icon: Wrench,
    color: "text-amber-600 dark:text-amber-400",
    bgColor: "bg-amber-50 dark:bg-amber-950/40",
    queryKey: ["hub:operations-count"],
    queryFn: async () => {
      // Use listOperationsForBOM which requires no extra params
      const res = await operationService.listOperationsForBOM()
      return res?.items?.length ?? 0
    },
  },
  {
    title: "Workstations",
    description: "Set up production workstations, machines, and work centres used in manufacturing routing.",
    href: "/manufacturing/workstations-master",
    icon: Factory,
    color: "text-rose-600 dark:text-rose-400",
    bgColor: "bg-rose-50 dark:bg-rose-950/40",
    queryKey: ["hub:workstations-count"],
    queryFn: async () => {
      const res = await workstationsService.listWorkstations()
      return Array.isArray(res) ? res.length : 0
    },
  },
]

// ── Individual card ────────────────────────────────────────────────────────────

function HubCard({ section }: { section: HubSection }) {
  const navigate = useNavigate()

  const { data: count, isLoading } = useQuery({
    queryKey: section.queryKey,
    queryFn: section.queryFn,
    staleTime: 30_000,
    // Don't crash the whole hub if one count fails
    retry: 1,
  })

  return (
    <Card
      className={cn(
        "group cursor-pointer border transition-all duration-200",
        "hover:shadow-md hover:-translate-y-0.5 hover:border-primary/40"
      )}
      onClick={() => navigate(section.href)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") navigate(section.href) }}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1 min-w-0">
            {/* Icon */}
            <div className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
              section.bgColor
            )}>
              <section.icon className={cn("h-5 w-5", section.color)} />
            </div>

            {/* Text */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                  {section.title}
                </h3>
                {isLoading ? (
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                ) : count !== undefined ? (
                  <Badge variant="secondary" className="text-xs tabular-nums">
                    {count}
                  </Badge>
                ) : null}
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                {section.description}
              </p>
            </div>
          </div>

          {/* Arrow */}
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/30 group-hover:text-primary group-hover:translate-x-0.5 transition-all duration-200" />
        </div>
      </CardContent>
    </Card>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MasterDataPage() {
  return (
    <div className="w-full space-y-6 pb-8">
      <PageHeader
        title="Master Data"
        description="Manage foundational reference data that drives your entire ERP — units, categories, locations, operations, and workstations."
      />

      <div className="grid gap-3 sm:grid-cols-1 lg:grid-cols-2">
        {HUB_SECTIONS.map((section) => (
          <HubCard key={section.title} section={section} />
        ))}
      </div>
    </div>
  )
}
