import {
    ArrowDownWideNarrow,
    ArrowUpWideNarrow,
    Calendar,
    CalendarDays,
    Camera,
    ChevronDown,
    Film,
    HardDrive,
    Image,
    LayoutGrid,
    MapPin,
    Minus,
    Plus,
    Star,
    StretchHorizontal,
    X,
} from "lucide-react"
import { useCameras } from "@/hooks/use-cameras"
import { config } from "@/lib/config"
import type { DateGroupMode, ViewMode } from "@/stores/view-prefs"
import { useViewPrefsStore } from "@/stores/view-prefs"
import { useMediaQueryStore } from "@/stores/media-query"
import type { SortKey, SortOrder } from "@/lib/filter-types"
import { StarRating } from "@/components/ui/star-rating"
import { cn } from "@/lib/utils"

const typeTabs = [
    { key: "", label: "All", icon: LayoutGrid },
    { key: "photo", label: "Photos", icon: Image },
    { key: "video", label: "Videos", icon: Film },
] as const

const sortTabs = [
    { key: "date_taken:desc", label: "Newest", icon: ArrowDownWideNarrow },
    { key: "date_taken:asc", label: "Oldest", icon: ArrowUpWideNarrow },
    { key: "rating:desc", label: "Top Rated", icon: Star },
    { key: "size:desc", label: "Largest", icon: HardDrive },
] as const

const groupTabs = [
    { key: "month", label: "Month", icon: Calendar },
    { key: "day", label: "Day", icon: CalendarDays },
] as const

const viewTabs = [
    { key: "justified", label: "Justified", icon: StretchHorizontal },
    { key: "grid", label: "Grid", icon: LayoutGrid },
] as const

interface FilterMenuProps {
    showFilters: boolean
}

