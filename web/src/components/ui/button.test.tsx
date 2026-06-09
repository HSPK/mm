import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { Button } from "./button"

describe("Button", () => {
    it("renders children", () => {
        render(<Button>Click me</Button>)
        expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument()
    })

    it("disables itself when `disabled` is true", () => {
        render(<Button disabled>Click me</Button>)
        expect(screen.getByRole("button")).toBeDisabled()
    })

    it("disables itself + sets aria-busy when `loading`", () => {
        render(<Button loading>Submit</Button>)
        const btn = screen.getByRole("button", { name: /Submit/ })
        expect(btn).toBeDisabled()
        expect(btn.getAttribute("aria-busy")).toBe("true")
    })

    it("renders a spinner before children when loading", () => {
        render(<Button loading>Loading</Button>)
        const btn = screen.getByRole("button", { name: /Loading/ })
        const spinner = btn.querySelector("svg")
        expect(spinner?.classList.contains("animate-spin")).toBe(true)
    })

    it("calls onClick when not loading", () => {
        const handler = vi.fn()
        render(<Button onClick={handler}>Go</Button>)
        fireEvent.click(screen.getByRole("button"))
        expect(handler).toHaveBeenCalledOnce()
    })

    it("does not call onClick when loading", () => {
        const handler = vi.fn()
        render(<Button loading onClick={handler}>Go</Button>)
        fireEvent.click(screen.getByRole("button"))
        expect(handler).not.toHaveBeenCalled()
    })
})
