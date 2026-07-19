import { lazy, Suspense, type ReactNode } from "react"
import { RouteObject, Navigate } from "react-router-dom"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"
import { getRolesForModule } from "@/lib/roles.config"

const BusinessConfigPage = lazy(() => import("./pages/BusinessConfigPage"))
const NumberSeriesPage = lazy(() => import("./pages/NumberSeriesPage"))
const NumberSeriesEntityConfigPage = lazy(() => import("./pages/NumberSeriesEntityConfigPage"))
const CompanySetupPage = lazy(() => import("./pages/CompanySetupPage"))
const SecuritySettingsPage = lazy(() => import("./pages/SecuritySettingsPage"))
const CompanyProfilePage = lazy(() => import("./pages/CompanyProfilePage"))
const UnitMasterPage = lazy(() => import("./pages/UnitMasterPage"))
const CategoryMasterPage = lazy(() => import("./pages/CategoryMasterPage"))
const LocationMasterPage = lazy(() => import("./pages/LocationMasterPage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>
const settingsRoles = getRolesForModule("settings")
const settingsElement = (children: ReactNode) => (
  <ProtectedRoute allowedRoles={settingsRoles}>
    <Suspense fallback={<PageLoading />}>{children}</Suspense>
  </ProtectedRoute>
)

export const settingsRoutes: RouteObject[] = [
  {
    // /settings → redirect to company-profile (the new settings landing)
    path: "settings",
    element: <Navigate to="/settings/company-profile" replace />,
  },
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
  // ── New routes ────────────────────────────────────────────────────────────
  {
    path: "settings/company-profile",
    element: settingsElement(<CompanyProfilePage />),
  },
  {
    path: "settings/master-data/units",
    element: settingsElement(<UnitMasterPage />),
  },
  {
    path: "settings/master-data/categories",
    element: settingsElement(<CategoryMasterPage />),
  },
  {
    path: "settings/master-data/locations",
    element: settingsElement(<LocationMasterPage />),
  },
]
