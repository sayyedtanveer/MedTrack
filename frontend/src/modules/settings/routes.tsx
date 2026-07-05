import { lazy, Suspense, type ReactNode } from "react"
import { RouteObject } from "react-router-dom"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"
import { getRolesForModule } from "@/lib/roles.config"

const BusinessConfigPage = lazy(() => import("./pages/BusinessConfigPage"))
const NumberSeriesPage = lazy(() => import("./pages/NumberSeriesPage"))
const NumberSeriesEntityConfigPage = lazy(() => import("./pages/NumberSeriesEntityConfigPage"))
const CompanySetupPage = lazy(() => import("./pages/CompanySetupPage"))
const SecuritySettingsPage = lazy(() => import("./pages/SecuritySettingsPage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>
const settingsRoles = getRolesForModule("settings")
const settingsElement = (children: ReactNode) => (
  <ProtectedRoute allowedRoles={settingsRoles}>
    <Suspense fallback={<PageLoading />}>{children}</Suspense>
  </ProtectedRoute>
)

export const settingsRoutes: RouteObject[] = [
  {
    path: "settings/business-config",
    element: settingsElement(<BusinessConfigPage />),
  },
  {
    path: "settings/business-config/number-series",
    element: settingsElement(<NumberSeriesPage />),
  },
  {
    path: "settings/business-config/number-series/:entityType",
    element: settingsElement(<NumberSeriesEntityConfigPage />),
  },
  {
    path: "settings/company-setup",
    element: settingsElement(<CompanySetupPage />),
  },
  {
    path: "settings/security",
    element: settingsElement(<SecuritySettingsPage />),
  },
]
