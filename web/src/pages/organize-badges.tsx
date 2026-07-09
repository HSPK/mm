import { Star, X, type LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { StatusValue } from "./organize-model"

export function IconHeader({ icon: Icon, label }: { icon: LucideIcon, label: string }) {
    return (
        <span title={label} aria-label={label} className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-background/70">
            <Icon className="h-3 w-3" />
        </span>
    )
}

export function NewBadge() {
    return (
        <span className="shrink-0 rounded-full bg-amber-500/18 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-amber-600 dark:text-amber-300">
            New
        </span>
    )
}

export function RatingIndicator({ rating }: { rating: number | null }) {
    return (
        <span
            title={rating == null ? "No metadata rating" : `Rating ${rating.toFixed(1)}`}
            className={cn(
                "inline-flex h-6 min-w-6 items-center justify-center gap-1 rounded-full px-1.5 text-[11px] font-semibold tabular-nums",
                rating == null ? "bg-secondary/60 text-muted-foreground/60" : "bg-amber-500/12 text-amber-600 dark:text-amber-300",
            )}
        >
            <Star className="h-3 w-3" />
            {rating != null && rating.toFixed(1)}
        </span>
    )
}

export function RatingSourceBadge({ source, compact }: { source: string, compact?: boolean }) {
    const normalized = source.toLowerCase()
    return (
        <span className={cn(
            "inline-flex items-center justify-center rounded-md font-black tracking-tight",
            compact ? "h-4 min-w-7 px-1 text-[8px]" : "h-7 min-w-14 px-2 text-xs",
            normalized.includes("imdb") && "bg-[#f5c518] text-black",
            (normalized.includes("tmdb") || normalized.includes("themoviedb")) && "bg-[#032541] text-[#90cea1]",
            normalized.includes("tvdb") && "bg-[#f97316] text-white",
            !normalized && "bg-secondary text-muted-foreground",
            normalized
                && !normalized.includes("imdb")
                && !normalized.includes("tmdb")
                && !normalized.includes("themoviedb")
                && !normalized.includes("tvdb")
                && "bg-primary/15 text-primary",
        )}>
            {ratingSourceShortLabel(source)}
        </span>
    )
}

export function IconStatus({
    icon: Icon,
    value,
    label,
}: {
    icon: LucideIcon
    value: StatusValue
    label: string
}) {
    const text = value === "na" ? "N/A" : value === "partial" ? "Partial" : value === "yes" ? "Yes" : "No"
    return (
        <span
            title={`${label}: ${text}`}
            aria-label={`${label}: ${text}`}
            className={cn(
                "inline-flex h-6 w-6 items-center justify-center rounded-full",
                value === "yes" && "bg-primary/10 text-primary",
                value === "partial" && "bg-amber-500/12 text-amber-600 dark:text-amber-300",
                value === "no" && "bg-secondary/60 text-muted-foreground/60",
                value === "na" && "bg-secondary/40 text-muted-foreground/35",
            )}
        >
            {value === "no" ? <X className="h-3 w-3" /> : <Icon className="h-3 w-3" />}
        </span>
    )
}

function ratingSourceShortLabel(source: string) {
    const normalized = source.toLowerCase()
    if (normalized.includes("imdb")) return "IMDb"
    if (normalized.includes("tmdb") || normalized.includes("themoviedb")) return "TMDb"
    if (normalized.includes("tvdb")) return "TVDb"
    if (normalized.includes("trakt")) return "Trakt"
    if (normalized.includes("metacritic")) return "META"
    if (normalized.includes("rotten")) return "RT"
    if (normalized.includes("user")) return "USER"
    if (normalized.includes("nfo")) return "NFO"
    return source ? source.slice(0, 5).toUpperCase() : "N/A"
}
