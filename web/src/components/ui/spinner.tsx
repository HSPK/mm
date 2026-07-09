import { cn } from "@/lib/utils"

interface SpinnerProps {
    size?: "sm" | "md" | "lg"
    className?: string
    label?: string
}

const sizeClass: Record<NonNullable<SpinnerProps["size"]>, string> = {
    sm: "h-4 gap-1",
    md: "h-5 gap-1.5",
    lg: "h-7 gap-2",
}

const dotClass: Record<NonNullable<SpinnerProps["size"]>, string> = {
    sm: "h-1.5 w-1.5",
    md: "h-2 w-2",
    lg: "h-2.5 w-2.5",
}

/** Inline loading indicator. Use `label` to announce loading to screen readers. */
export function Spinner({ size = "md", className, label = "Loading" }: SpinnerProps) {
    return (
        <span
            role="status"
            aria-label={label}
            className={cn("inline-flex shrink-0 items-center justify-center align-middle leading-none", sizeClass[size], className)}
        >
            {[0, 1, 2].map((index) => (
                <span
                    key={index}
                    className={cn(
                        "rounded-full bg-current opacity-40 animate-[mm-loading-dot_1.05s_ease-in-out_infinite]",
                        dotClass[size],
                    )}
                    style={{ animationDelay: `${index * 0.14}s` }}
                />
            ))}
        </span>
    )
}
