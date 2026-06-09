import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { DeleteConfirmDialog } from "./delete-confirm-dialog"

describe("DeleteConfirmDialog", () => {
    it("renders nothing when closed", () => {
        const { container } = render(
            <DeleteConfirmDialog
                open={false}
                filename="a.jpg"
                inTrash={false}
                deleting={false}
                onCancel={() => { }}
                onConfirm={() => { }}
            />,
        )
        expect(container.firstChild).toBeNull()
    })

    it("shows trash copy when inTrash", () => {
        render(
            <DeleteConfirmDialog
                open
                filename="a.jpg"
                inTrash
                deleting={false}
                onCancel={() => { }}
                onConfirm={() => { }}
            />,
        )
        expect(screen.getByText("Delete permanently?")).toBeInTheDocument()
        expect(screen.getByText("a.jpg")).toBeInTheDocument()
        expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument()
    })

    it("shows non-trash copy when !inTrash", () => {
        render(
            <DeleteConfirmDialog
                open
                filename="a.jpg"
                inTrash={false}
                deleting={false}
                onCancel={() => { }}
                onConfirm={() => { }}
            />,
        )
        expect(screen.getByText("Move to trash?")).toBeInTheDocument()
        expect(screen.getByRole("button", { name: "Move" })).toBeInTheDocument()
    })

    it("Cancel triggers onCancel, Confirm triggers onConfirm", () => {
        const onCancel = vi.fn()
        const onConfirm = vi.fn()
        render(
            <DeleteConfirmDialog
                open
                filename="a.jpg"
                inTrash
                deleting={false}
                onCancel={onCancel}
                onConfirm={onConfirm}
            />,
        )
        fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
        expect(onCancel).toHaveBeenCalledOnce()
        fireEvent.click(screen.getByRole("button", { name: "Delete" }))
        expect(onConfirm).toHaveBeenCalledOnce()
    })

    it("buttons are disabled while deleting", () => {
        render(
            <DeleteConfirmDialog
                open
                filename="a.jpg"
                inTrash={false}
                deleting
                onCancel={() => { }}
                onConfirm={() => { }}
            />,
        )
        const buttons = screen.getAllByRole("button")
        // Cancel + Confirm (which now shows just a spinner via loading prop)
        expect(buttons.length).toBe(2)
        for (const b of buttons) expect(b).toBeDisabled()
    })
})
