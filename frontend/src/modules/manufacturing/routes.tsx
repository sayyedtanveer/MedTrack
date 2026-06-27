/**
 * Manufacturing Module Routes - Operations and Workstations Management
 */

import { lazy, Suspense } from "react"
import { RouteObject } from "react-router-dom"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"

const OperationListPage = lazy(() => import("./pages/OperationListPage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const manufacturingRoutes: RouteObject[] = [
  {
    path: "manufacturing",
    children: [
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
            <Suspense fallback={<PageLoading />}><OperationListPage /></Suspense>
          </ProtectedRoute>
        ),
      },
    ],
  },
]
