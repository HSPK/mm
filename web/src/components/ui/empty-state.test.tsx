import { fireEvent, render, screen } from "@testing-library/react"
import { ImageOff } from "lucide-react"
import { describe, expect, it, vi } from "vitest"
import { EmptyState } from "./empty-state"

describe("EmptyState", () => {
    it("renders the title", () => {
        render(<EmptyState title="Nothing here" />)
        expect(screen.getByRole("heading", { name: "Nothing here" })).toBeInTheDocument()
    })

    it("renders description + icon when provided", () => {
        render(<EmptyState icon={ImageOff} title="Empty" description="Try a different filter" />)
        expect(screen.getByText("Try a different filter")).toBeInTheDocument()
    })

    it("renders an action button and triggers onClick", () => {
        const onClick = vi.fn()
        render(
            <EmptyState
                title="Empty"
                action={{ label: "Clear", onClick }}
            />,
        )
        fireEvent.click(screen.getByRole("button", { name: "Clear" }))
        expect(onClick).toHaveBeenCalledOnce()
    })

    it("does not render the action button when omitted", () => {
        render(<EmptyState title="Empty" />)
        expect(screen.queryByRole("button")).not.toBeInTheDocument()
    })
})
