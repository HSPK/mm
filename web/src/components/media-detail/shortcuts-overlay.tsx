import { useEffect } from "react"
import { Keyboard, X } from "lucide-react"

interface Shortcut {
    keys: string[]
    label: string
}

const shortcuts: Shortcut[] = [
    { keys: ["←", "→"], label: "Previous / Next" },
    { keys: ["Esc"], label: "Close" },
    { keys: ["?"], label: "Show this help" },
    { keys: ["Double-click"], label: "Toggle zoom" },
    { keys: ["Scroll"], label: "Zoom in / out" },
]

interface ShortcutsOverlayProps {
    open: boolean
    onClose: () => void
}

export function ShortcutsOverlay({ open, onClose }: ShortcutsOverlayProps) {
    useEffect(() => {
        if (!open) return
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose()
        }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
    }, [open, onClose])

    if (!open) return null

    return (
        <div
            className="absolute inset-0 z-30 flex items-center justify-center bg-black/60 p-6 backdrop-blur-sm"
            onClick={onClose}
            role="presentation"
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-label="Keyboard shortcuts"
                className="w-full max-w-xs rounded-2xl border border-white/10 bg-neutral-950/95 p-5 text-white shadow-2xl animate-[fade-in-up_180ms_ease-out]"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                        <Keyboard className="h-4 w-4 text-white/60" />
                        Shortcuts
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close shortcuts"
                        className="flex h-7 w-7 items-center justify-center rounded-full text-white/50 hover:bg-white/10 hover:text-white"
                    >
                        <X className="h-3.5 w-3.5" />
                    </button>
                </div>

                <ul className="space-y-2.5">
                    {shortcuts.map((s) => (
                        <li key={s.label} className="flex items-center justify-between gap-3">
                            <span className="text-sm text-white/70">{s.label}</span>
                            <span className="flex items-center gap-1">
                                {s.keys.map((k) => (
                                    <kbd
                                        key={k}
                                        className="rounded-md border border-white/15 bg-white/[0.06] px-2 py-0.5 text-[11px] font-mono text-white/85"
                                    >
                                        {k}
                                    </kbd>
                                ))}
                            </span>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    )
}