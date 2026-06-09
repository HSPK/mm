import { useEffect, useRef } from "react"

interface DiscardChangesDialogProps {
    open: boolean
    onKeepEditing: () => void
    onDiscard: () => void
}

export function DiscardChangesDialog({ open, onKeepEditing, onDiscard }: DiscardChangesDialogProps) {
    const keepRef = useRef<HTMLButtonElement>(null)

    useEffect(() => {
        if (!open) return
        const frame = window.requestAnimationFrame(() => keepRef.current?.focus())
        return () => window.cancelAnimationFrame(frame)
    }, [open])

    if (!open) return null

    return (
        <div
            className="absolute inset-0 z-10 flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm"
            role="presentation"
            onClick={(e) => e.stopPropagation()}
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-label="Discard unsaved changes"
                tabIndex={-1}
                className="w-full max-w-[340px] rounded-2xl border border-white/10 bg-neutral-950/95 p-5 text-white shadow-2xl"
            >
                <div className="mb-2 text-sm font-semibold">Discard unsaved edits?</div>
                <p className="mb-5 text-sm leading-relaxed text-white/55">
                    Your metadata changes have not been saved.
                </p>
                <div className="flex justify-end gap-2">
                    <button
                        ref={keepRef}
                        type="button"
                        className="rounded-full px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
                        onClick={onKeepEditing}
                    >
                        Keep editing
                    </button>
                    <button
                        type="button"
                        className="rounded-full bg-red-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-400"
                        onClick={onDiscard}
                    >
                        Discard
                    </button>
                </div>
            </div>
        </div>
    )
}
