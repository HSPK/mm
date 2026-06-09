import { useNavigate } from "react-router-dom"
import {
    ArrowDownWideNarrow,
    ArrowUpWideNarrow,
    Calendar,
    CalendarDays,
    Camera,
    ChevronDown,
    Copy,
    Film,
    HardDrive,
    Image,
    LayoutDashboard,
    LayoutGrid,
    LogOut,
    Map as MapIcon,
    MapPin,
    Minus,
    Plus,
    Settings,
    Star,
    StretchHorizontal,
    Tag as TagIcon,
    X,
} from "lucide-react"
import { useCameras } from "@/hooks/use-cameras"
import { useLogoutRedirect } from "@/hooks/use-logout-redirect"
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
    onNavigate: () => void
}

export function FilterMenu({ showFilters, onNavigate }: FilterMenuProps) {
    const navigate = useNavigate()
    const handleLogout = useLogoutRedirect()
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

    const navAndClose = (to: string) => {
        navigate(to)
        onNavigate()
    }

    return (
        <div className="absolute right-0 top-full mt-2 w-72 rounded-3xl material-thick elevation-3 border border-border/50 py-2 z-50 overflow-hidden max-h-[calc(100vh-6rem)] overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-muted-foreground/20 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/40 [&::-webkit-scrollbar-track]:bg-transparent">
            {showFilters && (
                <div className="border-b border-border px-4 py-3.5 space-y-3.5">
                    <Section label="Type">
                        <div className="flex rounded-2xl bg-secondary/50 p-1 gap-0.5">
                            {typeTabs.map((tab) => {
                                const Icon = tab.icon
                                const isActive = (filters.type ?? "") === tab.key
                                return (
                                    <button
                                        key={tab.key}
                                        onClick={() => setFilter("type", tab.key || null)}
                                        className={cn(
                                            "flex-1 flex items-center justify-center gap-1 h-8 rounded-xl text-xs font-medium transition-all duration-200 overflow-hidden",
                                            isActive
                                                ? "bg-background text-foreground shadow-sm"
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
                        <div className="grid grid-cols-2 gap-1.5">
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
                                            "flex items-center justify-center gap-1 h-8 rounded-xl text-xs font-medium transition-all duration-200 overflow-hidden",
                                            isActive
                                                ? "bg-primary/15 text-primary ring-1 ring-primary/20"
                                                : "bg-secondary/50 text-muted-foreground/60 hover:text-muted-foreground hover:bg-secondary",
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
                            <div className="flex rounded-2xl bg-secondary/50 p-1 gap-0.5">
                                {groupTabs.map((tab) => {
                                    const Icon = tab.icon
                                    const isActive = dateGroupMode === tab.key
                                    return (
                                        <button
                                            key={tab.key}
                                            onClick={() => setDateGroupMode(tab.key as DateGroupMode)}
                                            className={cn(
                                                "flex-1 flex items-center justify-center gap-1 h-8 rounded-xl text-xs font-medium transition-all duration-200 overflow-hidden",
                                                isActive
                                                    ? "bg-background text-foreground shadow-sm"
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
                        <div className="flex rounded-2xl bg-secondary/50 p-1 gap-0.5">
                            {viewTabs.map((tab) => {
                                const Icon = tab.icon
                                const isActive = viewMode === tab.key
                                return (
                                    <button
                                        key={tab.key}
                                        onClick={() => setViewMode(tab.key as ViewMode)}
                                        className={cn(
                                            "flex-1 flex items-center justify-center gap-1 h-8 rounded-xl text-xs font-medium transition-all duration-200 overflow-hidden",
                                            isActive
                                                ? "bg-background text-foreground shadow-sm"
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
                        <div className="flex items-center gap-1.5 h-8 rounded-2xl bg-secondary/50 px-1.5">
                            <button
                                onClick={() => setThumbSize(Math.max(config.thumbSize.min, thumbSize - 40))}
                                disabled={thumbSize <= config.thumbSize.min}
                                className="flex items-center justify-center h-6 w-6 rounded-full text-muted-foreground/60 hover:text-foreground/80 active:scale-90 transition-all duration-150 disabled:opacity-25 disabled:pointer-events-none"
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
                                className="flex items-center justify-center h-6 w-6 rounded-full text-muted-foreground/60 hover:text-foreground/80 active:scale-90 transition-all duration-150 disabled:opacity-25 disabled:pointer-events-none"
                            >
                                <Plus className="h-3 w-3" />
                            </button>
                        </div>
                    </Section>

                    <Section label="Date Range">
                        <div className="flex items-center h-8 rounded-xl bg-secondary/50 px-2 overflow-hidden">
                            <input
                                type="date"
                                value={filters.date_from ?? ""}
                                onChange={(e) => setFilter("date_from", e.target.value || null)}
                                className="flex-1 min-w-0 bg-transparent text-xs font-medium appearance-none border-0 outline-none focus:ring-0 text-foreground/80 cursor-pointer placeholder-muted-foreground/40 [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:hover:opacity-80"
                            />
                            <span className="text-muted-foreground/30 px-2 text-xs">→</span>
                            <input
                                type="date"
                                value={filters.date_to ?? ""}
                                onChange={(e) => setFilter("date_to", e.target.value || null)}
                                className="flex-1 min-w-0 bg-transparent text-xs font-medium appearance-none border-0 outline-none focus:ring-0 text-foreground/80 cursor-pointer placeholder-muted-foreground/40 [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:hover:opacity-80 text-right"
                            />
                        </div>
                    </Section>

                    {filters.lat != null && filters.lon != null && (
                        <Section label="Location">
                            <div className="flex items-center justify-between gap-2 h-8 rounded-xl bg-secondary/50 px-3 border border-emerald-500/20">
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
                        <div className="flex items-center h-8 px-3 rounded-2xl bg-secondary/50">
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
                                <Camera className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40 pointer-events-none" />
                                <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground/30 pointer-events-none" />
                                <select
                                    value={filters.camera ?? ""}
                                    onChange={(e) => setFilter("camera", e.target.value || null)}
                                    className="w-full h-8 rounded-xl bg-secondary/50 text-xs font-medium pl-8 pr-7 appearance-none border-0 outline-none focus:ring-1 focus:ring-ring/30 text-foreground/80 cursor-pointer"
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
            )}

            <div className="py-1 px-1.5">
                <MenuItem icon={MapIcon} label="Map" onClick={() => navAndClose("/map")} />
                <MenuItem icon={LayoutDashboard} label="Stats" onClick={() => navAndClose("/dashboard")} />
                <MenuItem icon={TagIcon} label="Manage tags" onClick={() => navAndClose("/tags")} />
                <MenuItem icon={Copy} label="Duplicates" onClick={() => navAndClose("/duplicates")} />
                <MenuItem icon={Settings} label="Settings" onClick={() => navAndClose("/settings")} />
            </div>

            <div className="border-t border-border pt-1 px-1.5">
                <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-3 px-3 py-2.5 text-sm text-destructive hover:bg-destructive/10 rounded-xl transition-colors"
                >
                    <LogOut className="h-4 w-4" />
                    Logout
                </button>
            </div>
        </div>
    )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div>
            <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">
                {label}
            </p>
            {children}
        </div>
    )
}

interface MenuItemProps {
    icon: typeof LayoutDashboard
    label: string
    onClick: () => void
}

function MenuItem({ icon: Icon, label, onClick }: MenuItemProps) {
    return (
        <button
            onClick={onClick}
            className="flex w-full items-center gap-3 px-3 py-2.5 text-sm text-foreground/80 hover:bg-secondary/60 rounded-xl transition-colors"
        >
            <Icon className="h-4 w-4 text-muted-foreground" />
            {label}
        </button>
    )
}
