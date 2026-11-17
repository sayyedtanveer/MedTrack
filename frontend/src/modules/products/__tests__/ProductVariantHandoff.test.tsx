import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { expect, it, vi } from "vitest"
import ProductDetailPage from "../pages/ProductDetailPage"
import ProductTemplateFormPage from "../pages/ProductTemplateFormPage"

const api = vi.hoisted(() => ({
  template: { id: "template-id", code: "SEMI", name: "Machined blank", attributes: [{ key: "COLOR", label: "Color", values: ["Blue", "Red"] }], is_active: true },
  createVariant: vi.fn().mockResolvedValue({ id: "new-variant" }),
}))

vi.mock("@/hooks/usePermissions", () => ({ usePermissions: () => ({ hasRole: () => true }) }))
vi.mock("@/services/product.service", () => ({
  productService: {
    getTemplate: vi.fn().mockResolvedValue(api.template),
    getVariants: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getTemplateImages: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    createVariant: api.createVariant,
  },
}))
vi.mock("@/services/bom.service", () => ({ bomService: { getBOMsForProduct: vi.fn().mockResolvedValue({ items: [], total: 0 }) } }))
vi.mock("@/services/material.service", () => ({
  materialService: {
    getUnits: vi.fn().mockResolvedValue([]),
    getCategories: vi.fn().mockResolvedValue([]),
    getMaterials: vi.fn().mockResolvedValue({
      items: [{ id: "semi-id", code: "SF-001", name: "Machined blank", material_type: "semi_finished" }],
    }),
  },
}))

it("opens the first variant form directly and saves the selected semi-finished inventory link", async () => {
  HTMLElement.prototype.scrollIntoView ??= vi.fn()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/products/template-id?tab=variants"]}>
        <Routes>
          <Route path="/products/:id" element={<ProductDetailPage />} />
          <Route path="/products/:id/edit" element={<ProductTemplateFormPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
  const buttons = await screen.findAllByRole("button", { name: "Create First Variant" })
  expect(api.createVariant).not.toHaveBeenCalled()
  fireEvent.click(buttons[0])
  expect(await screen.findByText("Create New Variant")).toBeVisible()
  expect(screen.queryByText("Basic Information")).not.toBeInTheDocument()

  const color = screen.getByRole("combobox", { name: "Color" })
  fireEvent.keyDown(color, { key: "ArrowDown" })
  fireEvent.click(await screen.findByRole("option", { name: "Blue" }))
  expect(color).toHaveTextContent("Blue")
  fireEvent.keyDown(color, { key: "ArrowDown" })
  fireEvent.click(await screen.findByRole("option", { name: "Red" }))
  expect(color).toHaveTextContent("Red")

  const inventory = screen.getByRole("combobox", { name: "Link to Existing Material (Optional)" })
  fireEvent.keyDown(inventory, { key: "Enter" })
  const material = await screen.findByRole("option", { name: /SF-001/ })
  fireEvent.keyDown(material, { key: "Enter" })
  fireEvent.click(screen.getByRole("button", { name: "Create" }))
  await waitFor(() => expect(api.createVariant).toHaveBeenCalledWith("template-id", expect.objectContaining({
    attribute_values: { COLOR: "Red" },
    material_id: "semi-id",
  })))
})

