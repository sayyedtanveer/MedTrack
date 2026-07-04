/**
 * Reports Module Routes
 */

import { lazy, Suspense } from "react"
import { RouteObject } from "react-router-dom"
import { getRolesForModule } from "@/lib/roles.config"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"

const ManufacturingKPIsPage = lazy(() => import("./pages/ManufacturingKPIsPage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>
const reportsRoles = getRolesForModule("reports")

export const reportsRoutes: RouteObject[] = [
  {
    path: "reports/manufacturing-kpis",
    element: (
      <ProtectedRoute allowedRoles={reportsRoles}>
        <Suspense fallback={<PageLoading />}>
          <ManufacturingKPIsPage />
        </Suspense>
      </ProtectedRoute>
    ),
  },
]
