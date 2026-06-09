import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface SpinnerProps {
    size?: "sm" | "md" | "lg"
    className?: string
    label?: string
}

const sizeClass: Record<NonNullable<SpinnerProps["size"]>, string> = {
    sm: "h-3.5 w-3.5",
    md: "h-5 w-5",
    lg: "h-7 w-7",
}

/** Inline loading indicator. Use `label` to announce loading to screen readers. */
export function Spinner({ size = "md", className, label = "Loading" }: SpinnerProps) {
    return (
        <Loader2
            role="status"
            aria-label={label}
            className={cn("animate-spin", sizeClass[size], className)}
        />
    )
}
