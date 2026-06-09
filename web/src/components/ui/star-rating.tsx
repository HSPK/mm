import { useState } from "react"
import { Star } from "lucide-react"
import { cn } from "@/lib/utils"

interface StarRatingProps {
    value: number
    max?: number
    size?: number
    className?: string
    interactive?: boolean
    onChange?: (value: number) => void
}

export function StarRating({
    value,
    max = 5,
    size = 16,
    className,
    interactive = false,
    onChange,
}: StarRatingProps) {
    const [hover, setHover] = useState<number | null>(null)
    const display = interactive && hover != null ? hover : value

    return (
        <div
            className={cn("inline-flex items-center gap-0.5", className)}
            onMouseLeave={interactive ? () => setHover(null) : undefined}
            role={interactive ? "radiogroup" : "img"}
            aria-label={interactive ? "Rating" : `Rated ${value} out of ${max}`}
        >
            {Array.from({ length: max }, (_, i) => {
                const target = i + 1
                const filled = i < Math.floor(display)
                const half = !filled && i < display
                const toggleTo = value === target ? 0 : target
                return (
                    <Star
                        key={i}
                        size={size}
                        className={cn(
                            "transition-colors",
                            filled
                                ? "fill-yellow-400 text-yellow-400"
                                : half
                                    ? "fill-yellow-400/50 text-yellow-400"
                                    : "text-muted-foreground/30",
                            interactive && "cursor-pointer hover:text-yellow-400",
                        )}
                        role={interactive ? "radio" : undefined}
                        aria-checked={interactive ? value === target : undefined}
                        aria-label={interactive ? `Rate ${target} star${target === 1 ? "" : "s"}` : undefined}
                        tabIndex={interactive ? 0 : undefined}
                        onClick={interactive && onChange ? () => onChange(toggleTo) : undefined}
                        onMouseEnter={interactive ? () => setHover(target) : undefined}
                        onFocus={interactive ? () => setHover(target) : undefined}
                        onBlur={interactive ? () => setHover(null) : undefined}
                        onKeyDown={interactive && onChange
                            ? (e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault()
                                    if (e.repeat) return
                                    onChange(toggleTo)
                                }
                            }
                            : undefined}
                    />
                )
            })}
        </div>
    )
}
