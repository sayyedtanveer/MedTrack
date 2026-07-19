import { Link, useLocation } from "react-router-dom"
import { ChevronRight, Home } from "lucide-react"

// Human-readable labels for known path segments
const SEGMENT_LABELS: Record<string, string> = {
  "bom": "Bill of Materials",
  "list": "All BOMs",
  "products": "Products",
  "inventory": "Inventory",
  "materials": "Materials",
  "movements": "Movements",
  "transactions": "Transactions",
  "users": "Users",
  "settings": "Settings",
  "business-config": "Business Config",
  "number-series": "Number Series",
  "company-setup": "Company Setup",
  "security": "Security",
  "manufacturing": "Manufacturing",
  "workstations": "Workstations",
  "operations": "Operations",
  "reports": "Reports",
  "new": "New",
  "edit": "Edit",
}

// UUID pattern
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function getSegmentLabel(segment: string): string {
  if (UUID_REGEX.test(segment)) return "Detail"
  if (SEGMENT_LABELS[segment]) return SEGMENT_LABELS[segment]
  // Fallback: capitalize and replace hyphens/underscores
  return segment.charAt(0).toUpperCase() + segment.slice(1).replace(/[-_]/g, " ")
}

export function Breadcrumb() {
  const location = useLocation()
  const paths = location.pathname.split("/").filter(Boolean)

  return (
    <nav
      aria-label="Breadcrumb"
      className="mb-1 flex flex-wrap items-center gap-1 rounded-full border border-slate-200/80 bg-white px-3 py-2 text-sm text-slate-500 shadow-sm"
    >
      <Link
        to="/"
        className="flex items-center gap-1 rounded-full px-2 py-1 font-medium hover:bg-slate-50 hover:text-slate-900 transition-colors"
      >
        <Home className="h-3.5 w-3.5" />
        <span>Dashboard</span>
      </Link>

      {paths.map((segment, index) => {
        const isLast = index === paths.length - 1
        const to = `/${paths.slice(0, index + 1).join("/")}`
        const label = getSegmentLabel(segment)

        return (
          <div key={`${segment}-${index}`} className="flex items-center gap-1">
            <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
            {isLast ? (
              <span
                className="rounded-full bg-slate-100 px-2 py-1 font-medium text-slate-900"
                aria-current="page"
              >
                {label}
              </span>
            ) : (
              <Link
                to={to}
                className="rounded-full px-2 py-1 transition-colors hover:bg-slate-50 hover:text-slate-900"
              >
                {label}
              </Link>
            )}
          </div>
        )
      })}
    </nav>
  )
}