export function FilterMenu({ showFilters }: FilterMenuProps) {
    const cameras = useCameras()

    const { filters, setFilter, setFilters } = useMediaQueryStore()
    const {
        viewMode,
        setViewMode,
        dateGroupMode,
        setDateGroupMode,
        thumbSize,
        setThumbSize,
    } = useViewPrefsStore()

    const currentSortKey = `${filters.sort}:${filters.order}`
    const isDateSort = filters.sort === "date_taken"
    if (!showFilters) return null

    return (
        <div className="scrollbar-hide absolute right-0 top-full z-50 mt-2 max-h-[calc(100vh-7rem)] w-[min(calc(100vw-6.5rem),24rem)] overflow-y-auto rounded-[2rem] border border-border bg-popover p-4 text-popover-foreground shadow-2xl shadow-black/20">
            <div className="space-y-4.5">
                <Section label="Type">
                    <div className="flex gap-1.5 rounded-[1.35rem] bg-secondary/45 p-1.5">
                        {typeTabs.map((tab) => {
                            const Icon = tab.icon
                            const isActive = (filters.type ?? "") === tab.key
                            return (
                                <button
                                    key={tab.key}
                                    onClick={() => setFilter("type", tab.key || null)}
                                    className={cn(
                                        "flex h-9 flex-1 items-center justify-center gap-1.5 overflow-hidden rounded-2xl text-xs font-medium transition-all duration-200",
                                        isActive
                                            ? "bg-background text-foreground shadow-sm ring-1 ring-border/50"
                                            : "text-muted-foreground/60 hover:text-foreground/70",
                                    )}
                                >
                                    <Icon className="h-3.5 w-3.5 shrink-0" />
                                    <span className="truncate">{tab.label}</span>
                                </button>
                            )
                        })}
                    </div>
                </Section>

                <Section label="Sort">
                    <div className="grid grid-cols-2 gap-2.5">
                        {sortTabs.map((tab) => {
                            const Icon = tab.icon
                            const isActive = currentSortKey === tab.key
                            return (
                                <button
                                    key={tab.key}
                                    onClick={() => {
                                        const [sort, order] = tab.key.split(":") as [SortKey, SortOrder]
                                        setFilters({ sort, order })
                                    }}
                                    className={cn(
                                        "flex h-10 items-center justify-center gap-1.5 overflow-hidden rounded-[1.15rem] text-xs font-medium transition-all duration-200",
                                        isActive
                                            ? "bg-primary/15 text-primary ring-1 ring-primary/25"
                                            : "bg-secondary/40 text-muted-foreground/65 hover:bg-secondary/70 hover:text-foreground",
                                    )}
                                >
                                    <Icon className="h-3.5 w-3.5 shrink-0" />
                                    <span className="truncate">{tab.label}</span>
                                </button>
                            )
                        })}
                    </div>
                </Section>

                {isDateSort && (
                    <Section label="Group">
                        <div className="flex gap-1.5 rounded-[1.35rem] bg-secondary/45 p-1.5">
                            {groupTabs.map((tab) => {
                                const Icon = tab.icon
                                const isActive = dateGroupMode === tab.key
                                return (
                                    <button
                                        key={tab.key}
                                        onClick={() => setDateGroupMode(tab.key as DateGroupMode)}
                                        className={cn(
                                            "flex h-9 flex-1 items-center justify-center gap-1.5 overflow-hidden rounded-2xl text-xs font-medium transition-all duration-200",
                                            isActive
                                                ? "bg-background text-foreground shadow-sm ring-1 ring-border/50"
                                                : "text-muted-foreground/60 hover:text-foreground/70",
                                        )}
                                    >
                                        <Icon className="h-3.5 w-3.5 shrink-0" />
                                        <span className="truncate">{tab.label}</span>
                                    </button>
                                )
                            })}
                        </div>
                    </Section>
                )}

                <Section label="View">
                    <div className="flex gap-1.5 rounded-[1.35rem] bg-secondary/45 p-1.5">
                        {viewTabs.map((tab) => {
                            const Icon = tab.icon
                            const isActive = viewMode === tab.key
                            return (
                                <button
                                    key={tab.key}
                                    onClick={() => setViewMode(tab.key as ViewMode)}
                                    className={cn(
                                        "flex h-9 flex-1 items-center justify-center gap-1.5 overflow-hidden rounded-2xl text-xs font-medium transition-all duration-200",
                                        isActive
                                            ? "bg-background text-foreground shadow-sm ring-1 ring-border/50"
                                            : "text-muted-foreground/60 hover:text-foreground/70",
                                    )}
                                >
                                    <Icon className="h-3.5 w-3.5 shrink-0" />
                                    <span className="truncate">{tab.label}</span>
                                </button>
                            )
                        })}
                    </div>
                </Section>

                <Section label="Size">
                    <div className="flex h-11 items-center gap-2.5 rounded-[1.35rem] bg-secondary/45 px-2.5">
                        <button
                            onClick={() => setThumbSize(Math.max(config.thumbSize.min, thumbSize - 40))}
                            disabled={thumbSize <= config.thumbSize.min}
                            className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground/60 transition-all duration-150 hover:bg-background/60 hover:text-foreground/80 active:scale-90 disabled:pointer-events-none disabled:opacity-25"
                        >
                            <Minus className="h-3 w-3" />
                        </button>
                        <div className="flex-1 h-1 rounded-full bg-border relative overflow-hidden">
                            <div
                                className="absolute inset-y-0 left-0 rounded-full bg-primary/50 transition-all duration-200"
                                style={{ width: `${((thumbSize - config.thumbSize.min) / (config.thumbSize.max - config.thumbSize.min)) * 100}%` }}
                            />
                        </div>
                        <button
                            onClick={() => setThumbSize(Math.min(config.thumbSize.max, thumbSize + 40))}
                            disabled={thumbSize >= config.thumbSize.max}
                            className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground/60 transition-all duration-150 hover:bg-background/60 hover:text-foreground/80 active:scale-90 disabled:pointer-events-none disabled:opacity-25"
                        >
                            <Plus className="h-3 w-3" />
                        </button>
                    </div>
                </Section>

                <Section label="Date Range">
                    <div className="flex h-11 items-center overflow-hidden rounded-[1.35rem] bg-secondary/45 px-3.5">
                        <input
                            type="date"
                            value={filters.date_from ?? ""}
                            onChange={(e) => setFilter("date_from", e.target.value || null)}
                            className="min-w-0 flex-1 cursor-pointer appearance-none border-0 bg-transparent text-xs font-medium text-foreground/80 outline-none placeholder:text-muted-foreground/40 focus:ring-0 [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:hover:opacity-80"
                        />
                        <span className="text-muted-foreground/30 px-2 text-xs">→</span>
                        <input
                            type="date"
                            value={filters.date_to ?? ""}
                            onChange={(e) => setFilter("date_to", e.target.value || null)}
                            className="min-w-0 flex-1 cursor-pointer appearance-none border-0 bg-transparent text-right text-xs font-medium text-foreground/80 outline-none placeholder:text-muted-foreground/40 focus:ring-0 [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:hover:opacity-80"
                        />
                    </div>
                </Section>

                {filters.lat != null && filters.lon != null && (
                    <Section label="Location">
                        <div className="flex h-10 items-center justify-between gap-2 rounded-[1.15rem] border border-emerald-500/20 bg-secondary/50 px-3">
                            <div className="flex items-center gap-2 min-w-0">
                                <MapPin className="h-3.5 w-3.5 text-emerald-500/70 shrink-0" />
                                <span className="text-xs font-medium truncate text-emerald-600 dark:text-emerald-400">
                                    {`${filters.lat?.toFixed(2)}, ${filters.lon?.toFixed(2)}`}
                                </span>
                                <span className="text-[10px] text-muted-foreground/50 shrink-0">
                                    (~{Math.round(filters.radius ?? 0)}km)
                                </span>
                            </div>
                            <button
                                onClick={() => setFilters({ lat: null, lon: null, radius: null })}
                                className="p-1 -mr-1 text-muted-foreground/50 hover:text-foreground/80 transition-colors"
                            >
                                <X className="h-3 w-3" />
                            </button>
                        </div>
                    </Section>
                )}

                <Section label="Min Rating">
                    <div className="flex h-11 items-center rounded-[1.35rem] bg-secondary/45 px-3.5">
                        <StarRating
                            value={filters.min_rating ?? 0}
                            interactive
                            size={18}
                            onChange={(v) => setFilter("min_rating", v === (filters.min_rating ?? 0) ? null : v)}
                        />
                    </div>
                </Section>

                {cameras.length > 0 && (
                    <Section label="Camera">
                        <div className="relative">
                            <Camera className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/45" />
                            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground/35" />
                            <select
                                value={filters.camera ?? ""}
                                onChange={(e) => setFilter("camera", e.target.value || null)}
                                className="h-11 w-full cursor-pointer appearance-none rounded-[1.35rem] border-0 bg-secondary/45 pl-9 pr-8 text-xs font-medium text-foreground/80 outline-none focus:ring-2 focus:ring-ring/15"
                            >
                                <option value="" className="bg-popover">All Cameras</option>
                                {cameras.map((c) => (
                                    <option key={`${c.make}-${c.model}`} value={c.model || c.make} className="bg-popover">
                                        {[c.make, c.model].filter(Boolean).join(" ")} ({c.count})
                                    </option>
                                ))}
                            </select>
                        </div>
                    </Section>
                )}
            </div>
        </div>
    )
}

function Section({
    label,
    children,
}: {
    label: string
    children: React.ReactNode
}) {
    return (
        <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/45">
                {label}
            </p>
            {children}
        </div>
    )
}
