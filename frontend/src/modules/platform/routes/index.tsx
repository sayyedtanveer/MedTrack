import { lazy, Suspense } from "react"
import { RouteObject, Navigate } from "react-router-dom"
import { PlatformRoute } from "./PlatformRoute"
import { PlatformLayout } from "../layouts/PlatformLayout"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"

const PlatformDashboard = lazy(() => import("../pages/PlatformDashboard"))
const PlatformTenants = lazy(() => import("../pages/PlatformTenants"))
const PlatformTenantDetails = lazy(() => import("../pages/PlatformTenantDetails"))

// Loading fallback matching premium UI standard (skeleton used in the pages instead of here, 
// but for the lazy load Suspense boundary, a simple loading or null is fine, the components will render skeletons)
const PageLoading = () => <div className="p-8 flex items-center justify-center text-muted-foreground">Loading module...</div>

// Future placeholders
const PlaceholderPage = ({ title }: { title: string }) => (
  <div className="flex h-[50vh] flex-col items-center justify-center p-8 text-center rounded-lg border border-dashed m-4">
    <h2 className="text-xl font-semibold mb-2">{title}</h2>
    <p className="text-muted-foreground">This module is under construction.</p>
  </div>
)

export const platformRoutes: RouteObject[] = [
  {
    path: "platform",
    element: (
      <ProtectedRoute allowedRoles={["TENANT_ADMIN", "ADMIN"]}>
        <PlatformRoute />
      </ProtectedRoute>
    ),
    children: [
      {
        path: "",
        element: <PlatformLayout />,
        children: [
          { index: true, element: <Suspense fallback={<PageLoading />}><PlatformDashboard /></Suspense> },
          { path: "dashboard", element: <Navigate to="/platform" replace /> },
          { path: "tenants", element: <Suspense fallback={<PageLoading />}><PlatformTenants /></Suspense> },
          { path: "tenants/:id", element: <Suspense fallback={<PageLoading />}><PlatformTenantDetails /></Suspense> },
          { path: "subscriptions", element: <PlaceholderPage title="Subscription Management" /> },
          { path: "audit-logs", element: <PlaceholderPage title="Audit Logs" /> },
          { path: "email-logs", element: <PlaceholderPage title="Email Logs" /> },
          { path: "notifications", element: <PlaceholderPage title="Notifications" /> },
          { path: "settings", element: <PlaceholderPage title="System Settings" /> },
        ],
      },
    ],
  },
]
