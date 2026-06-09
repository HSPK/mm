import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { TrashActionBar } from "./trash-action-bar"

describe("TrashActionBar", () => {
    it("shows the count and wires the 4 action buttons", () => {
        const handlers = {
            onBack: vi.fn(),
            onSelectAll: vi.fn(),
            onRestoreAll: vi.fn(),
            onEmpty: vi.fn(),
        }
        render(
            <TrashActionBar total={42} {...handlers} />,
        )
        expect(screen.getByText("42")).toBeInTheDocument()
        fireEvent.click(screen.getByRole("button", { name: /Back/i }))
        fireEvent.click(screen.getByRole("button", { name: /All/i }))
        fireEvent.click(screen.getByRole("button", { name: /Restore/i }))
        fireEvent.click(screen.getByRole("button", { name: /Empty/i }))
        expect(handlers.onBack).toHaveBeenCalledOnce()
        expect(handlers.onSelectAll).toHaveBeenCalledOnce()
        expect(handlers.onRestoreAll).toHaveBeenCalledOnce()
        expect(handlers.onEmpty).toHaveBeenCalledOnce()
    })
})

import { SelectionActionBar } from "./selection-action-bar"

describe("SelectionActionBar", () => {
    it("shows Restore + Delete when in trash, Album + Delete otherwise", () => {
        const props = {
            selectedCount: 5,
            albumPickerOpen: false,
            onCancel: vi.fn(),
            onSelectAll: vi.fn(),
            onToggleAlbumPicker: vi.fn(),
            onDelete: vi.fn(),
            onRestore: vi.fn(),
        }
        const { rerender } = render(<SelectionActionBar inTrash {...props} />)
        expect(screen.getByRole("button", { name: /Restore/i })).toBeInTheDocument()
        expect(screen.queryByRole("button", { name: /Album/i })).not.toBeInTheDocument()

        rerender(<SelectionActionBar inTrash={false} {...props} />)
        expect(screen.getByRole("button", { name: /Album/i })).toBeInTheDocument()
        expect(screen.queryByRole("button", { name: /Restore/i })).not.toBeInTheDocument()
    })

    it("calls handlers on click", () => {
        const onDelete = vi.fn()
        const onCancel = vi.fn()
        render(
            <SelectionActionBar
                selectedCount={2}
                inTrash={false}
                albumPickerOpen={false}
                onCancel={onCancel}
                onSelectAll={vi.fn()}
                onToggleAlbumPicker={vi.fn()}
                onDelete={onDelete}
                onRestore={vi.fn()}
            />,
        )
        fireEvent.click(screen.getByRole("button", { name: /Delete/i }))
        expect(onDelete).toHaveBeenCalledOnce()
        fireEvent.click(screen.getByRole("button", { name: /Cancel/i }))
        expect(onCancel).toHaveBeenCalledOnce()
    })
})
