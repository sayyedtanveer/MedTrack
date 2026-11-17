import { fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import RegisterTenantPage from "../pages/RegisterTenantPage"

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ register: vi.fn(), isRegistering: false }),
}))

describe("Workspace registration slug", () => {
  it("updates the displayed value while typing and preserves a manual slug", () => {
    render(<MemoryRouter><RegisterTenantPage /></MemoryRouter>)
    const company = screen.getByLabelText("Company/Tenant Name")
    const slug = screen.getByLabelText("Workspace URL (Slug)")

    fireEvent.change(company, { target: { value: "MédTrack" } })
    expect(slug).toHaveValue("medtrack")
    fireEvent.change(company, { target: { value: "MédTrack Engineering" } })
    expect(slug).toHaveValue("medtrack-engineering")

    fireEvent.change(slug, { target: { value: "custom-workspace" } })
    fireEvent.change(company, { target: { value: "MedTrack Fabrication" } })
    expect(slug).toHaveValue("custom-workspace")

    fireEvent.change(slug, { target: { value: "" } })
    fireEvent.change(company, { target: { value: "MedTrack Works" } })
    expect(slug).toHaveValue("medtrack-works")
    fireEvent.change(company, { target: { value: "" } })
    expect(slug).toHaveValue("")
  })
})

