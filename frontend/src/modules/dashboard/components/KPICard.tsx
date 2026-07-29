import { Link } from "react-router-dom"
import { KPIData } from "@/types/inventory.types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowDownIcon, ArrowRightIcon, ArrowUpIcon, PackageOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface KPICardProps {
  data: KPIData
  href?: string
  tone?: "primary" | "secondary" | "soft" | "glass"
}

export function KPICard({ data, href, tone = "primary" }: KPICardProps) {
  const toneClass =
    tone === "secondary"
      ? "bg-gradient-to-br from-indigo-500 via-purple-500 to-indigo-600 border-indigo-400/50 shadow-indigo-500/20"
      : tone === "soft"
        ? "bg-gradient-to-br from-blue-400 via-cyan-400 to-blue-500 border-blue-400/50 shadow-blue-500/20"
        : tone === "glass"
          ? "bg-white/70 backdrop-blur-xl border-slate-200/60 shadow-slate-200/50 text-slate-900"
          : "bg-gradient-to-br from-primary via-primary/90 to-primary/80 border-primary/50 shadow-primary/20"

  const content = (
    <Card className={cn(
      "overflow-hidden relative group transition-all duration-300 hover:-translate-y-1 hover:shadow-xl",
      "before:absolute before:inset-0 before:-z-10 before:bg-white/10 before:opacity-0 hover:before:opacity-100 before:transition-opacity",
      toneClass, 
      href && "cursor-pointer"
    )}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
        <CardTitle
          className={cn(
            "text-[11px] font-semibold uppercase tracking-[0.18em] sm:tracking-[0.24em]",
            tone === "glass" ? "text-slate-700" : "text-white drop-shadow-sm"
          )}
        >
          {data.label}
        </CardTitle>
        <div
          className={cn(
            "rounded-2xl border p-2.5 shadow-sm transition-transform duration-300 group-hover:scale-110",
            tone === "glass" ? "border-blue-200/50 bg-blue-50/50 text-blue-700" : "border-white/20 bg-white/10 text-white backdrop-blur-md"
          )}
        >
          <PackageOpen className={cn("h-4 w-4", tone !== "glass" && "drop-shadow-sm")} />
        </div>
      </CardHeader>
      <CardContent>
        <div className={cn("text-3xl font-bold leading-none sm:text-[2rem]", tone === "glass" ? "text-slate-950" : "text-white drop-shadow-sm")}>
          {data.value}
        </div>
        <p className={cn("mt-4 flex items-center text-xs font-medium", tone === "glass" ? "text-slate-600" : "text-white/90 drop-shadow-sm")}>
          {data.trend === "up" && <ArrowUpIcon className={cn("mr-1 h-3 w-3", tone === "glass" ? "text-emerald-500" : "text-emerald-50")} />}
          {data.trend === "down" && <ArrowDownIcon className={cn("mr-1 h-3 w-3", tone === "glass" ? "text-red-500" : "text-rose-50")} />}
          {data.trend === "neutral" && <ArrowRightIcon className={cn("mr-1 h-3 w-3", tone === "glass" ? "text-slate-500" : "text-white/85")} />}
          <span
            className={
              data.trend === "down" && data.label.includes("Alerts")
                ? tone === "glass"
                  ? "font-medium text-red-600"
                  : "font-medium text-rose-50"
                : data.trend === "up" && !data.label.includes("Alerts")
                  ? tone === "glass"
                    ? "font-medium text-emerald-600"
                    : "font-medium text-emerald-50"
                  : ""
            }
          >
            {data.change > 0 ? "+" : ""}{data.change}
          </span>
          <span className={cn("ml-1", tone === "glass" ? "text-slate-600" : "text-white/85")}>
            from last month
          </span>
        </p>
      </CardContent>
    </Card>
  )

  if (href) {
    return <Link to={href} className="block">{content}</Link>
  }

  return content
}
