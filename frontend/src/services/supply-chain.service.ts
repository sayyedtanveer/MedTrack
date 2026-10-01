import { apiClient } from "./api-client"

// Use central `apiClient` baseURL. Keep this empty so `apiClient` controls the prefix.
const BASE = ""

const asArray = <T>(payload: T[] | { items?: T[] } | null | undefined): T[] => {
  if (Array.isArray(payload)) return payload
  return payload?.items ?? []
}

const toNumber = (value: unknown): number => {
  const parsed = Number(value ?? 0)
  return Number.isFinite(parsed) ? parsed : 0
}

const normalizePoLine = (line: PurchaseOrderLine): PurchaseOrderLine => ({
  ...line,
  quantity: toNumber(line.quantity),
  received_quantity: toNumber(line.received_quantity),
  unit_price: toNumber(line.unit_price),
  line_total: toNumber(line.line_total),
})

const normalizePo = (po: PurchaseOrder): PurchaseOrder => ({
  ...po,
  total_amount: toNumber(po.total_amount),
  lines: Array.isArray(po.lines) ? po.lines.map(normalizePoLine) : [],
})

const withData = async <TResponse, TData>(
  request: Promise<{ data: TResponse }>,
  transform: (data: TResponse) => TData
) => {
  const response = await request
  return { ...response, data: transform(response.data) }
}

export type Supplier = {
  id: string
  code: string
  name: string
  contact_person?: string | null
  email?: string | null
  phone?: string | null
  address?: string | null
  gst?: string | null
  payment_terms?: string | null
  performance_rating?: number | null
  profile_completeness?: number
  is_active: boolean
}

export type PurchaseOrderLine = {
  id: string
  material_id: string
  quantity: number
  received_quantity: number
  unit_price: number
  line_total?: number
}

export type PurchaseOrder = {
  id: string
  po_number: string
  supplier_id: string
  status: string
  order_date: string
  expected_delivery?: string | null
  total_amount: number
  notes?: string | null
  lines: PurchaseOrderLine[]
}

export type SubcontractOrderSummary = {
  id: string
  order_number: string
  supplier_id: string
  supplier_name?: string
  supplier_code?: string
  product_id: string
  product_code?: string
  product_name?: string
  product_type: string
  quantity: number
  received_quantity: number
  status: string
  bom_id?: string | null
  due_date?: string | null
  notes?: string | null
  output_batch_id?: string | null
}

export type SubcontractOrderLine = {
  id: string
  material_id: string
  required_quantity: number
  issued_quantity: number
  returned_quantity: number
  status: string
}

export type SubcontractIssueRecord = {
  id: string
  material_id: string
  quantity: number
  returned_quantity: number
  batch_id?: string | null
  batch_number?: string | null
  from_location_id?: string | null
  issued_at?: string | null
}

export type SubcontractOrderDetail = SubcontractOrderSummary & {
  lines: SubcontractOrderLine[]
  issues: SubcontractIssueRecord[]
  approved_by?: string | null
  approved_at?: string | null
}

export type MaterialRequest = {
  id: string
  item_id: string
  item_type: string
  required_quantity: number
  fulfilled_quantity: number
  status: string
}

export type InspectionRow = {
  id: string
  reference_type: string
  reference_id: string
  result: string
  inspection_date: string
}

export type NCRRow = {
  id: string
  inspection_id: string | null
  ncr_type: string
  reason?: string | null
  action_taken?: string | null
  created_at?: string | null
}

export type QuarantineRow = {
  material_id: string
  material_code: string
  material_name: string
  location_id: string
  location_name: string
  quantity: number
}

export type InspectionTemplate = {
  id: string
  tenant_id: string
  name: string
  parameters: Record<string, unknown>[]
  is_active: boolean
}

