import { RouteObject } from "react-router-dom"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"
import ProcurementHubPage from "./pages/ProcurementHubPage"
import SuppliersListPage from "./pages/SuppliersListPage"
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage"
import PurchaseOrderDetailPage from "./pages/PurchaseOrderDetailPage"
import GrnPage from "./pages/GrnPage"
import QualityModulePage from "./pages/QualityModulePage"
import MaterialRequestsPage from "./pages/MaterialRequestsPage"
import SubcontractListPage from "./pages/SubcontractListPage"
import SubcontractOrderDetailPage from "./pages/SubcontractOrderDetailPage"
import SupplierPortalPage from "./pages/SupplierPortalPage"
import SupplierPortalPoDetailPage from "./pages/SupplierPortalPoDetailPage"
import SupplierPortalProfilePage from "./pages/SupplierPortalProfilePage"
import SupplierPortalInvoicesPage from "./pages/SupplierPortalInvoicesPage"
import SupplierPortalInvoiceCreatePage from "./pages/SupplierPortalInvoiceCreatePage"
import SupplierPortalPaymentsPage from "./pages/SupplierPortalPaymentsPage"
import SupplierPortalQuotationsPage from "./pages/SupplierPortalQuotationsPage"
import SupplierPortalQuotationDetailPage from "./pages/SupplierPortalQuotationDetailPage"
import SupplierPortalReceiptsPage from "./pages/SupplierPortalReceiptsPage"
import RFQListPage from "./pages/RFQListPage"
import RFQCreatePage from "./pages/RFQCreatePage"
import RFQDetailPage from "./pages/RFQDetailPage"
import SupplierPerformancePage from "./pages/SupplierPerformancePage"
import ProcurementDashboardPage from "./pages/ProcurementDashboardPage"

export const procurementRoutes: RouteObject[] = [
  { path: "procurement", element: <ProcurementHubPage /> },
  { path: "procurement/dashboard", element: <ProcurementDashboardPage /> },
  { path: "procurement/suppliers", element: <SuppliersListPage /> },
  { path: "procurement/purchase-orders", element: <PurchaseOrdersPage /> },
  { path: "procurement/purchase-orders/:poId", element: <PurchaseOrderDetailPage /> },
  { path: "procurement/grn", element: <GrnPage /> },
  { path: "procurement/quality", element: <QualityModulePage /> },
  { path: "procurement/mrp", element: <MaterialRequestsPage /> },
  { path: "procurement/subcontract", element: <SubcontractListPage /> },
  { path: "procurement/subcontract/:orderId", element: <SubcontractOrderDetailPage /> },
  // ── RFQ ──────────────────────────────────────────────────────────────
  { path: "procurement/rfq", element: <RFQListPage /> },
  { path: "procurement/rfq/new", element: <RFQCreatePage /> },
  { path: "procurement/rfq/:rfqId", element: <RFQDetailPage /> },
  // ── Supplier performance ──────────────────────────────────────────────
  { path: "procurement/supplier-performance", element: <SupplierPerformancePage /> },
  // ── Supplier portal ───────────────────────────────────────────────────
  {
    path: "supplier-portal",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/po/:poId",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalPoDetailPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/profile",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalProfilePage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/quotations",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalQuotationsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/quotations/:quotationId",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalQuotationDetailPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/receipts",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalReceiptsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/invoices",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalInvoicesPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/invoices/new",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalInvoiceCreatePage />
      </ProtectedRoute>
    ),
  },
  {
    path: "supplier-portal/payments",
    element: (
      <ProtectedRoute allowedRoles={["SUPPLIER"]}>
        <SupplierPortalPaymentsPage />
      </ProtectedRoute>
    ),
  },
]
