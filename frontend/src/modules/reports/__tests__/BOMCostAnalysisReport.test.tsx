import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, expect, it, vi } from "vitest"
import { BOMCostAnalysisReport } from "../pages/BOMCostAnalysisReport"

vi.mock("@/hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true }) }))
vi.mock("@/services/product.service", () => ({
  productService: {
    getTemplates: async () => ({ items: [{ id: "product", code: "FG", name: "Assembly" }], total: 1 }),
    getVariants: async () => ({ items: [], total: 0 }),
  },
}))
vi.mock("@/services/bom.service", () => ({
  bomService: { getBOMsForProduct: async () => ({ items: [{ id: "bom", version: "v1", is_active: true }], total: 1 }) },
}))
const api = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock("@/services/api-client", () => ({ apiClient: api }))

afterEach(() => { cleanup(); vi.clearAllMocks() })

it.each([true, false])("renders BOM cost state and expand controls on the responsive report (complete=%s)", async (complete) => {
  api.get.mockResolvedValue({ data: {
    bom_id: "bom", version: "v1", is_active: true, target_name: "Assembly", output_quantity: 1,
    output_uom: "KG", generated_at: "2026-11-17T00:00:00Z", currency_code: "INR",
    total_cost: complete ? "1252.00" : null, direct_material_cost: complete ? "12" : null,
    nested_cost: complete ? "1200" : null, own_operation_cost: "0", own_outside_processing_cost: "40",
    composition: complete ? { material: "1212", operations: "0", outside_processing: "40" } : null,
    is_complete: complete, missing_costs: complete ? [] : [{ component_id: "raw", name: "Raw", message: "Standard Cost missing" }],
    tree: { id: "bom", name: "Assembly", type: "template", quantity: "1", cost: complete ? "1252" : null,
      children: [{ id: "raw", name: "Raw", type: "material", quantity: "1", unit: "KG", cost: null, children: [] }] },
  } })
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><BOMCostAnalysisReport /></MemoryRouter></QueryClientProvider>)
  await screen.findByRole("option", { name: /FG/ })
  fireEvent.change(screen.getByLabelText(/^Product/), { target: { value: "product" } })
  await screen.findByRole("option", { name: /v1/ })
  fireEvent.change(screen.getByLabelText(/^BOM version/), { target: { value: "bom" } })
  expect(await screen.findByRole("link", { name: "Open BOM" })).toHaveAttribute("href", "/bom/bom")
  expect(screen.getByRole("button", { name: "Export Excel" })).toBeEnabled()
  expect(screen.getByText("Calculated BOM Cost").closest(".grid")).toHaveClass("grid-cols-1", "sm:grid-cols-2")
  if (complete) expect(screen.getByText("Reconciled Cost Composition")).toBeInTheDocument()
  else {
    expect(screen.getByRole("alert")).toHaveTextContent("Standard Cost missing")
    expect(screen.queryByText("Reconciled Cost Composition")).not.toBeInTheDocument()
  }
})