export const supplyChainApi = {
  listSuppliers: () =>
    withData(apiClient.get<Supplier[] | { items: Supplier[] }>(`${BASE}/suppliers`), asArray),
  createSupplier: (body: {
    code: string
    name: string
    contact_person?: string
    email?: string
    phone?: string
    address?: string
    gst?: string
    payment_terms?: string
  }) => apiClient.post<Supplier>(`${BASE}/suppliers`, body),
  updateSupplier: (
    id: string,
    body: {
      name?: string
      contact_person?: string
      email?: string
      phone?: string
      address?: string
      gst?: string
      payment_terms?: string
      performance_rating?: number
      is_active?: boolean
    }
  ) => apiClient.put<Supplier>(`${BASE}/suppliers/${id}`, body),

  listPurchaseOrders: () =>
    withData(
      apiClient.get<PurchaseOrder[] | { items: PurchaseOrder[] }>(`${BASE}/purchase-orders`),
      (data) => asArray(data).map(normalizePo)
    ),
  getPurchaseOrder: (id: string) =>
    withData(apiClient.get<PurchaseOrder>(`${BASE}/purchase-orders/${id}`), normalizePo),
  createPurchaseOrder: (body: {
    supplier_id: string
    expected_delivery?: string
    notes?: string
    lines: { material_id: string; quantity: number; unit_price: number }[]
  }) => apiClient.post<{ id: string; po_number: string }>(`${BASE}/purchase-orders`, body),

  sendPO: (id: string) => apiClient.put(`${BASE}/purchase-orders/${id}/send`),
  acknowledgePO: (id: string) => apiClient.put(`${BASE}/purchase-orders/${id}/acknowledge`),
  receiveGoods: (
    id: string,
    body: { lines: { line_id: string; quantity: number }[]; warehouse_location_id?: string }
  ) => apiClient.put(`${BASE}/purchase-orders/${id}/receive`, body),

  qualityInspect: (body: Record<string, unknown>) => apiClient.post(`${BASE}/quality/inspect`, body),
  createNCR: (body: Record<string, unknown>) => apiClient.post(`${BASE}/quality/ncr`, body),
  listInspections: () => apiClient.get<InspectionRow[]>(`${BASE}/quality/inspections`),
  listNCRs: () => apiClient.get<NCRRow[]>(`${BASE}/quality/ncrs`),
  quarantineStock: () => apiClient.get<QuarantineRow[]>(`${BASE}/quarantine-stock`),

  listInspectionTemplates: () => apiClient.get<InspectionTemplate[]>(`${BASE}/inspection-templates`),
  getInspectionTemplate: (id: string) =>
    apiClient.get<InspectionTemplate>(`${BASE}/inspection-templates/${id}`),
  createInspectionTemplate: (body: {
    name: string
    parameters?: Record<string, unknown>[]
    is_active?: boolean
  }) => apiClient.post<InspectionTemplate>(`${BASE}/inspection-templates`, body),
  updateInspectionTemplate: (
    id: string,
    body: { name?: string; parameters?: Record<string, unknown>[]; is_active?: boolean }
  ) => apiClient.put<InspectionTemplate>(`${BASE}/inspection-templates/${id}`, body),
  deleteInspectionTemplate: (id: string) => apiClient.delete(`${BASE}/inspection-templates/${id}`),

  listMaterialRequests: () => apiClient.get<MaterialRequest[]>(`${BASE}/material-requests`),
  runMrp: () => apiClient.post<{ created: number }>(`${BASE}/material-requests/run-mrp`),

  listSubcontractOrders: () => apiClient.get<{ total: number; items: SubcontractOrderSummary[] }>(`${BASE}/subcontract/orders`),
  getSubcontractOrder: (id: string) => apiClient.get<SubcontractOrderDetail>(`${BASE}/subcontract/orders/${id}`),
  createSubcontractOrder: (body: {
    supplier_id: string
    product_id: string
    product_type?: string
    quantity: number
    bom_id?: string | null
    due_date?: string | null
    notes?: string | null
  }) => apiClient.post(`${BASE}/subcontract/orders`, body),
  approveSubcontractOrder: (id: string) =>
    apiClient.post(`${BASE}/subcontract/orders/${id}/approve`, {}),
  cancelSubcontractOrder: (id: string) =>
    apiClient.post(`${BASE}/subcontract/orders/${id}/cancel`, {}),
  issueSubcontract: (orderId: string, body: {
    material_id: string
    quantity: number
    from_location_id: string
    batch_id?: string | null
    batch_number?: string | null
  }) => apiClient.post(`${BASE}/subcontract/orders/${orderId}/issue`, body),
  receiveSubcontract: (orderId: string, body: {
    material_id: string
    quantity: number
    warehouse_location_id: string
    output_batch_number?: string | null
  }) => apiClient.post(`${BASE}/subcontract/orders/${orderId}/receive`, body),
  returnSubcontractMaterial: (orderId: string, body: {
    material_id: string
    quantity: number
    to_location_id: string
    batch_id?: string | null
  }) => apiClient.post(`${BASE}/subcontract/orders/${orderId}/return-material`, body),
  getSubcontractTraceability: (id: string) =>
    apiClient.get(`${BASE}/subcontract/orders/${id}/traceability`),
  getBOMsForSubcontractMaterial: (materialId: string) =>
    apiClient.get<{
      material_id: string
      material_code: string
      material_name: string
      material_type: string
      boms: Array<{
        id: string
        version: string
        is_active: boolean
        valid_from: string | null
        valid_to: string | null
        line_count: number
        variant_id: string
        variant_name: string
        link_type: "explicit" | "code_match"
      }>
    }>(`${BASE}/subcontract/boms-for-material/${materialId}`),

  getBOMLines: (bomId: string) =>
    apiClient.get<{
      id: string
      version: string
      lines: Array<{
        id: string
        material_id: string | null
        quantity: number
        scrap_percentage: number
      }>
    }>(`/boms/${bomId}`),

  supplierPortalPOs: (params?: { status?: string; skip?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set("status", params.status)
    if (params?.skip != null) qs.set("skip", String(params.skip))
    if (params?.limit != null) qs.set("limit", String(params.limit))
    const query = qs.toString() ? `?${qs.toString()}` : ""
    return withData(apiClient.get<{
      total: number
      skip: number
      limit: number
      items: {
        id: string
        po_number: string
        status: string
        total_amount: number
        supplier_id: string
        order_date: string
        expected_delivery?: string | null
        notes?: string | null
        lines: PurchaseOrderLine[]
      }[]
    }>(`${BASE}/supplier/purchase-orders${query}`), (data) => ({
      ...data,
      items: data.items.map((po) => normalizePo(po as PurchaseOrder)),
    }))
  },
  supplierPortalPO: (id: string) =>
    withData(apiClient.get<PurchaseOrder>(`${BASE}/supplier/purchase-orders/${id}`), normalizePo),
  supplierAckPO: (id: string) => apiClient.put(`${BASE}/supplier/purchase-orders/${id}/acknowledge`),
  supplierDashboard: () => apiClient.get<SupplierDashboard>(`${BASE}/supplier/dashboard`),
  supplierProfile: () => apiClient.get<SupplierProfile>(`${BASE}/supplier/profile`),
  supplierUpdateProfile: (body: SupplierProfileUpdateInput) =>
    apiClient.put<SupplierProfile>(`${BASE}/supplier/profile`, body),
  supplierCreateShipmentNotice: (poId: string, body: SupplierShipmentNoticeInput) =>
    apiClient.post<SupplierReceipt>(`${BASE}/supplier/purchase-orders/${poId}/shipment-notices`, body),
  supplierQuotation: (body: Record<string, unknown>) => apiClient.post(`${BASE}/supplier/quotations`, body),
  supplierListQuotations: () => apiClient.get<SupplierQuotation[]>(`${BASE}/supplier/quotations`),
  supplierGetQuotation: (id: string) => apiClient.get<SupplierQuotation>(`${BASE}/supplier/quotations/${id}`),
  supplierSubmitQuotation: (id: string) => apiClient.put(`${BASE}/supplier/quotations/${id}/submit`),

  // ── RFQ ─────────────────────────────────────────────────────────────────
  listRFQs: () => apiClient.get<RFQSummary[]>(`${BASE}/rfq`),
  getRFQ: (id: string) => apiClient.get<RFQDetail>(`${BASE}/rfq/${id}`),
  createRFQ: (body: RFQCreateInput) =>
    apiClient.post<{ id: string; rfq_number: string }>(`${BASE}/rfq`, body),
  sendRFQ: (id: string) => apiClient.post(`${BASE}/rfq/${id}/send`),
  awardRFQ: (id: string, body: RFQAwardInput) =>
    apiClient.post<{ po_id: string; po_number: string }>(`${BASE}/rfq/${id}/award`, body),

  // ── Supplier performance (buyer view) ────────────────────────────────────
  listSupplierPerformance: () => apiClient.get<SupplierPerformance[]>(`${BASE}/supplier-performance`),
  getSupplierPerformance: (supplierId: string) =>
    apiClient.get<SupplierPerformance>(`${BASE}/supplier-performance/${supplierId}`),

  // ── Supplier portal extras ───────────────────────────────────────────────
  supplierListRFQs: () => apiClient.get<RFQSummary[]>(`${BASE}/supplier/rfq`),
  supplierSubmitRFQQuote: (rfqId: string, body: Record<string, unknown>) =>
    apiClient.post<{ id: string }>(`${BASE}/supplier/rfq/${rfqId}/quote`, body),
  supplierOwnPerformance: () => apiClient.get<SupplierPerformance>(`${BASE}/supplier/performance`),
  supplierListReceipts: (params?: PageParams) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set("page", String(params.page))
    if (params?.page_size) qs.set("page_size", String(params.page_size))
    const query = qs.toString() ? `?${qs.toString()}` : ""
    return apiClient.get<PagedResponse<SupplierReceipt>>(`${BASE}/supplier/receipts${query}`)
  },
  supplierListInvoices: (params?: PageParams & { status?: string }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set("status", params.status)
    if (params?.page) qs.set("page", String(params.page))
    if (params?.page_size) qs.set("page_size", String(params.page_size))
    const query = qs.toString() ? `?${qs.toString()}` : ""
    return apiClient.get<PagedResponse<SupplierInvoice>>(`${BASE}/supplier/invoices${query}`)
  },
  supplierGetInvoice: (invoiceId: string) =>
    apiClient.get<SupplierInvoice>(`${BASE}/supplier/invoices/${invoiceId}`),
  supplierCreateInvoice: (body: SupplierInvoiceInput) =>
    apiClient.post<SupplierInvoice>(`${BASE}/supplier/invoices`, body),
  supplierListPayments: (params?: PageParams) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set("page", String(params.page))
    if (params?.page_size) qs.set("page_size", String(params.page_size))
    const query = qs.toString() ? `?${qs.toString()}` : ""
    return apiClient.get<PagedResponse<SupplierPayment>>(`${BASE}/supplier/payments${query}`)
  },
  supplierDisputeInvoice: (invoiceId: string, body: { disputed_amount: number; reason: string }) =>
    apiClient.post<{ id: string; status: string }>(`${BASE}/supplier/invoices/${invoiceId}/dispute`, body),
  supplierGetInvoiceDisputes: (invoiceId: string) =>
    apiClient.get<InvoiceDispute[]>(`${BASE}/supplier/invoices/${invoiceId}/disputes`),
  resolveDispute: (disputeId: string, body: { resolution: string; resolution_notes?: string }) =>
    apiClient.put(`${BASE}/invoices/${disputeId}/dispute/resolve`, body),
}

