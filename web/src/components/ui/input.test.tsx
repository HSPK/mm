import { fireEvent, render, screen } from "@testing-library/react"
import { Search } from "lucide-react"
import { describe, expect, it, vi } from "vitest"
import { Input } from "./input"

describe("Input", () => {
    it("renders bare input when no label/error", () => {
        render(<Input placeholder="Type here" />)
        expect(screen.getByPlaceholderText("Type here")).toBeInTheDocument()
        expect(screen.queryByText("Username")).not.toBeInTheDocument()
    })

    it("wires a label to the input", () => {
        render(<Input label="Username" placeholder="u" />)
        const input = screen.getByLabelText("Username")
        expect(input).toBeInTheDocument()
        expect(input.tagName).toBe("INPUT")
    })

    it("shows an error message + aria-invalid + describedby", () => {
        render(<Input label="Password" error="Too short" />)
        const input = screen.getByLabelText("Password")
        expect(input.getAttribute("aria-invalid")).toBe("true")
        const errorText = screen.getByText("Too short")
        expect(input.getAttribute("aria-describedby")).toBe(errorText.id)
    })

    it("renders left and right icons", () => {
        render(<Input leftIcon={<Search data-testid="left" />} rightIcon={<span data-testid="right">x</span>} />)
        expect(screen.getByTestId("left")).toBeInTheDocument()
        expect(screen.getByTestId("right")).toBeInTheDocument()
    })

    it("forwards onChange", () => {
        const onChange = vi.fn()
        render(<Input onChange={onChange} />)
        fireEvent.change(screen.getByRole("textbox"), { target: { value: "abc" } })
        expect(onChange).toHaveBeenCalledOnce()
    })
})
