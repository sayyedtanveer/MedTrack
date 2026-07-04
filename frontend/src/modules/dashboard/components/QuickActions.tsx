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
    <Card className="col-span-1 md:col-span-4 lg:col-span-2">
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">

        {/* Manufacturing Section */}
        {canManageProducts && (
          <>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground col-span-full mt-1">
              Manufacturing
            </p>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/products")}
            >
              <PackageSearch className="mr-2 h-5 w-5 text-blue-500" />
              Manage Products
            </Button>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/bom/list")}
            >
              <Layers className="mr-2 h-5 w-5 text-violet-500" />
              View BOMs
            </Button>
            <Separator className="col-span-full my-1" />
          </>
        )}

        {/* Inventory Section */}
        {canWorkInventory && (
          <>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground col-span-full">
              Inventory
            </p>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/inventory/products?action=scan")}
            >
              <ScanBarcode className="mr-2 h-5 w-5 text-primary" />
              Scan Barcode
            </Button>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/inventory/movements/add")}
            >
              <ArrowDownToLine className="mr-2 h-5 w-5 text-emerald-500" />
              Receive Goods
            </Button>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/inventory/movements/issue")}
            >
              <ArrowUpToLine className="mr-2 h-5 w-5 text-amber-500" />
              Issue Material
            </Button>
          </>
        )}

        {/* Admin Section */}
        {isAdmin() && (
          <>
            <Separator className="col-span-full my-1" />
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground col-span-full">
              Admin
            </p>
            {/* Phase 0: Number Series must be first in the setup flow (Gap #11) */}
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/settings/business-config/number-series")}
            >
              <Hash className="mr-2 h-5 w-5 text-orange-500" />
              Configure Number Series
            </Button>
            <Button
              className="w-full justify-start h-12"
              variant="outline"
              onClick={() => navigate("/users/new")}
            >
              <UserPlus className="mr-2 h-5 w-5 text-purple-500" />
              Add User
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
