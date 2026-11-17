import { lazy, Suspense, type ReactNode } from "react"
import { RouteObject } from "react-router-dom"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"
import { getRolesForModule } from "@/lib/roles.config"

const MaterialListPage = lazy(() => import("./pages/MaterialListPage"))
const ProductListPage = lazy(() => import("./pages/ProductListPage"))
const TransactionHistoryPage = lazy(() => import("./pages/TransactionHistoryPage"))
const StockMovementPage = lazy(() => import("./pages/StockMovementPage"))
const InventoryDashboard = lazy(() => import("./pages/InventoryDashboard"))
const BatchListPage = lazy(() => import("./pages/BatchListPage"))
const StorekeeperDashboardPage = lazy(() => import("./pages/StorekeeperDashboardPage"))
const MaterialOnboardingPage = lazy(() => import("./pages/MaterialOnboardingPage"))
const MaterialBuyPage = lazy(() => import("./pages/MaterialBuyPage"))

// Simple fallback
const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>
const inventoryRoles = getRolesForModule("inventory")
const inventoryElement = (children: ReactNode) => (
  <ProtectedRoute allowedRoles={inventoryRoles}>
    <Suspense fallback={<PageLoading />}>{children}</Suspense>
  </ProtectedRoute>
)

export const inventoryRoutes: RouteObject[] = [
  {
    path: "inventory",
    element: inventoryElement(<InventoryDashboard />),
  },
  {
    path: "inventory/materials",
    element: inventoryElement(<MaterialListPage />),
  },
  {
    path: "inventory/products",
    element: inventoryElement(<ProductListPage />),
  },
  {
    path: "inventory/transactions",
    element: inventoryElement(<TransactionHistoryPage />),
  },
  {
    path: "inventory/movements",
    element: inventoryElement(<StockMovementPage />),
  },
  {
    path: "inventory/batches",
    element: inventoryElement(<BatchListPage />),
  },
  {
    path: "inventory/storekeeper",
    element: inventoryElement(<StorekeeperDashboardPage />),
  },
  {
    path: "inventory/material-onboarding",
    element: inventoryElement(<MaterialOnboardingPage />),
  },
  {
    path: "inventory/material-buy",
    element: inventoryElement(<MaterialBuyPage />),
  },
]
