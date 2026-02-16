import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import {
    Images,
    FolderHeart,
    Trash2,
    FolderPlus,
    CheckCheck,
    X,
    RotateCcw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useRef, useState, useEffect, useLayoutEffect, useCallback } from "react"
import { FloatingSearchBar } from "@/components/floating-search-bar"
import { useMediaStore } from "@/stores/media"
import { api } from "@/api/client"
import { Button } from "@/components/ui/button"
import MediaLibraryPage from "@/pages/media-library"
import AlbumsPage from "@/pages/albums"

const navItems = [
    { to: "/", label: "Library", icon: Images },
    { to: "/albums", label: "Albums", icon: FolderHeart },
]

const TAB_ROUTES = ["/", "/albums"]

function getActiveIndex(pathname: string) {
    // Exact match for "/", prefix match for others
    const idx = navItems.findIndex((item) =>
        item.to === "/" ? pathname === "/" : pathname.startsWith(item.to),
    )
    return idx === -1 ? 0 : idx
}

export default function AppLayout() {
    const location = useLocation()
    const navRef = useRef<HTMLElement>(null)
    const itemRefs = useRef<(HTMLAnchorElement | null)[]>([])
    const [indicator, setIndicator] = useState({ left: 0, width: 0 })
    const isTabRoute = TAB_ROUTES.includes(location.pathname)
    const activeTabIndex = getActiveIndex(location.pathname)

    // ─── Per-tab scroll containers (state for reactivity) ──
    const [libraryScrollEl, setLibraryScrollEl] = useState<HTMLDivElement | null>(null)
    const [albumsScrollEl, setAlbumsScrollEl] = useState<HTMLDivElement | null>(null)
    const [outletScrollEl, setOutletScrollEl] = useState<HTMLDivElement | null>(null)

    // Scroll Library to top when entering album view
    const { activeLabel: currentLabel, filters } = useMediaStore()
    const isDeletedView = filters.deleted
    const [prevLabel, setPrevLabel] = useState(currentLabel)
    if (currentLabel !== prevLabel) {
        setPrevLabel(currentLabel)
        if (currentLabel && libraryScrollEl) {
            libraryScrollEl.scrollTop = 0
        }
    }

    const activeScrollEl = isTabRoute
        ? (activeTabIndex === 0 ? libraryScrollEl : albumsScrollEl)
        : outletScrollEl

    // ─── Auto-hide both navs on scroll ─────────────────────
    const [navVisible, setNavVisible] = useState(true)
    const lastScrollY = useRef(0)

    // Reset visibility when active scroll container changes (during render)
    const [prevActiveScrollEl, setPrevActiveScrollEl] = useState(activeScrollEl)
    if (activeScrollEl !== prevActiveScrollEl) {
        setPrevActiveScrollEl(activeScrollEl)
        setNavVisible(true)
    }

    useEffect(() => {
        const el = activeScrollEl
        if (!el) return
        lastScrollY.current = el.scrollTop
        const handle = () => {
            const y = el.scrollTop
            if (y > lastScrollY.current && y > 60) {
                setNavVisible(false)
            } else {
                setNavVisible(true)
            }
            lastScrollY.current = y
        }
        el.addEventListener("scroll", handle, { passive: true })
        return () => el.removeEventListener("scroll", handle)
    }, [activeScrollEl])

    // ─── Nav indicator ─────────────────────────────────────
    const updateIndicator = useCallback(() => {
        const el = itemRefs.current[activeTabIndex]
        const nav = navRef.current
        if (el && nav) {
            const navRect = nav.getBoundingClientRect()
            const elRect = el.getBoundingClientRect()
            setIndicator({
                left: elRect.left - navRect.left,
                width: elRect.width,
            })
        }
    }, [activeTabIndex])

    useLayoutEffect(() => {
        updateIndicator()
    }, [updateIndicator])

    useEffect(() => {
        window.addEventListener("resize", updateIndicator)
        return () => window.removeEventListener("resize", updateIndicator)
    }, [updateIndicator])

    // ─── Swipe gesture for tab switching ─────────────────
    const navigate = useNavigate()
    const { activeLabel: inAlbumView } = useMediaStore()
    const swipeDisabled = !!inAlbumView
    const touchRef = useRef<{ startX: number; startY: number; startTime: number } | null>(null)
    const [swipeOffset, setSwipeOffset] = useState(0)
    const [swiping, setSwiping] = useState(false)

    const handleTouchStart = useCallback((e: React.TouchEvent) => {
        if (swipeDisabled) return
        const t = e.touches[0]
        touchRef.current = { startX: t.clientX, startY: t.clientY, startTime: Date.now() }
        setSwipeOffset(0)
        setSwiping(false)
    }, [swipeDisabled])

    const handleTouchMove = useCallback((e: React.TouchEvent) => {
        if (!touchRef.current) return
        const t = e.touches[0]
        const dx = t.clientX - touchRef.current.startX
        const dy = t.clientY - touchRef.current.startY

        // If mostly vertical, ignore
        if (!swiping && Math.abs(dy) > Math.abs(dx)) {
            touchRef.current = null
            return
        }

        // Start swiping only after a small threshold
        if (!swiping && Math.abs(dx) > 10) {
            setSwiping(true)
        }

        if (swiping || Math.abs(dx) > 10) {
            // Clamp: don't swipe past edges
            const maxLeft = activeTabIndex === 0 ? 0 : -Infinity
            const maxRight = activeTabIndex === navItems.length - 1 ? 0 : Infinity
            const clamped = Math.max(Math.min(dx, maxRight === Infinity ? dx : 0), maxLeft === -Infinity ? dx : 0)

            // Rubber band at edges
            if ((activeTabIndex === 0 && dx > 0) || (activeTabIndex === navItems.length - 1 && dx < 0)) {
                setSwipeOffset(dx * 0.2) // resistance
            } else {
                setSwipeOffset(clamped)
            }
        }
    }, [swiping, activeTabIndex])

    const handleTouchEnd = useCallback(() => {
        if (!touchRef.current || !swiping) {
            touchRef.current = null
            setSwipeOffset(0)
            setSwiping(false)
            return
        }

        const threshold = window.innerWidth * 0.25
        const velocity = Math.abs(swipeOffset) / (Date.now() - touchRef.current.startTime) * 1000

        if (swipeOffset > threshold || (swipeOffset > 30 && velocity > 500)) {
            // Swipe right → go to previous tab
            if (activeTabIndex > 0) {
                navigate(navItems[activeTabIndex - 1].to)
            }
        } else if (swipeOffset < -threshold || (swipeOffset < -30 && velocity > 500)) {
            // Swipe left → go to next tab
            if (activeTabIndex < navItems.length - 1) {
                navigate(navItems[activeTabIndex + 1].to)
            }
        }

        touchRef.current = null
        setSwipeOffset(0)
        setSwiping(false)
    }, [swipeOffset, swiping, activeTabIndex, navigate])

    // Check if filter tags will be shown on Library page (for dynamic padding)
    const hasFilterTags = !!(currentLabel || isDeletedView ||
        filters.type || filters.camera ||
        filters.date_from || filters.date_to ||
        filters.min_rating ||
        (filters.lat != null && filters.lon != null) ||
        filters.search
    )

    return (
        <div className="flex h-screen flex-col overflow-hidden bg-background">
            {/* Floating search bar — only on tab routes */}
            {isTabRoute && <FloatingSearchBar scrollContainer={activeScrollEl} />}

            {/* Content area */}
            <div className="flex-1 relative overflow-hidden">
                {/* Tab carousel — both tabs side by side, slide via translateX */}
                {isTabRoute && (
                    <div
                        className="absolute inset-0 flex"
                        style={{
                            transform: `translateX(calc(${-activeTabIndex * 100}% + ${swiping ? swipeOffset : 0}px))`,
                            transition: swiping ? 'none' : 'transform 300ms ease',
                            willChange: 'transform',
                        }}
                        onTouchStart={handleTouchStart}
                        onTouchMove={handleTouchMove}
                        onTouchEnd={handleTouchEnd}
                    >
                        <div ref={setLibraryScrollEl} className={cn("w-full h-full shrink-0 overflow-y-auto", hasFilterTags ? "pt-[5.5rem]" : "pt-16")}>
                            <MediaLibraryPage />
                        </div>
                        <div ref={setAlbumsScrollEl} className="w-full h-full shrink-0 overflow-y-auto pt-16">
                            <AlbumsPage />
                        </div>
                    </div>
                )}

                {/* Non-tab routes */}
                {!isTabRoute && (
                    <div
                        ref={setOutletScrollEl}
                        className="absolute inset-0 overflow-y-auto bg-background z-10"
                    >
                        <Outlet />
                    </div>
                )}
            </div>

            {/* Floating bottom navigation / selection action bar */}
            <BottomBar
                isTabRoute={isTabRoute}
                navVisible={navVisible}
                navRef={navRef}
                itemRefs={itemRefs}
                indicator={indicator}
            />
        </div>
    )
}

