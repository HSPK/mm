import { useCallback, useEffect, useMemo, useState } from "react"
import type { Media } from "@/api/types"

export interface UseMediaViewerNavigationOpts {
    items: Media[]
    startIndex: number
    onClose: () => void
    onActiveChange?: (id: number) => void
    onLoadMore?: () => Promise<void>
    hasMore: boolean
    loadingMore: boolean
    notify: (message: string) => void
    /** Called when the currently-active id is no longer in `items`. */
    onActiveLost?: () => void
}

export interface MediaViewerNavigation {
    activeMediaId: number | null
    displayMediaId: number | null
    currentIndex: number
    displayIndex: number
    currentItem: Media | undefined
    displayItem: Media | undefined
    pendingNext: boolean
    requestingMore: boolean
    setActiveMediaId: (id: number | null) => void
    setDisplayMediaId: (id: number | null) => void
    goPrev: () => void
    goNext: () => void
    loadMoreForNext: () => Promise<void>
}

/**
 * Owns the navigation state machine for the media viewer: active/display ids,
 * bounds checking, swipe-driven prev/next, and lazy-loading when nearing the
 * tail of the list. The display id is set by the caller (panel) after the
 * image has actually loaded so the transition feels seamless.
 */
export function useMediaViewerNavigation(opts: UseMediaViewerNavigationOpts): MediaViewerNavigation {
    const { items, startIndex, onClose, onActiveChange, onLoadMore, hasMore, loadingMore, notify, onActiveLost } = opts

    const initialMediaId = items[startIndex]?.id ?? null
    const [activeMediaId, setActiveMediaId] = useState<number | null>(initialMediaId)
    const [displayMediaId, setDisplayMediaId] = useState<number | null>(initialMediaId)
    const [pendingNext, setPendingNext] = useState(false)
    const [requestingMore, setRequestingMore] = useState(false)

    const currentIndex = useMemo(
        () => (activeMediaId != null ? items.findIndex((item) => item.id === activeMediaId) : -1),
        [activeMediaId, items],
    )
    const displayIndex = useMemo(
        () => (displayMediaId != null ? items.findIndex((item) => item.id === displayMediaId) : -1),
        [displayMediaId, items],
    )
    const currentItem = currentIndex >= 0 ? items[currentIndex] : undefined
    const displayItem = displayIndex >= 0 ? items[displayIndex] : currentItem

    // Bounds check: snap activeId back into range, or close if empty.
    useEffect(() => {
        if (items.length === 0) {
            onClose()
            return
        }
        if (activeMediaId != null && currentIndex < 0) {
            onActiveLost?.()
            return
        }
        if (currentIndex >= items.length) {
            setActiveMediaId(items[items.length - 1].id)
        }
    }, [activeMediaId, currentIndex, items, onActiveLost, onClose])

    // Sync to a new external startIndex.
    useEffect(() => {
        const target = items[startIndex]
        if (target && activeMediaId !== target.id) {
            setActiveMediaId(target.id)
            if (displayMediaId == null) setDisplayMediaId(target.id)
        }
    }, [activeMediaId, displayMediaId, items, startIndex])

    const navigateTo = useCallback((nextIndex: number) => {
        if (nextIndex === currentIndex || nextIndex < 0 || nextIndex >= items.length) return
        const nextId = items[nextIndex].id
        setActiveMediaId(nextId)
        onActiveChange?.(nextId)
    }, [currentIndex, items, onActiveChange])

    const loadMoreForNext = useCallback(async () => {
        if (!onLoadMore || !hasMore || loadingMore || requestingMore) {
            if (!hasMore) notify("End of library")
            return
        }
        setPendingNext(true)
        setRequestingMore(true)
        try {
            await onLoadMore()
        } catch {
            setPendingNext(false)
            notify("Could not load more media")
        } finally {
            setRequestingMore(false)
        }
    }, [hasMore, loadingMore, notify, onLoadMore, requestingMore])

    const goPrev = useCallback(() => navigateTo(currentIndex - 1), [navigateTo, currentIndex])
    const goNext = useCallback(() => {
        if (currentIndex < items.length - 1) {
            navigateTo(currentIndex + 1)
            return
        }
        void loadMoreForNext()
    }, [currentIndex, items.length, loadMoreForNext, navigateTo])

    // After a "next" trigger, advance once items grow — or surface end-of-library.
    useEffect(() => {
        if (!pendingNext) return
        if (currentIndex < items.length - 1) {
            setPendingNext(false)
            navigateTo(currentIndex + 1)
        } else if (!hasMore && !loadingMore && !requestingMore) {
            setPendingNext(false)
            notify("End of library")
        }
    }, [currentIndex, hasMore, items.length, loadingMore, navigateTo, notify, pendingNext, requestingMore])

    // Eager prefetch when nearing the tail.
    useEffect(() => {
        if (currentIndex < items.length - 4 || !hasMore || loadingMore || requestingMore || !onLoadMore) {
            return
        }
        setRequestingMore(true)
        onLoadMore()
            .catch(() => notify("Could not load more media"))
            .finally(() => setRequestingMore(false))
    }, [currentIndex, hasMore, items.length, loadingMore, notify, onLoadMore, requestingMore])

    return {
        activeMediaId,
        displayMediaId,
        currentIndex,
        displayIndex,
        currentItem,
        displayItem,
        pendingNext,
        requestingMore,
        setActiveMediaId,
        setDisplayMediaId,
        goPrev,
        goNext,
        loadMoreForNext,
    }
}
