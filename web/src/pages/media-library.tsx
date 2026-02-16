import { useEffect, useRef, useState, useMemo, useLayoutEffect, useCallback, memo } from "react"
import { useMediaStore } from "@/stores/media"
import { Button } from "@/components/ui/button"
import { StarRating } from "@/components/ui/star-rating"
import { Loader2, Film, ImageOff } from "lucide-react"
import { AuthImage } from "@/components/auth-image"
import { MediaDetailPanel } from "@/components/media-detail"
import { cn } from "@/lib/utils"
import type { Media } from "@/api/types"

// ─── helpers ──────────────────────────────────────────────
function fmtDateShort(iso: string | null | undefined) {
    if (!iso) return ""
    const d = new Date(iso)
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

/** Format for month grouping: "2024 · 01" */
function fmtMonthGroup(iso: string) {
    const d = new Date(iso)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, "0")
    return `${year} · ${month}`
}

/** Get month key for grouping: "2024-01" */
function getMonthKey(iso: string) {
    const d = new Date(iso)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
}

/** Format for day grouping: "2024 · 01 · 15" */
function fmtDayGroup(iso: string) {
    const d = new Date(iso)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, "0")
    const day = String(d.getDate()).padStart(2, "0")
    return `${year} · ${month} · ${day}`
}

