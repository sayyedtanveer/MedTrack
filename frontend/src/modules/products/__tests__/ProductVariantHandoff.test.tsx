import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { expect, it, vi } from "vitest"
import ProductDetailPage from "../pages/ProductDetailPage"
import ProductTemplateFormPage from "../pages/ProductTemplateFormPage"

const api = vi.hoisted(() => ({
  template: { id: "template-id", code: "SEMI", name: "Machined blank", attributes: [{ key: "COLOR", label: "Color", values: ["Blue", "Red"] }], is_active: true },
  createVariant: vi.fn().mockResolvedValue({ id: "new-variant" }),
  createTemplate: vi.fn().mockResolvedValue({ id: "template-id" }),
}))

vi.mock("@/hooks/usePermissions", () => ({ usePermissions: () => ({ hasRole: () => true }) }))
vi.mock("@/services/product.service", () => ({
  productService: {
    getTemplate: vi.fn().mockResolvedValue(api.template),
    getVariants: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getTemplateImages: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    createVariant: api.createVariant,
    createTemplate: api.createTemplate,
  },
}))
vi.mock("@/services/bom.service", () => ({ bomService: { getBOMsForProduct: vi.fn().mockResolvedValue({ items: [], total: 0 }) } }))
vi.mock("@/services/material.service", () => ({
  materialService: {
    getUnits: vi.fn().mockResolvedValue([]),
    getCategories: vi.fn().mockResolvedValue([{ id: "category-id", name: "Metal" }]),
    getMaterials: vi.fn().mockResolvedValue({
      items: [
        { id: "semi-id", code: "SF-001", name: "Machined blank", material_type: "semi_finished", is_active: true },
        { id: "finished-id", code: "FG-001", name: "Finished bracket", material_type: "finished", is_active: true },
        { id: "inactive-id", code: "SF-002", name: "Inactive blank", material_type: "semi_finished", is_active: false },
        { id: "raw-id", code: "RM-001", name: "Raw blank", material_type: "raw", is_active: true },
      ],
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
  expect(screen.getByRole("tab", { name: "Variants (0)" })).toHaveAttribute("aria-selected", "true")
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
  expect(screen.queryByText("Create New Variant")).not.toBeInTheDocument()
  fireEvent.click((await screen.findAllByRole("button", { name: "Create First Variant" }))[0])
  expect(await screen.findByText("Create New Variant")).toBeVisible()

  const color = screen.getByRole("combobox", { name: "Color" })
  fireEvent.keyDown(color, { key: "ArrowDown" })
  fireEvent.click(await screen.findByRole("option", { name: "Blue" }))
  expect(color).toHaveTextContent("Blue")
  fireEvent.keyDown(color, { key: "ArrowDown" })
  fireEvent.click(await screen.findByRole("option", { name: "Red" }))
  expect(color).toHaveTextContent("Red")

  const finished = screen.getByRole("combobox", { name: "Finished good inventory material" })
  expect(finished).toHaveTextContent("Auto-create a finished good")
  fireEvent.click(screen.getByRole("button", { name: "Semi-finished (subcontracting)" }))
  expect(screen.getByRole("button", { name: "Create" })).toBeDisabled()

  const inventory = screen.getByRole("combobox", { name: "Semi-finished item (required)" })
  expect(screen.getByRole("link", { name: /Add a semi-finished item in Materials/ })).toHaveAttribute("href", "/inventory/materials")
  expect(screen.getByText("Assigned automatically when you save")).toBeVisible()
  await waitFor(() => expect(inventory).toBeEnabled())
  fireEvent.keyDown(inventory, { key: "Enter" })
  const material = await screen.findByRole("option", { name: /SF-001/ })
  expect(screen.getAllByRole("option")).toHaveLength(1)
  fireEvent.keyDown(material, { key: "Enter" })
  fireEvent.click(screen.getByRole("button", { name: "Create" }))
  await waitFor(() => expect(api.createVariant).toHaveBeenCalledWith("template-id", expect.objectContaining({
    attribute_values: { COLOR: "Red" },
    material_id: "semi-id",
  })))
  await waitFor(() => expect(screen.queryByText("Create New Variant")).not.toBeInTheDocument())
})

it("opens the inline variant form after a new SFG template is saved", async () => {
  HTMLElement.prototype.scrollIntoView ??= vi.fn()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/products/new"]}>
        <Routes>
          <Route path="/products/new" element={<ProductTemplateFormPage />} />
          <Route path="/products/:id" element={<ProductDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
  fireEvent.change(screen.getByRole("textbox", { name: "Name" }), { target: { value: "Chair seat" } })
  fireEvent.keyDown(screen.getByRole("combobox", { name: "Product type" }), { key: "Enter" })
  fireEvent.click(await screen.findByRole("option", { name: "Semi-Finished Good (SFG)" }))
  fireEvent.keyDown(screen.getByRole("combobox", { name: "Category" }), { key: "Enter" })
  fireEvent.click(await screen.findByRole("option", { name: "Metal" }))
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(await screen.findByText("Create New Variant")).toBeVisible()
  expect(screen.getByRole("tab", { name: "Variants (0)" })).toHaveAttribute("aria-selected", "true")
  expect(api.createTemplate).toHaveBeenCalledWith(expect.objectContaining({
    category_id: "category-id",
    product_type: "semi_finished",
  }))
})

