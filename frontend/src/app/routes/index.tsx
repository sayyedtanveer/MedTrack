import { createBrowserRouter } from "react-router-dom"
import { lazy, Suspense } from "react"
import { ProtectedRoute } from "./ProtectedRoute"
import AuthLayout from "@/layouts/AuthLayout"
import DefaultLayout from "@/layouts/DefaultLayout"
import { inventoryRoutes } from "@/modules/inventory/routes"
import { usersRoutes } from "@/modules/users/routes"
import { bomRoutes } from "@/modules/bom/routes"
import { productRoutes } from "@/modules/products/routes"
import { operationsRoutes } from "@/modules/operations/routes"
import { manufacturingRoutes } from "@/modules/manufacturing/routes"
import { salesRoutes } from "@/modules/sales/routes"
import { workOrderRoutes } from "@/modules/work-orders/routes"
import { shopFloorRoutes } from "@/modules/shop-floor/routes"
import { procurementRoutes } from "@/modules/procurement/routes"
import { financeRoutes } from "@/modules/finance/routes"
import { clientRoutes } from "@/modules/client/routes"
import { mrpRoutes } from "@/modules/mrp/routes"
import { NotFoundPage, ForbiddenPage } from "@/components/layout/ErrorPages"

// Lazy loaded modules
const LoginPage = lazy(() => import("@/modules/auth/pages/LoginPage"))
const RegisterTenantPage = lazy(() => import("@/modules/auth/pages/RegisterTenantPage"))
const DashboardPage = lazy(() => import("@/modules/dashboard/pages/DashboardPage"))
const SystemMapPage = lazy(() => import("@/modules/dashboard/pages/SystemMapPage"))
const ActivityLogPage = lazy(() => import("@/modules/audit/pages/ActivityLogPage"))
const StorekeeperDashboardPage = lazy(() => import("@/modules/inventory/pages/StorekeeperDashboardPage"))

// Error fallback component
const RouteErrorFallback = () => (
  <div className="flex h-[50vh] flex-col items-center justify-center p-8 text-center bg-destructive/10 rounded-lg m-4">
    <h2 className="text-xl font-semibold text-destructive mb-2">Failed to load page</h2>
    <p className="text-muted-foreground mb-4">There was an error loading this page. Please try again.</p>
    <a href="/" className="text-primary underline hover:text-primary/80">
      Return to Dashboard
    </a>
  </div>
)

// Loading fallback for Suspense
const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const router = createBrowserRouter([
  ...clientRoutes,
  {
    path: "/login",
    element: <AuthLayout />,
    errorElement: <RouteErrorFallback />,
    children: [
      { index: true, element: <Suspense fallback={<PageLoading />}><LoginPage /></Suspense> },
    ],
  },
  {
    path: "/register",
    element: <AuthLayout />,
    errorElement: <RouteErrorFallback />,
    children: [
      { index: true, element: <Suspense fallback={<PageLoading />}><RegisterTenantPage /></Suspense> },
    ],
  },
  {
    path: "/",
    element: <ProtectedRoute />, // All child routes require auth
    errorElement: <RouteErrorFallback />,
    children: [
      {
        path: "/",
        element: <DefaultLayout />,
        errorElement: <RouteErrorFallback />,
        children: [
          { index: true, element: <Suspense fallback={<PageLoading />}><DashboardPage /></Suspense> },
          { path: "dashboard/planner", element: <Suspense fallback={<PageLoading />}><DashboardPage /></Suspense> },
          { path: "dashboard/storekeeper", element: <Suspense fallback={<PageLoading />}><StorekeeperDashboardPage /></Suspense> },
          { path: "dashboard/sales", element: <Suspense fallback={<PageLoading />}><DashboardPage /></Suspense> },
          { path: "dashboard/qc", element: <Suspense fallback={<PageLoading />}><DashboardPage /></Suspense> },
          { path: "dashboard/client", element: <Suspense fallback={<PageLoading />}><DashboardPage /></Suspense> },
          { path: "system-map", element: <Suspense fallback={<PageLoading />}><SystemMapPage /></Suspense> },
          {
            path: "activity-log",
            element: (
              <ProtectedRoute allowedRoles={["ADMIN", "TENANT_ADMIN"]}>
                <Suspense fallback={<PageLoading />}>
                  <ActivityLogPage />
                </Suspense>
              </ProtectedRoute>
            ),
          },
          ...inventoryRoutes,
          ...usersRoutes,
          ...bomRoutes,
          ...productRoutes,
          ...operationsRoutes,
          ...manufacturingRoutes,
          ...salesRoutes,
          ...workOrderRoutes,
          ...shopFloorRoutes,
          ...procurementRoutes,
          ...financeRoutes,
          ...mrpRoutes,
          { path: "403", element: <ForbiddenPage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
])