/** Get day key for grouping: "2024-01-15" */
function getDayKey(iso: string) {
    const d = new Date(iso)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

function fmtDuration(seconds: number | null | undefined) {
    if (!seconds) return null
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, "0")}`
}

/** Group items by month for date-sorted views */
function groupByMonth(items: Media[]): { key: string; label: string; items: Media[] }[] {
    const map = new Map<string, { label: string; items: Media[] }>()
    for (const item of items) {
        if (item.date_taken) {
            const key = getMonthKey(item.date_taken)
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: fmtMonthGroup(item.date_taken), items: [item] })
            }
        } else {
            const key = "no-date"
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: "No Date", items: [item] })
            }
        }
    }
    return Array.from(map.entries()).map(([key, { label, items }]) => ({ key, label, items }))
}

/** Group items by day for date-sorted views */
function groupByDay(items: Media[]): { key: string; label: string; items: Media[] }[] {
    const map = new Map<string, { label: string; items: Media[] }>()
    for (const item of items) {
        if (item.date_taken) {
            const key = getDayKey(item.date_taken)
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: fmtDayGroup(item.date_taken), items: [item] })
            }
        } else {
            const key = "no-date"
            const existing = map.get(key)
            if (existing) {
                existing.items.push(item)
            } else {
                map.set(key, { label: "No Date", items: [item] })
            }
        }
    }
    return Array.from(map.entries()).map(([key, { label, items }]) => ({ key, label, items }))
}

// ─── component ────────────────────────────────────────────
export default function MediaLibraryPage() {
    const {
        items, loading, hasMore, error,
        filters, fetchMedia, resetFilters,
        viewMode, dateGroupMode,
        thumbSize, setThumbSize,
        removeItem,
        selectionMode, selectedIds,
        enterSelectionMode, toggleSelected,
    } = useMediaStore()

    const sentinelRef = useRef<HTMLDivElement>(null)
    const galleryRef = useRef<HTMLDivElement>(null)

    // ─── Pinch-to-zoom (trackpad ctrl+wheel & touch pinch) ──
    const thumbSizeRef = useRef(thumbSize)
    useEffect(() => {
        thumbSizeRef.current = thumbSize
    }, [thumbSize])

    useEffect(() => {
        const el = galleryRef.current
        if (!el) return

        const onWheel = (e: WheelEvent) => {
            if (!e.ctrlKey) return
            e.preventDefault()
            const delta = -e.deltaY
            const next = Math.round(thumbSizeRef.current + delta * 0.5)
            setThumbSize(Math.min(400, Math.max(80, next)))
        }

        let initDist = 0
        let initSize = 0
        const dist = (t: TouchList) => {
            const dx = t[0].clientX - t[1].clientX
            const dy = t[0].clientY - t[1].clientY
            return Math.hypot(dx, dy)
        }
        const onTouchStart = (e: TouchEvent) => {
            if (e.touches.length === 2) {
                initDist = dist(e.touches)
                initSize = thumbSizeRef.current
            }
        }
        const onTouchMove = (e: TouchEvent) => {
            if (e.touches.length === 2) {
                e.preventDefault()
                const scale = dist(e.touches) / initDist
                setThumbSize(Math.min(400, Math.max(80, Math.round(initSize * scale))))
            }
        }

        el.addEventListener("wheel", onWheel, { passive: false })
        el.addEventListener("touchstart", onTouchStart, { passive: true })
        el.addEventListener("touchmove", onTouchMove, { passive: false })
        return () => {
            el.removeEventListener("wheel", onWheel)
            el.removeEventListener("touchstart", onTouchStart)
            el.removeEventListener("touchmove", onTouchMove)
        }
    }, [setThumbSize])

    // initial load
    useEffect(() => {
        if (items.length === 0) fetchMedia(true)
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    // infinite scroll — stable ref avoids observer thrashing on state changes
    const scrollRef = useRef({ hasMore, loading, fetchMedia })
    useEffect(() => {
        scrollRef.current = { hasMore, loading, fetchMedia }
    }, [hasMore, loading, fetchMedia])

    useEffect(() => {
        const el = sentinelRef.current
        if (!el) return
        const obs = new IntersectionObserver(
            (entries) => {
                const { hasMore, loading, fetchMedia } = scrollRef.current
                if (entries[0].isIntersecting && hasMore && !loading) fetchMedia()
            },
            { rootMargin: "400px" },
        )
        obs.observe(el)
        return () => obs.disconnect()
    }, [])

    // ─── Detail panel state (with history for mobile back) ──
    const [detailId, setDetailIdRaw] = useState<number | null>(null)
    const detailIdRef = useRef(detailId)

    const openDetail = useCallback((id: number) => {
        setDetailIdRaw(id)
        detailIdRef.current = id
        // Push a history entry so mobile back button closes the panel
        window.history.pushState({ mediaDetail: true }, "")
    }, [])

    const closeDetail = useCallback(() => {
        if (detailIdRef.current != null) {
            setDetailIdRaw(null)
            detailIdRef.current = null
            // Pop the history entry we pushed (if we're closing programmatically, not via popstate)
            if (window.history.state?.mediaDetail) {
                window.history.back()
            }
        }
    }, [])

    // Listen for browser back / mobile back gesture
    useEffect(() => {
        const onPopState = () => {
            if (detailIdRef.current != null) {
                setDetailIdRaw(null)
                detailIdRef.current = null
            }
        }
        window.addEventListener("popstate", onPopState)
        return () => window.removeEventListener("popstate", onPopState)
    }, [])

    const currentIndex = useMemo(
        () => (detailId ? items.findIndex((i) => i.id === detailId) : -1),
        [detailId, items],
    )

    // ─── Group by date when sorted by date ────────────────
    const isDateSort = filters.sort === "date_taken"
    const groups = useMemo(() => {
        if (!isDateSort) return null
        return dateGroupMode === "day" ? groupByDay(items) : groupByMonth(items)
    }, [isDateSort, items, dateGroupMode])

    return (
        <div className="pb-20">
            {/* ── Gallery ── */}
            <div ref={galleryRef} className="px-2 sm:px-4 pt-2">
                {error && (
                    <div className="mb-4 rounded-xl bg-destructive/10 p-3 text-sm text-destructive">
                        {error}
                    </div>
                )}

                {!loading && items.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
                        <ImageOff className="h-10 w-10 mb-3 opacity-40" />
                        <p className="text-base font-medium mb-1">No media found</p>
                        <p className="text-sm text-muted-foreground/60 mb-5">Try adjusting your filters</p>
                        <Button variant="secondary" size="sm" className="rounded-xl" onClick={resetFilters}>
                            Clear filters
                        </Button>
                    </div>
                )}

                {groups
                    ? groups.map((group) => (
                        <div key={group.key} className="mb-10" style={{ contentVisibility: 'auto', containIntrinsicSize: 'auto 500px' } as React.CSSProperties}>
                            <div className="flex items-center gap-3 mb-4">
                                <h3 className="text-2xl sm:text-3xl font-bold tracking-tight tabular-nums text-foreground">
                                    {group.label}
                                </h3>
                                <span className="text-xs font-medium text-muted-foreground/40 tabular-nums">
                                    {group.items.length}
                                </span>
                            </div>
                            <GalleryGrid
                                items={group.items}
                                thumbSize={thumbSize}
                                viewMode={viewMode}
                                onSelect={openDetail}
                                selectionMode={selectionMode}
                                selectedIds={selectedIds}
                                onToggleSelect={toggleSelected}
                                onLongPress={enterSelectionMode}
                            />
                        </div>
                    ))
                    : (
                        <GalleryGrid
                            items={items}
                            thumbSize={thumbSize}
                            viewMode={viewMode}
                            onSelect={openDetail}
                            selectionMode={selectionMode}
                            selectedIds={selectedIds}
                            onToggleSelect={toggleSelected}
                            onLongPress={enterSelectionMode}
                        />
                    )}

                <div ref={sentinelRef} className="h-1" />

                {loading && (
                    <div className="flex justify-center py-10">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/40" />
                    </div>
                )}

                {!hasMore && items.length > 0 && !loading && (
                    <div className="py-10 flex justify-center">
                        <span className="text-[10px] text-muted-foreground/30 uppercase tracking-[0.2em]">End</span>
                    </div>
                )}
            </div>

            {/* ── Detail Panel ── */}
            {detailId != null && currentIndex >= 0 && !selectionMode && (
                <MediaDetailPanel
                    items={items}
                    startIndex={currentIndex}
                    onClose={closeDetail}
                    onDelete={(id) => removeItem(id)}
                />
            )}
        </div>
    )
}

// ─── Subcomponents (memoized) ─────────────────────────────

interface GalleryGridProps {
    items: Media[]
    thumbSize: number
    viewMode: "justified" | "grid"
    onSelect: (id: number) => void
    selectionMode: boolean
    selectedIds: Set<number>
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
}

const GalleryGrid = memo(function GalleryGrid({
    items, thumbSize, viewMode, onSelect,
    selectionMode, selectedIds, onToggleSelect, onLongPress,
}: GalleryGridProps) {
    if (viewMode === "grid") {
        return (
            <div
                className="grid gap-1 transition-all"
                style={{
                    gridTemplateColumns: `repeat(auto-fill, minmax(${thumbSize}px, 1fr))`,
                }}
            >
                {items.map((item) => (
                    <SquareTile
                        key={item.id} item={item} onSelect={onSelect}
                        selectionMode={selectionMode}
                        selected={selectedIds.has(item.id)}
                        onToggleSelect={onToggleSelect}
                        onLongPress={onLongPress}
                    />
                ))}
            </div>
        )
    }

    // Justified Layout - calculate rows to fill container width
    return <JustifiedGallery items={items} targetHeight={thumbSize} gap={4} onSelect={onSelect} selectionMode={selectionMode} selectedIds={selectedIds} onToggleSelect={onToggleSelect} onLongPress={onLongPress} />
})

/** Justified gallery that fills each row completely */
const JustifiedGallery = memo(function JustifiedGallery({
    items,
    targetHeight,
    gap,
    onSelect,
    selectionMode,
    selectedIds,
    onToggleSelect,
    onLongPress,
}: {
    items: Media[]
    targetHeight: number
    gap: number
    onSelect: (id: number) => void
    selectionMode: boolean
    selectedIds: Set<number>
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
}) {
    const containerRef = useRef<HTMLDivElement>(null)
    const [containerWidth, setContainerWidth] = useState(0)

    // Measure container width
    useLayoutEffect(() => {
        const el = containerRef.current
        if (!el) return
        const measure = () => setContainerWidth(el.clientWidth)
        measure()
        const obs = new ResizeObserver(measure)
        obs.observe(el)
        return () => obs.disconnect()
    }, [])

    // Build justified rows
    const rows = useMemo(() => {
        if (containerWidth <= 0) return []

        const result: { item: Media; width: number; height: number }[][] = []
        let currentRow: { item: Media; width: number; height: number }[] = []
        let rowWidth = 0

        for (const item of items) {
            const w = item.width && item.width > 0 ? item.width : 4
            const h = item.height && item.height > 0 ? item.height : 3
            const aspect = w / h
            const itemWidth = targetHeight * aspect

            // Check if adding this item would overflow
            const totalGaps = currentRow.length * gap
            if (currentRow.length > 0 && rowWidth + itemWidth + totalGaps > containerWidth) {
                // Finalize current row - scale to fill
                const gapsWidth = (currentRow.length - 1) * gap
                const availableWidth = containerWidth - gapsWidth
                const scale = availableWidth / (rowWidth - gap) // rowWidth includes no gaps yet
                const scaledRow = currentRow.map(r => ({
                    ...r,
                    width: Math.floor(r.width * scale),
                    height: Math.floor(r.height * scale),
                }))
                result.push(scaledRow)
                currentRow = []
                rowWidth = 0
            }

            currentRow.push({ item, width: itemWidth, height: targetHeight })
            rowWidth += itemWidth
        }

        // Last row - don't scale if less than 60% full (keep natural size)
        if (currentRow.length > 0) {
            const gapsWidth = (currentRow.length - 1) * gap
            const fillRatio = (rowWidth + gapsWidth) / containerWidth
            if (fillRatio > 0.6) {
                const availableWidth = containerWidth - gapsWidth
                const scale = availableWidth / rowWidth
                const scaledRow = currentRow.map(r => ({
                    ...r,
                    width: Math.floor(r.width * scale),
                    height: Math.floor(r.height * scale),
                }))
                result.push(scaledRow)
            } else {
                result.push(currentRow)
            }
        }

        return result
    }, [items, containerWidth, targetHeight, gap])

    return (
        <div ref={containerRef} className="w-full">
            {rows.map((row, rowIdx) => (
                <div
                    key={rowIdx}
                    className="flex"
                    style={{ gap, marginBottom: gap, contentVisibility: 'auto', containIntrinsicSize: `auto ${row[0]?.height ?? targetHeight}px` } as React.CSSProperties}
                >
                    {row.map(({ item, width, height }) => (
                        <MediaTile
                            key={item.id}
                            item={item}
                            style={{ width, height }}
                            className="rounded-sm flex-shrink-0"
                            onSelect={onSelect}
                            selectionMode={selectionMode}
                            selected={selectedIds.has(item.id)}
                            onToggleSelect={onToggleSelect}
                            onLongPress={onLongPress}
                        />
                    ))}
                </div>
            ))}
        </div>
    )
})

const SquareTile = memo(function SquareTile({
    item,
    onSelect,
    selectionMode,
    selected,
    onToggleSelect,
    onLongPress,
}: {
    item: Media
    onSelect: (id: number) => void
    selectionMode: boolean
    selected: boolean
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
}) {
    return (
        <MediaTile
            item={item}
            className="aspect-square rounded-md"
            onSelect={onSelect}
            selectionMode={selectionMode}
            selected={selected}
            onToggleSelect={onToggleSelect}
            onLongPress={onLongPress}
        />
    )
})

// ─── Shared media tile with long-press selection ──────────

const LONG_PRESS_MS = 400

const MediaTile = memo(function MediaTile({
    item,
    onSelect,
    selectionMode,
    selected,
    onToggleSelect,
    onLongPress,
    className,
    style,
}: {
    item: Media
    onSelect: (id: number) => void
    selectionMode: boolean
    selected: boolean
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
    className?: string
    style?: React.CSSProperties
}) {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const didLongPress = useRef(false)

    const startPress = useCallback(() => {
        didLongPress.current = false
        timerRef.current = setTimeout(() => {
            didLongPress.current = true
            // Haptic feedback if supported
            navigator?.vibrate?.(30)
            onLongPress(item.id)
        }, LONG_PRESS_MS)
    }, [item.id, onLongPress])

    const cancelPress = useCallback(() => {
        if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null }
    }, [])

    const handleClick = useCallback(() => {
        if (didLongPress.current) return
        if (selectionMode) {
            onToggleSelect(item.id)
        } else {
            onSelect(item.id)
        }
    }, [selectionMode, item.id, onSelect, onToggleSelect])

    return (
        <div
            className={cn("group relative overflow-hidden bg-muted cursor-pointer", className)}
            style={style}
            onClick={handleClick}
            onPointerDown={startPress}
            onPointerUp={cancelPress}
            onPointerLeave={cancelPress}
            onContextMenu={(e) => { e.preventDefault(); onLongPress(item.id) }}
        >
            <AuthImage
                apiSrc={`/media/${item.id}/thumbnail`}
                alt=""
                loading="lazy"
                className={cn(
                    "h-full w-full object-cover transition-all duration-200 will-change-transform",
                    selectionMode && selected && "scale-[0.90] rounded-lg",
                    selectionMode && !selected && "scale-100",
                    !selectionMode && "group-hover:scale-[1.03]",
                )}
            />
            {!selectionMode && <Overlay item={item} />}

            {/* Selection indicator */}
            {selectionMode && (
                <div className={cn(
                    "absolute top-[6%] left-[6%] z-10 h-5 w-5 rounded-full flex items-center justify-center transition-all duration-150",
                    selected
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "border-2 border-white/60 bg-black/20"
                )}>
                    {selected && (
                        <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                        </svg>
                    )}
                </div>
            )}
        </div>
    )
})

const RAW_EXTS = new Set(["CR2", "CR3", "ARW", "NEF", "DNG", "RAF", "ORF", "RW2", "PEF", "SRW", "NRW", "3FR", "IIQ", "ERF", "MEF", "MOS"])

const Overlay = memo(function Overlay({ item }: { item: Media }) {
    const ext = item.extension?.replace(/^\./, "").toUpperCase() || ""
    const isRaw = RAW_EXTS.has(ext)
    return (
        <>
            {/* Single hover overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none will-change-[opacity]">
                <div className="absolute bottom-0 left-0 right-0 p-2 flex items-end justify-between gap-2">
                    <div className="flex flex-col gap-0.5 min-w-0">
                        {item.date_taken && (
                            <span className="text-[11px] text-white/90 font-medium">
                                {fmtDateShort(item.date_taken)}
                            </span>
                        )}
                        {item.camera_model && (
                            <span className="text-[10px] text-white/50 truncate">
                                {item.camera_model}
                            </span>
                        )}
                    </div>
                    {(item.rating ?? 0) > 0 && (
                        <StarRating value={item.rating} size={10} />
                    )}
                </div>
            </div>

            {/* Always-visible badges */}
            {isRaw && (
                <div className="absolute top-1.5 right-1.5">
                    <span className="inline-flex items-center rounded bg-black/50 px-1.5 py-0.5 text-[9px] text-white/70 font-bold tracking-wider">
                        RAW
                    </span>
                </div>
            )}
            {item.media_type === "video" && (
                <div className="absolute top-1.5 left-1.5">
                    <span className="inline-flex items-center gap-0.5 rounded bg-black/50 px-1.5 py-0.5 text-[10px] text-white font-medium">
                        <Film className="h-2.5 w-2.5" />
                        {fmtDuration(item.duration) ?? "Video"}
                    </span>
                </div>
            )}
        </>
    )
})