// ── Additional types ─────────────────────────────────────────────────────────

export type PageParams = {
  page?: number
  page_size?: number
}

export type PagedResponse<T> = {
  items: T[]
  total: number
  page: number
  pages: number
}

export type SupplierProfile = Supplier & {
  changed_fields?: string[]
}

export type SupplierProfileUpdateInput = Pick<
  Supplier,
  "contact_person" | "email" | "phone" | "address" | "gst" | "payment_terms"
>

export type SupplierDashboard = {
  supplier: SupplierProfile
  purchase_orders: { by_status: Record<string, number>; total: number }
  quotations: { by_status: Record<string, number>; total: number }
  invoices: { by_status: Record<string, number>; total: number; outstanding: number }
  receipts: { pending: number }
  performance: { rating?: number | null }
  recent_purchase_orders: PurchaseOrder[]
  action_items: { type: string; label: string; count: number; href: string }[]
}

export type SupplierQuotation = {
  id: string
  quotation_number: string
  supplier_id: string
  purchase_order_id?: string | null
  material_id: string
  material_code: string
  material_name: string
  quantity: number
  unit_price: number
  valid_until?: string | null
  status: string
  created_at?: string | null
  updated_at?: string | null
}

export type SupplierReceiptLine = {
  id: string
  po_line_id: string
  material_id: string
  po_quantity: number
  received_quantity: number
  accepted_quantity: number
  rejected_quantity: number
  unit_price: number
  remarks?: string | null
}

