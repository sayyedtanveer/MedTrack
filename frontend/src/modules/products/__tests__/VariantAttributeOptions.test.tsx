import { useState } from "react"
import { fireEvent, render, screen } from "@testing-library/react"
import { expect, it, vi } from "vitest"
import { TagInput } from "@/components/ui/tag-input"

it("adds options by button or keyboard, rejects duplicates, and removes saved values", () => {
  const submit = vi.fn()
  function Form() {
    const [options, setOptions] = useState(["Blue"])
    return (
      <form onSubmit={submit}>
        <TagInput label="Color option" value={options} onChange={setOptions} />
      </form>
    )
  }
  render(<Form />)
  const input = screen.getByRole("textbox", { name: "Color option" })
  fireEvent.change(input, { target: { value: " Red " } })
  fireEvent.click(screen.getByRole("button", { name: "Add" }))
  expect(screen.getByRole("button", { name: "Remove Red" })).toBeVisible()
  fireEvent.change(input, { target: { value: "red" } })
  expect(fireEvent.keyDown(input, { key: "Enter" })).toBe(false)
  expect(screen.getByRole("alert")).toHaveTextContent("This option already exists.")
  fireEvent.change(input, { target: { value: "Green" } })
  fireEvent.keyDown(input, { key: "Enter" })
  expect(screen.getByRole("button", { name: "Remove Green" })).toBeVisible()
  fireEvent.click(screen.getByRole("button", { name: "Remove Blue" }))
  expect(screen.queryByRole("button", { name: "Remove Blue" })).toBeNull()
  expect(submit).not.toHaveBeenCalled()
})

