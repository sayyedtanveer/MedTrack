import { usePermissions } from "@/hooks/usePermissions"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  ArrowDownToLine,
  ArrowUpToLine,
  ScanBarcode,
  UserPlus,
  PackageSearch,
  Layers,
  Hash,
} from "lucide-react"
import { useNavigate } from "react-router-dom"

export function QuickActions() {
  const { hasRole, isAdmin } = usePermissions()
  const navigate = useNavigate()

  const canWorkInventory = hasRole(["ADMIN", "MANAGER", "OPERATOR"])
  const canManageProducts = hasRole(["ADMIN", "MANAGER"])

  return (
    <Card className="col-span-1 md:col-span-4 lg:col-span-2 border-slate-200/60 bg-white/70 backdrop-blur-xl shadow-lg relative overflow-hidden">
      {/* Decorative gradient blob */}
      <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <CardHeader className="pb-3 border-b border-slate-100/50 bg-white/40">
        <CardTitle className="text-lg font-semibold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 grid-cols-1 sm:grid-cols-2 pt-4">

        {/* Manufacturing Section */}
        {canManageProducts && (
          <>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 col-span-full mt-2 ml-1">
              Manufacturing
            </p>
            <Button
              className="w-full justify-start h-auto min-h-[3.5rem] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group/btn text-slate-700 h-full whitespace-normal text-left"
              variant="outline"
              onClick={() => navigate("/products")}
            >
              <div className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-blue-100 to-blue-50 border border-slate-200/60 flex items-center justify-center mr-3 transition-transform duration-300 group-hover/btn:scale-110 group-hover/btn:rotate-3 shadow-sm">
                <PackageSearch className="h-5 w-5 text-blue-600" />
              </div>
              <div className="flex flex-col items-start">
                <span className="font-semibold text-sm">Manage Products</span>
              </div>
            </Button>
            <Button
              className="w-full justify-start h-auto min-h-[3.5rem] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group/btn text-slate-700 h-full whitespace-normal text-left"
              variant="outline"
              onClick={() => navigate("/bom/list")}
            >
              <div className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-violet-100 to-violet-50 border border-slate-200/60 flex items-center justify-center mr-3 transition-transform duration-300 group-hover/btn:scale-110 group-hover/btn:rotate-3 shadow-sm">
                <Layers className="h-5 w-5 text-violet-600" />
              </div>
              <div className="flex flex-col items-start">
                <span className="font-semibold text-sm">View BOMs</span>
              </div>
            </Button>
            <Separator className="col-span-full my-1 bg-slate-100/50" />
          </>
        )}

        {/* Inventory Section */}
        {canWorkInventory && (
          <>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 col-span-full ml-1">
              Inventory
            </p>
            <Button
              className="w-full justify-start h-auto min-h-[3.5rem] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group/btn text-slate-700 h-full whitespace-normal text-left"
              variant="outline"
              onClick={() => navigate("/inventory/products?action=scan")}
            >
              <div className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 border border-slate-200/60 flex items-center justify-center mr-3 transition-transform duration-300 group-hover/btn:scale-110 group-hover/btn:rotate-3 shadow-sm">
                <ScanBarcode className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col items-start">
                <span className="font-semibold text-sm">Scan Barcode</span>
              </div>
            </Button>
            <Button
              className="w-full justify-start h-auto min-h-[3.5rem] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group/btn text-slate-700 h-full whitespace-normal text-left"
              variant="outline"
              onClick={() => navigate("/inventory/movements")}
            >
              <div className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-emerald-100 to-emerald-50 border border-slate-200/60 flex items-center justify-center mr-3 transition-transform duration-300 group-hover/btn:scale-110 group-hover/btn:rotate-3 shadow-sm">
                <ArrowDownToLine className="h-5 w-5 text-emerald-600" />
              </div>
              <div className="flex flex-col items-start">
                <span className="font-semibold text-sm">Receive Goods</span>
              </div>
            </Button>
            <Button
              className="w-full justify-start h-auto min-h-[3.5rem] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group/btn text-slate-700 h-full whitespace-normal text-left"
              variant="outline"
              onClick={() => navigate("/inventory/movements")}
            >
              <div className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-amber-100 to-amber-50 border border-slate-200/60 flex items-center justify-center mr-3 transition-transform duration-300 group-hover/btn:scale-110 group-hover/btn:rotate-3 shadow-sm">
                <ArrowUpToLine className="h-5 w-5 text-amber-600" />
              </div>
              <div className="flex flex-col items-start">
                <span className="font-semibold text-sm">Issue Material</span>
              </div>
            </Button>
          </>
        )}

        {/* Admin Section */}
        {isAdmin() && (
          <>
            <Separator className="col-span-full my-1 bg-slate-100/50" />
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 col-span-full ml-1">
              Admin
            </p>
            {/* Phase 0: Number Series must be first in the setup flow (Gap #11) */}
            <Button
              className="w-full justify-start h-auto min-h-[3.5rem] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group/btn text-slate-700 h-full whitespace-normal text-left"
              variant="outline"
              onClick={() => navigate("/settings/business-config/number-series")}
            >
              <div className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-orange-100 to-orange-50 border border-slate-200/60 flex items-center justify-center mr-3 transition-transform duration-300 group-hover/btn:scale-110 group-hover/btn:rotate-3 shadow-sm">
                <Hash className="h-5 w-5 text-orange-600" />
              </div>
              <div className="flex flex-col items-start">
                <span className="font-semibold text-sm">Number Series</span>
              </div>
            </Button>
            <Button
              className="w-full justify-start h-auto min-h-[3.5rem] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group/btn text-slate-700 h-full whitespace-normal text-left"
              variant="outline"
              onClick={() => navigate("/users")}
            >
              <div className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-purple-100 to-purple-50 border border-slate-200/60 flex items-center justify-center mr-3 transition-transform duration-300 group-hover/btn:scale-110 group-hover/btn:rotate-3 shadow-sm">
                <UserPlus className="h-5 w-5 text-purple-600" />
              </div>
              <div className="flex flex-col items-start">
                <span className="font-semibold text-sm">Add User</span>
              </div>
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