export type SupplierReceipt = {
  id: string
  grn_number: string
  purchase_order_id: string
  supplier_id: string
  status: string
  actual_receipt_date?: string | null
  driver_name?: string | null
  vehicle_number?: string | null
  transport_company?: string | null
  tracking_number?: string | null
  remarks?: string | null
  created_at?: string | null
  lines: SupplierReceiptLine[]
}

export type SupplierShipmentNoticeInput = {
  driver_name?: string
  vehicle_number?: string
  transport_company?: string
  tracking_number?: string
  remarks?: string
  lines: { po_line_id: string; quantity: number; remarks?: string }[]
}

export type SupplierInvoice = {
  id: string
  invoice_number: string
  supplier_invoice_ref?: string | null
  purchase_order_id?: string | null
  supplier_id: string
  supplier_name: string
  status: string
  invoice_date?: string | null
  due_date?: string | null
  subtotal: number
  tax_amount: number
  grand_total: number
  paid_amount: number
  balance_due: number
  notes?: string | null
  created_at?: string | null
}

export type SupplierInvoiceInput = {
  purchase_order_id?: string
  supplier_invoice_ref?: string
  invoice_date: string
  due_date: string
  subtotal: number
  tax_amount?: number
  grand_total: number
  notes?: string
}

export type SupplierPayment = {
  id: string
  payment_number: string
  supplier_invoice_id: string
  supplier_id: string
  amount: number
  payment_date?: string | null
  payment_method?: string | null
  reference_number?: string | null
  notes?: string | null
  created_at?: string | null
}