// ─── Bottom Bar: morphs between nav tabs and selection action bar ──

function BottomBar({
    isTabRoute,
    navVisible,
    navRef,
    itemRefs,
    indicator,
}: {
    isTabRoute: boolean
    navVisible: boolean
    navRef: React.RefObject<HTMLElement | null>
    itemRefs: React.MutableRefObject<(HTMLAnchorElement | null)[]>
    indicator: { left: number; width: number }
}) {
    const {
        selectionMode, selectedIds, items, total,
        exitSelectionMode, selectAll, removeItems,
        filters, resetFilters,
        activeLabel: viewingAlbum,
    } = useMediaStore()

    const isDeletedView = filters.deleted

    const [albumMode, setAlbumMode] = useState<false | "pick" | "create">(false)
    const [albums, setAlbums] = useState<{ id: number; name: string }[]>([])
    const [newAlbumName, setNewAlbumName] = useState("")
    const [busy, setBusy] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)

    // Reset album picker when exiting selection
    const [prevSelectionMode, setPrevSelectionMode] = useState(selectionMode)
    if (selectionMode !== prevSelectionMode) {
        setPrevSelectionMode(selectionMode)
        if (!selectionMode) setAlbumMode(false)
    }

    useEffect(() => {
        if (albumMode === "create") inputRef.current?.focus()
    }, [albumMode])

    const loadAlbums = useCallback(async () => {
        const res = await api.get<{ id: number; name: string }[]>("/albums")
        setAlbums(res.data)
    }, [])

    const addToAlbum = async (albumId: number) => {
        setBusy(true)
        await api.post(`/albums/${albumId}/media`, { media_ids: [...selectedIds] })
        setBusy(false)
        setAlbumMode(false)
    }

    const createAndAdd = async () => {
        const name = newAlbumName.trim()
        if (!name) return
        setBusy(true)
        const res = await api.post<{ id: number }>("/albums", { name })
        await api.post(`/albums/${res.data.id}/media`, { media_ids: [...selectedIds] })
        setBusy(false)
        setNewAlbumName("")
        setAlbumMode(false)
    }

    const handleDelete = async () => {
        const ids = [...selectedIds]
        if (ids.length === 0) return
        if (isDeletedView) {
            // In trash: permanent delete
            if (!window.confirm(`Permanently delete ${ids.length} item(s)?`)) return
            await Promise.allSettled(ids.map((id) => api.delete(`/media/${id}`, { params: { permanent: true } })))
            removeItems(ids)
            exitSelectionMode()
            if (items.length - ids.length <= 0) resetFilters()
        } else {
            // Normal: soft delete
            try {
                await api.post("/batch/delete", { media_ids: ids })
            } catch {
                await Promise.allSettled(ids.map((id) => api.delete(`/media/${id}`)))
            }
            removeItems(ids)
            exitSelectionMode()
        }
    }

    const handleRestore = async () => {
        const ids = selectionMode ? [...selectedIds] : items.map((i) => i.id)
        if (ids.length === 0) return
        if (!window.confirm(`Restore ${ids.length} item(s)?`)) return
        await Promise.allSettled(ids.map((id) => api.post(`/media/${id}/restore`)))
        removeItems(ids)
        exitSelectionMode()
        if (items.length - ids.length <= 0) resetFilters()
    }

    const handleEmptyTrash = async () => {
        if (!window.confirm(`Permanently delete all ${total} items? This cannot be undone.`)) return
        await api.delete("/media/trash")
        resetFilters()
    }

    const show = selectionMode || isDeletedView || (isTabRoute && navVisible && !viewingAlbum)

    return (
        <div
            className={cn(
                "fixed bottom-0 left-0 right-0 z-30 transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                show ? "translate-y-0" : "translate-y-full",
            )}
            style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
        >
            {/* Album picker dropdown — sits above the bar */}
            {selectionMode && albumMode && (
                <div className="flex justify-center px-4 pb-2">
                    <div className="w-full max-w-xs bg-popover border border-border rounded-2xl shadow-xl overflow-hidden">
                        {albumMode === "pick" ? (
                            <div className="max-h-48 overflow-y-auto p-1.5">
                                {albums.length === 0 && (
                                    <p className="text-xs text-muted-foreground/50 text-center py-4">No albums yet</p>
                                )}
                                {albums.map((a) => (
                                    <button
                                        key={a.id}
                                        onClick={() => addToAlbum(a.id)}
                                        disabled={busy}
                                        className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-sm text-foreground/80 hover:bg-secondary transition-colors text-left disabled:opacity-50"
                                    >
                                        <FolderPlus className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
                                        <span className="truncate">{a.name}</span>
                                    </button>
                                ))}
                                <button
                                    onClick={() => setAlbumMode("create")}
                                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-sm text-primary/80 hover:bg-primary/5 transition-colors text-left"
                                >
                                    <span className="h-3.5 w-3.5 flex items-center justify-center text-primary/60 shrink-0 text-base leading-none">+</span>
                                    <span>New album…</span>
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 p-2.5">
                                <input
                                    ref={inputRef}
                                    type="text"
                                    value={newAlbumName}
                                    onChange={(e) => setNewAlbumName(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") createAndAdd()
                                        if (e.key === "Escape") setAlbumMode("pick")
                                    }}
                                    placeholder="Album name"
                                    className="flex-1 h-9 rounded-lg bg-secondary px-3 text-sm outline-none focus:ring-1 focus:ring-ring/40 text-foreground placeholder:text-muted-foreground/40"
                                />
                                <Button
                                    size="sm"
                                    className="rounded-lg h-9 px-4 text-xs"
                                    onClick={createAndAdd}
                                    disabled={!newAlbumName.trim() || busy}
                                >
                                    {busy ? "…" : "Create"}
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* The bar itself */}
            <div className="flex justify-center px-4 pb-4">
                {selectionMode ? (
                    /* ── Selection action bar (works for both library and trash) ── */
                    <div className="relative flex items-center gap-1 px-2 py-1.5 bg-background border border-border shadow-2xl shadow-black/10 rounded-full">
                        <button
                            onClick={() => { exitSelectionMode() }}
                            className="relative z-10 flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                        >
                            <X className="h-[1.15rem] w-[1.15rem]" />
                            <span>Cancel</span>
                        </button>

                        <span className="text-[10px] font-semibold text-foreground/80 px-2 tabular-nums">
                            {selectedIds.size}
                        </span>

                        <button
                            onClick={selectAll}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                            title="Select all"
                        >
                            <CheckCheck className="h-[1.15rem] w-[1.15rem]" />
                            <span>All</span>
                        </button>

                        {isDeletedView ? (
                            <>
                                <button
                                    onClick={handleRestore}
                                    className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                                    title="Restore"
                                >
                                    <RotateCcw className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Restore</span>
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-destructive/70 hover:text-destructive transition-colors"
                                    title="Delete permanently"
                                >
                                    <Trash2 className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Delete</span>
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    onClick={() => { if (albumMode) setAlbumMode(false); else { loadAlbums(); setAlbumMode("pick") } }}
                                    className={cn(
                                        "relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium transition-colors",
                                        albumMode ? "text-primary" : "text-muted-foreground/70 hover:text-foreground"
                                    )}
                                    title="Add to album"
                                >
                                    <FolderPlus className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Album</span>
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-destructive/70 hover:text-destructive transition-colors"
                                    title="Delete"
                                >
                                    <Trash2 className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Delete</span>
                                </button>
                            </>
                        )}
                    </div>
                ) : isDeletedView ? (
                    /* ── Trash default bar (no selection yet) ── */
                    <div className="relative flex items-center gap-1 px-2 py-1.5 bg-background border border-border shadow-2xl shadow-black/10 rounded-full">
                        <button
                            onClick={resetFilters}
                            className="relative z-10 flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                        >
                            <X className="h-[1.15rem] w-[1.15rem]" />
                            <span>Back</span>
                        </button>

                        <span className="text-[10px] font-semibold text-foreground/80 px-2 tabular-nums">
                            {total}
                        </span>

                        <button
                            onClick={selectAll}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                            title="Select all"
                        >
                            <CheckCheck className="h-[1.15rem] w-[1.15rem]" />
                            <span>All</span>
                        </button>
                        <button
                            onClick={handleRestore}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                            title="Restore all"
                        >
                            <RotateCcw className="h-[1.15rem] w-[1.15rem]" />
                            <span>Restore</span>
                        </button>
                        <button
                            onClick={handleEmptyTrash}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-destructive/70 hover:text-destructive transition-colors"
                            title="Empty trash"
                        >
                            <Trash2 className="h-[1.15rem] w-[1.15rem]" />
                            <span>Empty</span>
                        </button>
                    </div>
                ) : (
                    /* ── Normal tab navigation ── */
                    <nav
                        ref={navRef}
                        className="relative flex items-center gap-1 px-2 py-2 bg-background/80 backdrop-blur-xl border border-border/60 shadow-2xl shadow-black/10 rounded-full"
                    >
                        <div
                            className="absolute top-2 h-[calc(100%-1rem)] rounded-full bg-primary/12 transition-all duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]"
                            style={{ left: indicator.left, width: indicator.width }}
                        />
                        {navItems.map((item, i) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                end={item.to === "/"}
                                ref={(el) => { itemRefs.current[i] = el }}
                                className={({ isActive }) =>
                                    cn(
                                        "relative z-10 flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-full text-[10px] font-medium transition-colors duration-200",
                                        isActive
                                            ? "text-primary"
                                            : "text-muted-foreground/50 hover:text-foreground/70",
                                    )
                                }
                            >
                                <item.icon className="h-[1.15rem] w-[1.15rem]" />
                                <span>{item.label}</span>
                            </NavLink>
                        ))}
                    </nav>
                )}
            </div>
        </div>
    )
}
