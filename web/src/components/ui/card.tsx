import { cn } from "@/lib/utils"
import type { HTMLAttributes, ReactNode } from "react"

/**
 * Apple-style surface — no heavy border, generous radius, soft elevation.
 * Mirrors the iOS / macOS grouped list section appearance.
 */
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn(
                "rounded-2xl bg-card text-card-foreground elevation-1 overflow-hidden",
                className,
            )}
            {...props}
        />
    )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return <div className={cn("flex flex-col space-y-1 p-5", className)} {...props} />
}

export function CardTitle({ className, children }: { className?: string; children: ReactNode }) {
    return (
        <h3 className={cn("text-[17px] font-semibold leading-tight tracking-tight", className)}>
            {children}
        </h3>
    )
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return <div className={cn("p-5 pt-0", className)} {...props} />
}
