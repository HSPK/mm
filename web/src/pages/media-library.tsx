import { useEffect, useRef, useMemo, useCallback, useState } from "react"
import { ImageOff } from "lucide-react"
import { useMediaQueryStore } from "@/stores/media-query"
import { useSelectionStore } from "@/stores/media-selection"
import { useViewPrefsStore } from "@/stores/view-prefs"
import { EmptyState } from "@/components/ui/empty-state"
import { Spinner } from "@/components/ui/spinner"
import { GalleryGrid } from "@/components/gallery"
import { MediaGridSkeleton } from "@/components/gallery/media-grid-skeleton"
import { MediaDetailPanel } from "@/components/media-detail"
import { useDetailPanel } from "@/hooks/use-detail-panel"
import { useInfiniteScroll } from "@/hooks/use-infinite-scroll"
import { usePinchZoom } from "@/hooks/use-pinch-zoom"
import { groupByDay, groupByMonth } from "@/lib/format"

export default function MediaLibraryPage() {
    const {
        items, total, loading, hasMore, error,
        filters, fetchMedia, resetFilters,
        removeItem,
    } = useMediaQueryStore()
    const { viewMode, dateGroupMode, thumbSize, setThumbSize } = useViewPrefsStore()
    const {
        selectionMode, selectedIds,
        enterSelectionMode, toggleSelected,
    } = useSelectionStore()

    const sentinelRef = useRef<HTMLDivElement>(null)
    const galleryRef = useRef<HTMLDivElement>(null)
    const [retainedDetailId, setRetainedDetailId] = useState<number | null>(null)
    const [detailDirty, setDetailDirty] = useState(false)

    usePinchZoom(galleryRef, thumbSize, setThumbSize)

    // initial load
    useEffect(() => {
        if (items.length === 0) fetchMedia(true)
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    useInfiniteScroll(sentinelRef, hasMore, loading, fetchMedia)

    const {
        detailId,
        currentIndex,
        openDetail,
        closeDetail,
        closeDetailForNavigation,
        setActiveDetail,
    } = useDetailPanel(items)

    const loadMoreDetail = useCallback(() => fetchMedia(), [fetchMedia])
    const closeDetailWithHistory = useCallback(() => closeDetail(), [closeDetail])

    useEffect(() => {
        if (detailId == null || currentIndex >= 0 || loading) return
        if (hasMore) {
            void fetchMedia()
            return
        }
        void closeDetailForNavigation()
    }, [closeDetailForNavigation, currentIndex, detailId, fetchMedia, hasMore, loading])

    const handleOpenDetail = useCallback((id: number) => {
        setRetainedDetailId(id)
        openDetail(id)
    }, [openDetail])
    const handleActiveDetail = useCallback((id: number) => {
        setRetainedDetailId(id)
        setActiveDetail(id)
    }, [setActiveDetail])
    const handleDetailDirtyChange = useCallback((dirty: boolean) => {
        setDetailDirty(dirty)
        if (dirty && detailId != null) setRetainedDetailId(detailId)
        if (!dirty && detailId == null) setRetainedDetailId(null)
    }, [detailId])

    const renderDetailId = detailId ?? (detailDirty ? retainedDetailId : null)
    const panelIndex = useMemo(
        () => (renderDetailId != null ? items.findIndex((item) => item.id === renderDetailId) : -1),
        [items, renderDetailId],
    )
    const keepEditingAfterBlockedClose = useCallback(() => {
        if (retainedDetailId != null) setActiveDetail(retainedDetailId)
    }, [retainedDetailId, setActiveDetail])
    const discardBlockedClose = useCallback(() => {
        setDetailDirty(false)
        setRetainedDetailId(null)
    }, [])

    const handleDetailDelete = useCallback((id: number) => {
        removeItem(id)
        if (!filters.deleted) return
        if (total - 1 <= 0) {
            resetFilters()
        } else if (items.length <= 1) {
            void fetchMedia(true)
        }
    }, [fetchMedia, filters.deleted, items.length, removeItem, resetFilters, total])

    // ─── Group by date when sorted by date ────────────────
    const isDateSort = filters.sort === "date_taken"
    const groups = useMemo(() => {
        if (!isDateSort) return null
        return dateGroupMode === "day" ? groupByDay(items) : groupByMonth(items)
    }, [isDateSort, items, dateGroupMode])

    return (
        <div className="pb-20">
            <div ref={galleryRef} className="px-2 sm:px-4 pt-2">
                {error && (
                    <div className="mb-4 rounded-xl bg-destructive/10 p-3 text-sm text-destructive">
                        {error}
                    </div>
                )}

                {loading && items.length === 0 && (
                    <MediaGridSkeleton />
                )}

                {!loading && items.length === 0 && (
                    <EmptyState
                        icon={ImageOff}
                        title="No media found"
                        description="Try adjusting your filters or import new media."
                        action={{ label: "Clear filters", onClick: resetFilters }}
                    />
                )}

                {groups
                    ? groups.map((group) => (
                        <div key={group.key} className="mb-10" style={{ contentVisibility: "auto", containIntrinsicSize: "auto 500px" } as React.CSSProperties}>
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
                                onSelect={handleOpenDetail}
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
                            onSelect={handleOpenDetail}
                            selectionMode={selectionMode}
                            selectedIds={selectedIds}
                            onToggleSelect={toggleSelected}
                            onLongPress={enterSelectionMode}
                        />
                    )}

                <div ref={sentinelRef} className="h-1" />

                {loading && items.length > 0 && (
                    <div className="flex justify-center py-10">
                        <Spinner size="md" className="text-muted-foreground/40" />
                    </div>
                )}

                {!hasMore && items.length > 0 && !loading && (
                    <div className="py-10 flex justify-center">
                        <span className="text-[10px] text-muted-foreground/30 uppercase tracking-[0.2em]">End</span>
                    </div>
                )}
            </div>

            {/* ── Detail Panel ── */}
            {renderDetailId != null && panelIndex >= 0 && !selectionMode && (
                <MediaDetailPanel
                    items={items}
                    startIndex={panelIndex}
                    onClose={closeDetailWithHistory}
                    onDelete={handleDetailDelete}
                    onActiveChange={handleActiveDetail}
                    onNavigateAway={closeDetailForNavigation}
                    onDirtyChange={handleDetailDirtyChange}
                    externalCloseRequested={detailId == null && detailDirty && retainedDetailId != null}
                    onKeepEditing={keepEditingAfterBlockedClose}
                    onDiscardClose={discardBlockedClose}
                    onLoadMore={loadMoreDetail}
                    hasMore={hasMore}
                    loadingMore={loading}
                    inTrash={!!filters.deleted}
                />
            )}
        </div>
    )
}
