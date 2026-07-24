/**
 * Manufacturing Module Routes - Operations, Workstations, and Production Dashboard
 */

import { lazy, Suspense } from "react"
import { RouteObject } from "react-router-dom"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"

const OperationListPage = lazy(() => import("./pages/OperationListPage"))
const ProductionDashboardPage = lazy(() => import("./pages/ProductionDashboardPage"))
const WorkstationMasterPage = lazy(() => import("./pages/WorkstationMasterPage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const manufacturingRoutes: RouteObject[] = [
  {
    path: "manufacturing",
    children: [
      {
        path: "dashboard",
        element: (
          <Suspense fallback={<PageLoading />}>
            <ProductionDashboardPage />
          </Suspense>
        ),
      },
      {
        path: "operations-master",
        element: (
          <ProtectedRoute roles={["ADMIN", "MANAGER"]}>
            <Suspense fallback={<PageLoading />}><OperationListPage /></Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: "workstations-master",
        element: (
          <ProtectedRoute roles={["ADMIN", "MANAGER"]}>
            <Suspense fallback={<PageLoading />}><WorkstationMasterPage /></Suspense>
          </ProtectedRoute>
        ),
      },
    ],
  },
]
