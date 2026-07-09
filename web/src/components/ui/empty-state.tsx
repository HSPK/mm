import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
    icon?: LucideIcon
    title: string
    description?: string
    action?: { label: string; onClick: () => void; variant?: "primary" | "secondary" }
    className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
    return (
        <div className={cn("flex min-h-[18rem] flex-col items-center justify-center px-6 py-16 text-center", className)}>
            {Icon && (
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-muted/40">
                    <Icon className="h-7 w-7 text-muted-foreground/50" aria-hidden />
                </div>
            )}
            <h3 className="mb-1 text-base font-semibold text-foreground/90">{title}</h3>
            {description && (
                <p className="mb-5 max-w-xs text-sm leading-6 text-muted-foreground/70">{description}</p>
            )}
            {action && (
                <button
                    type="button"
                    onClick={action.onClick}
                    className={cn(
                        "h-9 px-4 rounded-full text-xs font-semibold transition-colors",
                        action.variant === "primary"
                            ? "bg-primary text-primary-foreground hover:bg-primary/90"
                            : "bg-secondary text-foreground/80 hover:bg-secondary/80",
                    )}
                >
                    {action.label}
                </button>
            )}
        </div>
    )
}
