import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ActiveFilterTags } from "./active-filter-tags"

describe("ActiveFilterTags", () => {
    it("returns null when there are no tags", () => {
        const { container } = render(<ActiveFilterTags tags={[]} />)
        expect(container.firstChild).toBeNull()
    })

    it("renders labels and skips remove button for non-removable tags", () => {
        render(
            <ActiveFilterTags
                tags={[
                    { key: "a", label: "Locked", removable: false, onRemove: () => { } },
                    { key: "b", label: "Removable", removable: true, onRemove: () => { } },
                ]}
            />,
        )
        expect(screen.getByText("Locked")).toBeInTheDocument()
        expect(screen.getByText("Removable")).toBeInTheDocument()
        expect(screen.getAllByRole("button")).toHaveLength(1)
    })

    it("calls onRemove when the chip x is clicked", () => {
        const onRemove = vi.fn()
        render(
            <ActiveFilterTags
                tags={[{ key: "a", label: "Photos", removable: true, onRemove }]}
            />,
        )
        fireEvent.click(screen.getByRole("button"))
        expect(onRemove).toHaveBeenCalledOnce()
    })

    it("applies a color class for each color variant", () => {
        const { container } = render(
            <ActiveFilterTags
                tags={[
                    { key: "a", label: "Red", color: "destructive", removable: false, onRemove: () => { } },
                    { key: "b", label: "Yellow", color: "amber", removable: false, onRemove: () => { } },
                ]}
            />,
        )
        const chips = container.querySelectorAll(":scope > div > span")
        expect(chips[0]?.className).toContain("destructive")
        expect(chips[1]?.className).toContain("amber")
    })
})
