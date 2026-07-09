import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function PlayerButton({
    children,
    label,
    onClick,
    disabled,
    primary,
    active,
    large,
    small,
    className,
}: {
    children: ReactNode
    label: string
    onClick: () => void
    disabled?: boolean
    primary?: boolean
    active?: boolean
    large?: boolean
    small?: boolean
    className?: string
}) {
    const sizeClass = large
        ? primary ? "flex h-16 w-16" : "flex h-12 w-12"
        : primary ? "flex h-10 w-10" : small ? "flex h-9 w-9" : "flex h-10 w-10"
    return (
        <button
            type="button"
            aria-label={label}
            title={label}
            disabled={disabled}
            onClick={onClick}
            className={cn(
                "shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40",
                sizeClass,
                className,
                primary
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                    : active
                        ? "bg-primary/15 text-primary hover:bg-primary/20"
                        : "bg-secondary/70 text-muted-foreground hover:bg-secondary hover:text-foreground",
            )}
        >
            {children}
        </button>
    )
}
