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
  "company-profile": "Company Profile",
  "master-data": "Master Data",
  "units": "Units of Measure",
  "categories": "Material Categories",
  "locations": "Storage Locations",
  "security": "Security",
  "manufacturing": "Manufacturing",
  "workstations": "Workstations",
  "workstations-master": "Workstations",
  "operations": "Operations",
  "reports": "Reports",
  "procurement": "Procurement",
  "suppliers": "Suppliers",
  "sales": "Sales",
  "clients": "Clients",
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
  const state = location.state as any
  const rawPaths = location.pathname.split("/").filter(Boolean)

  // Build standard breadcrumb items
  let items = rawPaths.map((segment, index) => {
    return {
      label: getSegmentLabel(segment),
      to: `/${rawPaths.slice(0, index + 1).join("/")}`
    }
  })

  // If user navigated here from Company Setup, intercept the breadcrumb
  if (state?.fromSetup) {
    items = [
      { label: "Settings", to: "/settings/company-profile" },
      { label: "Company Setup", to: "/settings/company-setup" },
      { label: getSegmentLabel(rawPaths[rawPaths.length - 1]), to: location.pathname }
    ]
  } else if (items.length > 0 && items[0].label === "Settings") {
     // Fix the 'Settings' root link to go to company profile instead of 404
     items[0].to = "/settings/company-profile"
  }

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

      {items.map((item, index) => {
        const isLast = index === items.length - 1

        return (
          <div key={`${item.to}-${index}`} className="flex items-center gap-1">
            <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
            {isLast ? (
              <span
                className="rounded-full bg-slate-100 px-2 py-1 font-medium text-slate-900"
                aria-current="page"
              >
                {item.label}
              </span>
            ) : (
              <Link
                to={item.to}
                className="rounded-full px-2 py-1 transition-colors hover:bg-slate-50 hover:text-slate-900"
              >
                {item.label}
              </Link>
            )}
          </div>
        )
      })}
    </nav>
  )
}
