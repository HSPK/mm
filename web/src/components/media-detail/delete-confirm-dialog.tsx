import { Trash2 } from "lucide-react"
import { useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"

interface DeleteConfirmDialogProps {
    open: boolean
    filename: string
    inTrash: boolean
    deleting: boolean
    onCancel: () => void
    onConfirm: () => void
}

export function DeleteConfirmDialog({
    open,
    filename,
    inTrash,
    deleting,
    onCancel,
    onConfirm,
}: DeleteConfirmDialogProps) {
    const cancelRef = useRef<HTMLButtonElement>(null)

    useEffect(() => {
        if (!open) return
        const frame = window.requestAnimationFrame(() => cancelRef.current?.focus())
        return () => window.cancelAnimationFrame(frame)
    }, [open])

    if (!open) return null

    return (
        <div
            className="absolute inset-0 z-40 flex items-center justify-center bg-black/60 p-6 backdrop-blur-sm"
            role="presentation"
            onClick={onCancel}
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-label="Confirm delete"
                tabIndex={-1}
                className="w-full max-w-sm rounded-2xl border border-white/10 bg-neutral-950/95 p-5 text-white shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="mb-1 flex items-center gap-2 text-sm font-semibold">
                    <Trash2 className="h-4 w-4 text-red-300" />
                    {inTrash ? "Delete permanently?" : "Move to trash?"}
                </div>
                <p className="mb-5 break-words text-sm text-white/60">
                    {filename}
                    {inTrash && (
                        <span className="mt-2 block text-xs text-red-200/70">
                            This cannot be undone.
                        </span>
                    )}
                </p>
                <div className="flex justify-end gap-2">
                    <button
                        ref={cancelRef}
                        type="button"
                        className="rounded-full px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
                        onClick={onCancel}
                        disabled={deleting}
                    >
                        Cancel
                    </button>
                    <Button
                        type="button"
                        variant="destructive"
                        className="rounded-full px-4 py-2"
                        onClick={onConfirm}
                        loading={deleting}
                    >
                        {deleting ? "" : inTrash ? "Delete" : "Move"}
                    </Button>
                </div>
            </div>
        </div>
    )
}
