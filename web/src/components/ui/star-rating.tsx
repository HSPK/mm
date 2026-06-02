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
    return (
        <div className={cn("inline-flex items-center gap-0.5", className)}>
            {Array.from({ length: max }, (_, i) => {
                const filled = i < Math.floor(value)
                const half = !filled && i < value
                return (
                    <Star
                        key={i}
                        size={size}
                        className={cn(
                            "transition-colors",
                            filled ? "fill-yellow-400 text-yellow-400" : half ? "fill-yellow-400/50 text-yellow-400" : "text-muted-foreground/30",
                            interactive && "cursor-pointer hover:text-yellow-400",
                        )}
                        role={interactive ? "button" : undefined}
                        aria-label={interactive ? `Set rating to ${value === i + 1 ? 0 : i + 1}` : undefined}
                        tabIndex={interactive ? 0 : undefined}
                        onClick={interactive && onChange ? () => onChange(value === i + 1 ? 0 : i + 1) : undefined}
                        onKeyDown={interactive && onChange
                            ? (e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault()
                                    if (e.repeat) return
                                    onChange(value === i + 1 ? 0 : i + 1)
                                }
                            }
                            : undefined}
                    />
                )
            })}
        </div>
    )
}