export type RFQLine = {
  id: string
  material_id: string
  quantity: number
  description?: string | null
}

export type RFQSupplierInvite = {
  id: string
  supplier_id: string
  status: "invited" | "responded" | "declined"
  quotation_id?: string | null
}

export type RFQSummary = {
  id: string
  rfq_number: string
  title?: string | null
  status: "draft" | "sent" | "closed" | "awarded"
  deadline?: string | null
  material_request_id?: string | null
  awarded_supplier_id?: string | null
  awarded_po_id?: string | null
  created_at: string
  supplier_invites: RFQSupplierInvite[]
  lines?: RFQLine[]
}

export type RFQDetail = RFQSummary & {
  lines: RFQLine[]
  notes?: string | null
  quotation_details: Record<
    string,
    { unit_price: number; quantity: number; valid_until?: string | null; status: string }
  >
}

export type RFQCreateInput = {
  title?: string
  material_request_id?: string
  deadline?: string
  notes?: string
  lines: { material_id: string; quantity: number; description?: string }[]
  supplier_ids: string[]
}

export type RFQAwardInput = {
  supplier_id: string
  lines: { material_id: string; quantity: number; unit_price: number }[]
  expected_delivery?: string
  notes?: string
}

export type SupplierPerformance = {
  supplier_id: string
  supplier_name: string
  supplier_code: string
  on_time_delivery_pct?: number | null
  quality_acceptance_pct?: number | null
  avg_lead_time_days?: number | null
  performance_rating?: number | null
  price_history: {
    material_id: string
    material_code: string
    material_name: string
    unit_price: number
    effective_from?: string | null
  }[]
}

export type InvoiceDispute = {
  id: string
  disputed_amount: number
  reason: string
  status: "open" | "approved" | "rejected"
  resolution_notes?: string | null
  resolved_at?: string | null
  created_at: string
}

