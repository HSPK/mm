import { AlertCircle, CheckCircle2, Info, X } from "lucide-react"
import { createPortal } from "react-dom"
import { useToastStore, type ToastVariant } from "@/stores/toast"
import { cn } from "@/lib/utils"

const variantStyles: Record<ToastVariant, string> = {
    default: "bg-popover/95 text-foreground border-border",
    success: "bg-emerald-500/15 text-emerald-200 border-emerald-500/30",
    error: "bg-destructive/15 text-destructive border-destructive/30",
}

const variantIcons: Record<ToastVariant, typeof Info> = {
    default: Info,
    success: CheckCircle2,
    error: AlertCircle,
}

/**
 * Mount once near the app root. Renders all queued toasts in a portal at the
 * bottom of the screen, above the safe-area inset.
 */
export function ToastViewport() {
    const toasts = useToastStore((s) => s.toasts)
    const dismiss = useToastStore((s) => s.dismiss)

    if (typeof document === "undefined") return null
    if (toasts.length === 0) return null

    return createPortal(
        <div
            role="region"
            aria-label="Notifications"
            className="pointer-events-none fixed left-0 right-0 z-[10010] flex flex-col items-center gap-2 px-4"
            style={{ bottom: "max(env(safe-area-inset-bottom, 0px), 1rem)" }}
        >
            {toasts.map((t) => {
                const Icon = variantIcons[t.variant]
                return (
                    <div
                        key={t.id}
                        role={t.variant === "error" ? "alert" : "status"}
                        className={cn(
                            "pointer-events-auto flex max-w-sm items-start gap-2.5 rounded-full border px-4 py-2.5 text-sm font-medium shadow-2xl backdrop-blur-xl",
                            "animate-[toast-in_200ms_cubic-bezier(0.16,1,0.3,1)]",
                            variantStyles[t.variant],
                        )}
                    >
                        <Icon className="h-4 w-4 shrink-0 mt-px" aria-hidden />
                        <span className="flex-1">{t.message}</span>
                        <button
                            type="button"
                            aria-label="Dismiss"
                            onClick={() => dismiss(t.id)}
                            className="-mr-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-current/70 hover:bg-white/10 hover:text-current transition-colors"
                        >
                            <X className="h-3 w-3" />
                        </button>
                    </div>
                )
            })}
        </div>,
        document.body,
    )
}
