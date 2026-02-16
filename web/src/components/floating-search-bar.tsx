import { useState, useEffect, useRef } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { useAuthStore } from "@/stores/auth"
import { useMediaStore } from "@/stores/media"
import { api } from "@/api/client"
import { Input } from "@/components/ui/input"
import { StarRating } from "@/components/ui/star-rating"

import {
    Search,
    Menu,
    X,
    LayoutDashboard,
    Settings,
    LogOut,
    Film,
    Image,
    LayoutGrid,
    StretchHorizontal,
    ArrowDownWideNarrow,
    ArrowUpWideNarrow,
    Star,
    HardDrive,
    Calendar,
    CalendarDays,
    Minus,
    Plus,
    Camera,
    MapPin,
    ChevronDown,
} from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Floating search bar with hamburger menu — auto-hides on scroll down,
 * reappears on scroll up. Lives at layout level so it floats over page content.
 *
 * On the Library page ("/"), the menu also shows media filters
 * (type, sort, group mode, view mode, star rating).
 */
export function FloatingSearchBar({ scrollContainer }: { scrollContainer?: HTMLElement | null }) {
    const navigate = useNavigate()
    const location = useLocation()
    const logout = useAuthStore((s) => s.logout)
    const {
        total, filters, setFilter, setFilters,
        viewMode, setViewMode,
        dateGroupMode, setDateGroupMode,
        thumbSize, setThumbSize,
    } = useMediaStore()

    const [searchInput, setSearchInput] = useState(filters.search ?? "")
    const [menuOpen, setMenuOpen] = useState(false)
    const [visible, setVisible] = useState(true)
    const menuRef = useRef<HTMLDivElement>(null)
    const lastScrollY = useRef(0)

    const isLibrary = location.pathname === "/"


    // Fetch camera list for filter
    const [cameras, setCameras] = useState<{ make: string; model: string; count: number }[]>([])
    useEffect(() => {
        api.get<{ make: string; model: string; count: number }[]>("/cameras")
            .then(res => setCameras(res.data))
            .catch(() => { })
    }, [])

    // Sync searchInput when store filter changes externally
    useEffect(() => {
        setSearchInput(filters.search ?? "")
    }, [filters.search])

    // Auto-hide on scroll down, show on scroll up
    useEffect(() => {
        const el = scrollContainer
        if (!el) return
        // Reset on container switch (tab change)
        lastScrollY.current = el.scrollTop
        setVisible(true)
        const handle = () => {
            const y = el.scrollTop
            if (y > lastScrollY.current && y > 60) {
                setVisible(false)
                setMenuOpen(false)
            } else {
                setVisible(true)
            }
            lastScrollY.current = y
        }
        el.addEventListener("scroll", handle, { passive: true })
        return () => el.removeEventListener("scroll", handle)
    }, [scrollContainer])

    // Close menu on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false)
            }
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    const submitSearch = () => {
        setFilter("search", searchInput || null)
    }

    const handleLogout = () => {
        logout()
        navigate("/login", { replace: true })
    }

    // ─── Filter definitions (only used on Library page) ──
    const currentSortKey = `${filters.sort}:${filters.order}`
    const isDateSort = filters.sort === "date_taken"

    const typeTabs = [
        { key: "", label: "All", icon: LayoutGrid },
        { key: "photo", label: "Photos", icon: Image },
        { key: "video", label: "Videos", icon: Film },
    ] as const

    const sortTabs = [
        { key: "date_taken:desc", label: "Newest", icon: ArrowDownWideNarrow },
        { key: "date_taken:asc", label: "Oldest", icon: ArrowUpWideNarrow },
        { key: "rating:desc", label: "Top Rated", icon: Star },
        { key: "file_size:desc", label: "Largest", icon: HardDrive },
    ] as const

    const groupTabs = [
        { key: "month", label: "Month", icon: Calendar },
        { key: "day", label: "Day", icon: CalendarDays },
    ] as const

    const viewTabs = [
        { key: "justified", label: "Justified", icon: StretchHorizontal },
        { key: "grid", label: "Grid", icon: LayoutGrid },
    ] as const

    return (
        <div
            className={cn(
                "fixed top-0 left-0 right-0 z-40 transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                visible ? "translate-y-0" : "-translate-y-full",
            )}
            style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
        >
            <div className="px-4 pt-2.5 pb-1 mx-auto max-w-2xl">
                <div className="flex items-center gap-2">
                    {/* Search input — capsule shape */}
                    <div className="relative flex-1">
                        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-[18px] w-[18px] text-muted-foreground/40" />
                        <Input
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && submitSearch()}
                            placeholder="Search…"
                            className="w-full h-11 pl-11 pr-4 text-sm bg-background/80 backdrop-blur-xl border border-border/60 rounded-full placeholder:text-muted-foreground/40 focus-visible:ring-1 focus-visible:ring-ring/30 shadow-lg shadow-black/10"
                        />
                    </div>

                    {/* Menu button */}
                    <div className="relative" ref={menuRef}>
                        <button
                            onClick={() => setMenuOpen(!menuOpen)}
                            className={cn(
                                "flex h-11 w-11 items-center justify-center rounded-full backdrop-blur-xl border shadow-lg shadow-black/10 transition-all duration-200",
                                menuOpen
                                    ? "bg-secondary border-border text-foreground"
                                    : "bg-background/80 border-border/60 text-muted-foreground hover:bg-secondary/80"
                            )}
                        >
                            {menuOpen ? (
                                <X className="h-[18px] w-[18px]" />
                            ) : (
                                <Menu className="h-[18px] w-[18px]" />
                            )}
                        </button>

                        {/* Dropdown menu */}
                        {menuOpen && (
                            <div className="absolute right-0 top-full mt-2 w-72 rounded-3xl border border-border bg-popover/95 backdrop-blur-2xl shadow-2xl shadow-black/20 py-2 z-50 overflow-hidden max-h-[calc(100vh-6rem)] overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-muted-foreground/20 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/40 [&::-webkit-scrollbar-track]:bg-transparent">
                                {/* ── Library Filters (only on "/" route) ── */}
                                {isLibrary && (
                                    <div className="border-b border-border px-4 py-3.5 space-y-3.5">
                                        {/* Type filter — segmented */}
                                        <div>
                                            <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Type</p>
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
                                                                    : "text-muted-foreground/60 hover:text-foreground/70"
                                                            )}
                                                        >
                                                            <Icon className="h-3.5 w-3.5 shrink-0" />
                                                            <span className="truncate">{tab.label}</span>
                                                        </button>
                                                    )
                                                })}
                                            </div>
                                        </div>

                                        {/* Sort — 2×2 grid for uniform sizing */}
                                        <div>
                                            <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Sort</p>
                                            <div className="grid grid-cols-2 gap-1.5">
                                                {sortTabs.map((tab) => {
                                                    const Icon = tab.icon
                                                    const isActive = currentSortKey === tab.key
                                                    return (
                                                        <button
                                                            key={tab.key}
                                                            onClick={() => {
                                                                const [sort, order] = tab.key.split(":")
                                                                setFilters({ sort, order })
                                                            }}
                                                            className={cn(
                                                                "flex items-center justify-center gap-1 h-8 rounded-xl text-xs font-medium transition-all duration-200 overflow-hidden",
                                                                isActive
                                                                    ? "bg-primary/15 text-primary ring-1 ring-primary/20"
                                                                    : "bg-secondary/50 text-muted-foreground/60 hover:text-muted-foreground hover:bg-secondary"
                                                            )}
                                                        >
                                                            <Icon className="h-3.5 w-3.5 shrink-0" />
                                                            <span className="truncate">{tab.label}</span>
                                                        </button>
                                                    )
                                                })}
                                            </div>
                                        </div>

                                        {/* Group mode (only for date sort) */}
                                        {isDateSort && (
                                            <div>
                                                <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Group</p>
                                                <div className="flex rounded-2xl bg-secondary/50 p-1 gap-0.5">
                                                    {groupTabs.map((tab) => {
                                                        const Icon = tab.icon
                                                        const isActive = dateGroupMode === tab.key
                                                        return (
                                                            <button
                                                                key={tab.key}
                                                                onClick={() => setDateGroupMode(tab.key as "day" | "month")}
                                                                className={cn(
                                                                    "flex-1 flex items-center justify-center gap-1 h-8 rounded-xl text-xs font-medium transition-all duration-200 overflow-hidden",
                                                                    isActive
                                                                        ? "bg-background text-foreground shadow-sm"
                                                                        : "text-muted-foreground/60 hover:text-foreground/70"
                                                                )}
                                                            >
                                                                <Icon className="h-3.5 w-3.5 shrink-0" />
                                                                <span className="truncate">{tab.label}</span>
                                                            </button>
                                                        )
                                                    })}
                                                </div>
                                            </div>
                                        )}

                                        {/* View mode */}
                                        <div>
                                            <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">View</p>
                                            <div className="flex rounded-2xl bg-secondary/50 p-1 gap-0.5">
                                                {viewTabs.map((tab) => {
                                                    const Icon = tab.icon
                                                    const isActive = viewMode === tab.key
                                                    return (
                                                        <button
                                                            key={tab.key}
                                                            onClick={() => setViewMode(tab.key as "justified" | "grid")}
                                                            className={cn(
                                                                "flex-1 flex items-center justify-center gap-1 h-8 rounded-xl text-xs font-medium transition-all duration-200 overflow-hidden",
                                                                isActive
                                                                    ? "bg-background text-foreground shadow-sm"
                                                                    : "text-muted-foreground/60 hover:text-foreground/70"
                                                            )}
                                                        >
                                                            <Icon className="h-3.5 w-3.5 shrink-0" />
                                                            <span className="truncate">{tab.label}</span>
                                                        </button>
                                                    )
                                                })}
                                            </div>
                                        </div>

                                        {/* Thumbnail size +/- */}
                                        <div>
                                            <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Size</p>
                                            <div className="flex items-center gap-1.5 h-8 rounded-2xl bg-secondary/50 px-1.5">
                                                <button
                                                    onClick={() => setThumbSize(Math.max(80, thumbSize - 40))}
                                                    disabled={thumbSize <= 80}
                                                    className="flex items-center justify-center h-6 w-6 rounded-full text-muted-foreground/60 hover:text-foreground/80 active:scale-90 transition-all duration-150 disabled:opacity-25 disabled:pointer-events-none"
                                                >
                                                    <Minus className="h-3 w-3" />
                                                </button>
                                                <div className="flex-1 h-1 rounded-full bg-border relative overflow-hidden">
                                                    <div
                                                        className="absolute inset-y-0 left-0 rounded-full bg-primary/50 transition-all duration-200"
                                                        style={{ width: `${((thumbSize - 80) / (400 - 80)) * 100}%` }}
                                                    />
                                                </div>
                                                <button
                                                    onClick={() => setThumbSize(Math.min(400, thumbSize + 40))}
                                                    disabled={thumbSize >= 400}
                                                    className="flex items-center justify-center h-6 w-6 rounded-full text-muted-foreground/60 hover:text-foreground/80 active:scale-90 transition-all duration-150 disabled:opacity-25 disabled:pointer-events-none"
                                                >
                                                    <Plus className="h-3 w-3" />
                                                </button>
                                            </div>
                                        </div>

                                        {/* Date Range Filter */}
                                        <div>
                                            <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Date Range</p>
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
                                        </div>

                                        {/* Location Filter */}
                                        {filters.lat != null && filters.lon != null && (
                                            <div>
                                                <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Location</p>
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
                                            </div>
                                        )}

                                        {/* Star rating filter */}
                                        <div>
                                            <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Min Rating</p>
                                            <div className="flex items-center h-8 px-3 rounded-2xl bg-secondary/50">
                                                <StarRating
                                                    value={filters.min_rating ?? 0}
                                                    interactive
                                                    size={18}
                                                    onChange={(v) => setFilter("min_rating", v === (filters.min_rating ?? 0) ? null : v)}
                                                />
                                            </div>
                                        </div>

                                        {/* Camera filter */}
                                        {cameras.length > 0 && (
                                            <div>
                                                <p className="text-[10px] font-semibold text-muted-foreground/40 uppercase tracking-widest mb-2">Camera</p>
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
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Navigation items */}
                                <div className="py-1 px-1.5">
                                    <button
                                        onClick={() => { navigate("/dashboard"); setMenuOpen(false) }}
                                        className="flex w-full items-center gap-3 px-3 py-2.5 text-sm text-foreground/80 hover:bg-secondary/60 rounded-xl transition-colors"
                                    >
                                        <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
                                        Stats
                                    </button>
                                    <button
                                        onClick={() => { navigate("/settings"); setMenuOpen(false) }}
                                        className="flex w-full items-center gap-3 px-3 py-2.5 text-sm text-foreground/80 hover:bg-secondary/60 rounded-xl transition-colors"
                                    >
                                        <Settings className="h-4 w-4 text-muted-foreground" />
                                        Settings
                                    </button>
                                </div>

                                {/* Logout */}
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
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
