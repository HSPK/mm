import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "react"

/**
 * Shimmer placeholder. Defaults to a neutral block; pass `className` for
 * dimensions/shape. Animation honors `prefers-reduced-motion`.
 */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            aria-hidden
            className={cn(
                "relative overflow-hidden bg-muted/60 rounded-md",
                "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.5s_infinite]",
                "before:bg-gradient-to-r before:from-transparent before:via-white/[0.06] before:to-transparent",
                "motion-reduce:before:animate-none",
                className,
            )}
            {...props}
        />
    )
}
