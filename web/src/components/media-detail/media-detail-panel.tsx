import { useState, useCallback, useEffect, useMemo, useRef, type MouseEvent, type TouchEvent } from "react"
import { createPortal } from "react-dom"
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch"

import { api } from "@/api/client"
import type { Media } from "@/api/types"
import {
    ChevronLeft,
    Info,
    Download,
    Trash2,
    Pencil,
    Loader2,
    AlertTriangle,
    ChevronRight,
} from "lucide-react"
import { canDisplayOriginalImage, getMediaSrc, getThumbnailSrc, getImageSrc } from "@/lib/media-url"
import { trapFocus } from "@/lib/focus"
import { InfoDialog } from "./info-dialog"

// ─── Main Component ────────────────────────────────────────

function addBoundedId(prev: Set<number>, id: number, limit = 32) {
    if (prev.has(id)) return prev
    const next = new Set(prev)
    next.add(id)
    while (next.size > limit) {
        const oldest = next.values().next().value
        if (oldest === undefined) break
        next.delete(oldest)
    }
    return next
}

interface Props {
    items: Media[]
    startIndex: number
    onClose: () => void
    onDelete?: (id: number) => void
    onActiveChange?: (id: number) => void
    onNavigateAway?: () => void | Promise<void>
    onDirtyChange?: (dirty: boolean) => void
    externalCloseRequested?: boolean
    onKeepEditing?: () => void
    onDiscardClose?: () => void
    onLoadMore?: () => Promise<void>
    hasMore?: boolean
    loadingMore?: boolean
    inTrash?: boolean
}

export function MediaDetailPanel({
    items,
    startIndex,
    onClose,
    onDelete,
    onActiveChange,
    onNavigateAway,
    onDirtyChange,
    externalCloseRequested = false,
    onKeepEditing,
    onDiscardClose,
    onLoadMore,
    hasMore = false,
    loadingMore = false,
    inTrash = false,
}: Props) {
    const initialMediaId = items[startIndex]?.id ?? null
    const [showInfo, setShowInfo] = useState(false)
    const [initialEditMode, setInitialEditMode] = useState(false)
    const [activeMediaId, setActiveMediaId] = useState<number | null>(initialMediaId)
    const [displayMediaId, setDisplayMediaId] = useState<number | null>(initialMediaId)
    const [deleting, setDeleting] = useState(false)
    const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
    const [downloading, setDownloading] = useState(false)
    const [loadedMediaIds, setLoadedMediaIds] = useState<Set<number>>(() => new Set())
    const [originalLoadedIds, setOriginalLoadedIds] = useState<Set<number>>(() => new Set())
    const [originalFailedIds, setOriginalFailedIds] = useState<Set<number>>(() => new Set())
    const [mediaError, setMediaError] = useState<{ id: number; message: string } | null>(null)
    const [notice, setNotice] = useState<string | null>(null)
    const [chromeVisible, setChromeVisible] = useState(true)
    const [pendingNext, setPendingNext] = useState(false)
    const [requestingMore, setRequestingMore] = useState(false)
    const panelRef = useRef<HTMLDivElement>(null)
    const deleteDialogRef = useRef<HTMLDivElement>(null)
    const deleteCancelRef = useRef<HTMLButtonElement>(null)
    const previousFocusRef = useRef<HTMLElement | null>(null)
    const settleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const revealFramesRef = useRef<Map<number, number[]>>(new Map())
    const touchRef = useRef<{ x: number; y: number; time: number } | null>(null)
    const lastSwipeAtRef = useRef(0)
    const scaleRef = useRef(1)
    const activeMediaIdRef = useRef(activeMediaId)

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
    const isVideo = currentItem?.media_type === "video"
    const currentMediaId = currentItem?.id ?? null
    const mediaLoaded = currentMediaId != null && loadedMediaIds.has(currentMediaId)
    const mediaErrorMessage = mediaError?.id === currentMediaId ? mediaError.message : null
    const showPreviousImage = Boolean(
        currentItem
        && displayItem
        && currentItem.media_type !== "video"
        && displayItem.media_type !== "video"
        && displayItem.id !== currentItem.id,
    )
    const controlsVisible = isVideo || showInfo || confirmDeleteOpen || chromeVisible
    const controlsVisibilityClass = controlsVisible ? "opacity-100" : "pointer-events-none opacity-0"

    const getBestImageSrc = useCallback((item: Media) => (
        canDisplayOriginalImage(item) && originalLoadedIds.has(item.id)
            ? getMediaSrc(item.id)
            : getImageSrc(item)
    ), [originalLoadedIds])

    const currentImageSrc = currentItem && !isVideo ? getBestImageSrc(currentItem) : ""
    const shouldLoadOriginalImage = Boolean(
        currentItem
        && !isVideo
        && mediaLoaded
        && canDisplayOriginalImage(currentItem)
        && !originalLoadedIds.has(currentItem.id)
        && !originalFailedIds.has(currentItem.id),
    )

    const clearRevealFrames = useCallback((id?: number) => {
        if (id != null) {
            const frames = revealFramesRef.current.get(id) ?? []
            for (const frame of frames) window.cancelAnimationFrame(frame)
            revealFramesRef.current.delete(id)
            return
        }
        for (const frames of revealFramesRef.current.values()) {
            for (const frame of frames) window.cancelAnimationFrame(frame)
        }
        revealFramesRef.current.clear()
    }, [])

    const markMediaLoaded = useCallback((id: number) => {
        clearRevealFrames(id)
        const first = window.requestAnimationFrame(() => {
            const second = window.requestAnimationFrame(() => {
                setLoadedMediaIds((prev) => {
                    if (prev.has(id)) return prev
                    return addBoundedId(prev, id)
                })
                setMediaError((prev) => (prev?.id === id ? null : prev))
                revealFramesRef.current.delete(id)
            })
            revealFramesRef.current.set(id, [second])
        })
        revealFramesRef.current.set(id, [first])
    }, [clearRevealFrames])

    const markMediaError = useCallback((id: number, message: string) => {
        if (activeMediaIdRef.current !== id) return
        clearRevealFrames(id)
        setMediaError({ id, message })
    }, [clearRevealFrames])

    const markOriginalLoaded = useCallback((id: number) => {
        setOriginalLoadedIds((prev) => addBoundedId(prev, id))
    }, [])

    const markOriginalUnavailable = useCallback((id: number) => {
        setOriginalFailedIds((prev) => addBoundedId(prev, id))
    }, [])

    useEffect(() => {
        activeMediaIdRef.current = activeMediaId
    }, [activeMediaId])

    useEffect(() => {
        if (settleTimerRef.current) {
            window.clearTimeout(settleTimerRef.current)
            settleTimerRef.current = null
        }
        if (!currentItem) return
        if (currentItem.media_type === "video") {
            setDisplayMediaId(currentItem.id)
            return
        }
        if (!loadedMediaIds.has(currentItem.id)) return
        if (displayMediaId === currentItem.id) return

        settleTimerRef.current = window.setTimeout(() => {
            if (activeMediaIdRef.current === currentItem.id) {
                setDisplayMediaId(currentItem.id)
            }
            settleTimerRef.current = null
        }, 320)

        return () => {
            if (settleTimerRef.current) {
                window.clearTimeout(settleTimerRef.current)
                settleTimerRef.current = null
            }
        }
    }, [currentItem, displayMediaId, loadedMediaIds])

    useEffect(() => {
        if (items.length === 0) {
            onClose()
            return
        }
        if (currentIndex >= items.length) {
            setActiveMediaId(items[items.length - 1].id)
        }
    }, [currentIndex, items, onClose])

    useEffect(() => {
        const target = items[startIndex]
        if (target && activeMediaId !== target.id) {
            setActiveMediaId(target.id)
            if (displayMediaId == null) setDisplayMediaId(target.id)
        }
    }, [activeMediaId, displayMediaId, items, startIndex])

    useEffect(() => {
        scaleRef.current = 1
        if (currentMediaId == null) {
            clearRevealFrames()
        } else {
            for (const id of Array.from(revealFramesRef.current.keys())) {
                if (id !== currentMediaId) clearRevealFrames(id)
            }
        }
        setMediaError(null)
        setNotice(null)
        setConfirmDeleteOpen(false)
        setChromeVisible(true)
    }, [clearRevealFrames, currentMediaId])

    useEffect(() => {
        if (!notice) return
        const t = window.setTimeout(() => setNotice(null), 2600)
        return () => window.clearTimeout(t)
    }, [notice])

    const openInfo = (edit = false) => {
        setInitialEditMode(edit)
        setShowInfo(true)
    }

    const navigateTo = useCallback((nextIndex: number) => {
        if (nextIndex === currentIndex || nextIndex < 0 || nextIndex >= items.length) return
        const nextId = items[nextIndex].id
        setActiveMediaId(nextId)
        onActiveChange?.(nextId)
    }, [currentIndex, items, onActiveChange])

    const loadMoreForNext = useCallback(async () => {
        if (!onLoadMore || !hasMore || loadingMore || requestingMore) {
            if (!hasMore) setNotice("End of library")
            return
        }
        setPendingNext(true)
        setRequestingMore(true)
        try {
            await onLoadMore()
        } catch {
            setPendingNext(false)
            setNotice("Could not load more media")
        } finally {
            setRequestingMore(false)
        }
    }, [hasMore, loadingMore, onLoadMore, requestingMore])

    const goPrev = useCallback(() => navigateTo(currentIndex - 1), [navigateTo, currentIndex])
    const goNext = useCallback(() => {
        if (currentIndex < items.length - 1) {
            navigateTo(currentIndex + 1)
            return
        }
        void loadMoreForNext()
    }, [currentIndex, items.length, loadMoreForNext, navigateTo])

    useEffect(() => {
        if (!pendingNext) return
        if (currentIndex < items.length - 1) {
            setPendingNext(false)
            navigateTo(currentIndex + 1)
        } else if (!hasMore && !loadingMore && !requestingMore) {
            setPendingNext(false)
            setNotice("End of library")
        }
    }, [currentIndex, hasMore, items.length, loadingMore, navigateTo, pendingNext, requestingMore])

    useEffect(() => {
        if (currentIndex < items.length - 4 || !hasMore || loadingMore || requestingMore || !onLoadMore) {
            return
        }
        setRequestingMore(true)
        onLoadMore()
            .catch(() => setNotice("Could not load more media"))
            .finally(() => setRequestingMore(false))
    }, [currentIndex, hasMore, items.length, loadingMore, onLoadMore, requestingMore])

    useEffect(() => {
        const preload = [currentIndex - 1, currentIndex + 1, currentIndex + 2]
            .filter((idx) => idx >= 0 && idx < items.length)
            .map((idx) => items[idx])
            .filter((item) => item.media_type !== "video")
        const images = preload.flatMap((item) => [
            getThumbnailSrc(item.id),
            getImageSrc(item),
        ]).map((src) => {
            const img = new Image()
            img.crossOrigin = "use-credentials"
            img.src = src
            return img
        })
        return () => {
            for (const img of images) img.src = ""
        }
    }, [currentIndex, items])

    // Keyboard navigation
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (showInfo) return
            if (confirmDeleteOpen) {
                if (e.key === "Escape" && !deleting) {
                    setConfirmDeleteOpen(false)
                    return
                }
                if (e.key === "Tab") {
                    trapFocus(e, deleteDialogRef.current)
                }
                return
            }
            if (e.key === "Tab") {
                trapFocus(e, panelRef.current)
                return
            }
            if (e.key === "ArrowLeft") goPrev()
            else if (e.key === "ArrowRight") goNext()
            else if (e.key === "Escape") onClose()
        }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
    }, [confirmDeleteOpen, deleting, goPrev, goNext, onClose, showInfo])

    // Prevent body scroll
    useEffect(() => {
        const prev = document.body.style.overflow
        document.body.style.overflow = "hidden"
        return () => { document.body.style.overflow = prev }
    }, [])

    useEffect(() => {
        previousFocusRef.current = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null
        const frame = window.requestAnimationFrame(() => {
            panelRef.current?.focus()
        })
        return () => {
            window.cancelAnimationFrame(frame)
            previousFocusRef.current?.focus()
            previousFocusRef.current = null
        }
    }, [])

    useEffect(() => {
        if (!confirmDeleteOpen) return
        const frame = window.requestAnimationFrame(() => {
            deleteCancelRef.current?.focus()
        })
        return () => window.cancelAnimationFrame(frame)
    }, [confirmDeleteOpen])

    useEffect(() => {
        return () => {
            if (settleTimerRef.current) window.clearTimeout(settleTimerRef.current)
            clearRevealFrames()
        }
    }, [clearRevealFrames])

    const handleDownload = async () => {
        if (!currentItem || downloading) return
        setDownloading(true)
        try {
            const resp = await api.get(`/media/${currentItem.id}/file`, { responseType: "blob" })
            const url = URL.createObjectURL(resp.data)
            const a = document.createElement("a")
            a.href = url
            a.download = currentItem.filename
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        } catch {
            setNotice("Download failed")
        } finally {
            setDownloading(false)
        }
    }

    const handleDelete = () => {
        if (!currentItem || deleting) return
        setChromeVisible(true)
        setConfirmDeleteOpen(true)
    }

    const confirmDelete = async () => {
        if (!currentItem || deleting) return
        setDeleting(true)
        try {
            const fallbackItem = currentIndex < items.length - 1
                ? items[currentIndex + 1]
                : items[currentIndex - 1]
            await api.delete(`/media/${currentItem.id}`, inTrash ? { params: { permanent: true } } : undefined)
            setConfirmDeleteOpen(false)
            if (!fallbackItem) {
                onDelete?.(currentItem.id)
                onClose()
            } else {
                onActiveChange?.(fallbackItem.id)
                setActiveMediaId(fallbackItem.id)
                if (fallbackItem.media_type === "video") setDisplayMediaId(fallbackItem.id)
                onDelete?.(currentItem.id)
            }
        } catch {
            setConfirmDeleteOpen(false)
            setNotice("Delete failed")
        } finally {
            setDeleting(false)
        }
    }

    const handleTouchStart = useCallback((e: TouchEvent) => {
        if (showInfo || isVideo || e.touches.length !== 1 || scaleRef.current > 1.02) {
            touchRef.current = null
            return
        }
        const t = e.touches[0]
        touchRef.current = { x: t.clientX, y: t.clientY, time: Date.now() }
    }, [isVideo, showInfo])

    const handleTouchEnd = useCallback((e: TouchEvent) => {
        const start = touchRef.current
        touchRef.current = null
        if (!start || isVideo || e.changedTouches.length === 0 || scaleRef.current > 1.02) return
        const t = e.changedTouches[0]
        const dx = t.clientX - start.x
        const dy = t.clientY - start.y
        const elapsed = Math.max(1, Date.now() - start.time)
        const velocity = Math.abs(dx) / elapsed
        if (Math.abs(dx) < 56 || Math.abs(dx) < Math.abs(dy) * 1.35 || velocity < 0.22) return
        lastSwipeAtRef.current = Date.now()
        if (dx > 0) goPrev()
        else goNext()
    }, [goNext, goPrev, isVideo])

    const handleMediaClick = useCallback((e: MouseEvent<HTMLDivElement>) => {
        if (isVideo || showInfo || confirmDeleteOpen || Date.now() - lastSwipeAtRef.current < 350) return
        if (e.target instanceof HTMLElement && e.target.closest("button, video, input, textarea, select, a")) return
        setChromeVisible((visible) => !visible)
    }, [confirmDeleteOpen, isVideo, showInfo])

    const actionBtnClass = (active = false) =>
        `flex items-center justify-center w-10 h-10 rounded-full transition-all duration-100 active:scale-90 ${active
            ? "text-white bg-white/20"
            : "text-white/70 hover:text-white hover:bg-white/10"
        }`

    if (!currentItem) return null

    return createPortal(
        <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label={currentItem.media_type === "video" ? "Video viewer" : "Photo viewer"}
            tabIndex={-1}
            className="fixed inset-0 z-[9999] flex flex-col bg-black select-none"
            onTouchStart={(e) => e.stopPropagation()}
            onTouchMove={(e) => e.stopPropagation()}
            onTouchEnd={(e) => e.stopPropagation()}
        >
            {/* ── Top bar ── */}
            <div
                className={`absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-3 pb-3 transition-opacity duration-200 ${controlsVisibilityClass}`}
                aria-hidden={!controlsVisible}
                inert={controlsVisible ? undefined : true}
                style={{
                    paddingTop: "max(env(safe-area-inset-top, 0px), 12px)",
                    background: "linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.25) 60%, transparent 100%)",
                }}
            >
                <button
                    type="button"
                    onClick={onClose}
                    className="flex items-center justify-center w-10 h-10 rounded-full text-white/80 hover:text-white hover:bg-white/10 active:scale-90 transition-all duration-100"
                    aria-label="Back"
                >
                    <ChevronLeft className="h-6 w-6" />
                </button>

                <div className="flex items-center gap-1">
                    <button type="button" onClick={() => openInfo(false)} className={actionBtnClass(showInfo && !initialEditMode)} aria-label="Info">
                        <Info className="h-[1.2rem] w-[1.2rem]" strokeWidth={showInfo && !initialEditMode ? 2.2 : 1.8} />
                    </button>
                    <button type="button" onClick={() => openInfo(true)} className={actionBtnClass(showInfo && initialEditMode)} aria-label="Edit">
                        <Pencil className="h-[1.2rem] w-[1.2rem]" strokeWidth={showInfo && initialEditMode ? 2.2 : 1.8} />
                    </button>
                    <button type="button" onClick={handleDownload} className={actionBtnClass()} aria-label="Download" disabled={downloading}>
                        {downloading
                            ? <Loader2 className="h-[1.2rem] w-[1.2rem] animate-spin" strokeWidth={1.8} />
                            : <Download className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />}
                    </button>
                    <button type="button" onClick={handleDelete} className={actionBtnClass()} aria-label={inTrash ? "Delete permanently" : "Move to trash"} disabled={deleting}>
                        {deleting
                            ? <Loader2 className="h-[1.2rem] w-[1.2rem] animate-spin" strokeWidth={1.8} />
                            : <Trash2 className="h-[1.2rem] w-[1.2rem]" strokeWidth={1.8} />}
                    </button>
                </div>
            </div>

            {/* ── Media area ── */}
            <div
                className={`flex-1 relative overflow-hidden ${isVideo ? "touch-auto" : "touch-none"}`}
                onClick={handleMediaClick}
                onTouchStart={handleTouchStart}
                onTouchEnd={handleTouchEnd}
            >
                {isVideo ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        {!mediaLoaded && !mediaErrorMessage && (
                            <Loader2 className="absolute z-10 h-6 w-6 animate-spin text-white/35" />
                        )}
                        {mediaErrorMessage && (
                            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 text-white/70">
                                <AlertTriangle className="h-7 w-7 text-white/45" />
                                <span className="text-sm">{mediaErrorMessage}</span>
                            </div>
                        )}
                        <video
                            key={currentItem.id}
                            src={getMediaSrc(currentItem.id)}
                            poster={getThumbnailSrc(currentItem.id, "xl")}
                            controls
                            playsInline
                            preload="metadata"
                            crossOrigin="use-credentials"
                            onLoadedData={() => markMediaLoaded(currentItem.id)}
                            onError={() => markMediaError(currentItem.id, "Could not load video")}
                            className="max-w-full max-h-full object-contain"
                        />
                    </div>
                ) : (
                    <div className="absolute inset-0">
                        {showPreviousImage && displayItem && !mediaErrorMessage && (
                            <img
                                key={`previous-${displayItem.id}`}
                                src={getBestImageSrc(displayItem)}
                                alt=""
                                crossOrigin="use-credentials"
                                draggable={false}
                                className="pointer-events-none absolute inset-0 h-full w-full object-contain"
                            />
                        )}
                        {!mediaLoaded && !mediaErrorMessage && (
                            <>
                                {!showPreviousImage && (
                                    <img
                                        src={getThumbnailSrc(currentItem.id)}
                                        alt=""
                                        crossOrigin="use-credentials"
                                        className="absolute inset-0 h-full w-full scale-105 animate-pulse object-contain opacity-30 blur-2xl"
                                        draggable={false}
                                    />
                                )}
                                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3">
                                    <Loader2 className="h-6 w-6 animate-spin text-white/35" />
                                    <span className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-white/45 backdrop-blur-md">
                                        Loading
                                    </span>
                                </div>
                            </>
                        )}
                        {mediaErrorMessage && (
                            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 text-white/70">
                                <AlertTriangle className="h-7 w-7 text-white/45" />
                                <span className="text-sm">{mediaErrorMessage}</span>
                            </div>
                        )}
                        <div
                            className={`absolute inset-0 transition-opacity duration-300 ease-out ${mediaLoaded && !mediaErrorMessage
                                ? "opacity-100"
                                : "pointer-events-none opacity-0"
                            }`}
                        >
                            <TransformWrapper
                                key={currentItem.id}
                                initialScale={1}
                                minScale={1}
                                maxScale={10}
                                centerOnInit
                                limitToBounds
                                wheel={{ step: 0.06 }}
                                pinch={{ disabled: false }}
                                doubleClick={{ mode: "toggle", step: 3 }}
                                panning={{ velocityDisabled: false }}
                                onTransformed={(ref) => {
                                    scaleRef.current = ref.state.scale
                                }}
                            >
                                <TransformComponent
                                    wrapperStyle={{ width: "100%", height: "100%" }}
                                    contentStyle={{
                                        width: "100%",
                                        height: "100%",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                    }}
                                >
                                     <img
                                        src={currentImageSrc}
                                        alt={currentItem.filename}
                                        crossOrigin="use-credentials"
                                        draggable={false}
                                        onLoad={() => markMediaLoaded(currentItem.id)}
                                        onError={() => markMediaError(currentItem.id, "Could not load photo")}
                                        style={{
                                            maxWidth: "100vw",
                                            maxHeight: "100vh",
                                            objectFit: "contain",
                                            userSelect: "none",
                                            WebkitUserSelect: "none",
                                        }}
                                     />
                                 </TransformComponent>
                             </TransformWrapper>
                            {shouldLoadOriginalImage && (
                                <img
                                    src={getMediaSrc(currentItem.id)}
                                    alt=""
                                    crossOrigin="use-credentials"
                                    draggable={false}
                                    onLoad={() => markOriginalLoaded(currentItem.id)}
                                    onError={() => markOriginalUnavailable(currentItem.id)}
                                    className="pointer-events-none absolute h-px w-px opacity-0"
                                />
                            )}
                        </div>
                    </div>
                )}

                <button
                    type="button"
                    onClick={goPrev}
                    disabled={!controlsVisible || currentIndex <= 0}
                    className={`hidden sm:flex absolute left-4 top-1/2 z-20 h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/30 text-white/70 backdrop-blur-md transition hover:bg-black/45 hover:text-white disabled:pointer-events-none disabled:opacity-0 ${controlsVisibilityClass}`}
                    aria-hidden={!controlsVisible}
                    aria-label="Previous media"
                >
                    <ChevronLeft className="h-6 w-6" />
                </button>
                <button
                    type="button"
                    onClick={goNext}
                    disabled={!controlsVisible || (currentIndex >= items.length - 1 && !hasMore)}
                    className={`hidden sm:flex absolute right-4 top-1/2 z-20 h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/30 text-white/70 backdrop-blur-md transition hover:bg-black/45 hover:text-white disabled:pointer-events-none disabled:opacity-0 ${controlsVisibilityClass}`}
                    aria-hidden={!controlsVisible}
                    aria-label="Next media"
                >
                    {requestingMore || loadingMore
                        ? <Loader2 className="h-5 w-5 animate-spin" />
                        : <ChevronRight className="h-6 w-6" />}
                </button>

                <div
                    className={`pointer-events-none absolute bottom-0 left-0 right-0 z-10 px-4 pb-5 pt-16 text-center transition-opacity duration-200 ${controlsVisibilityClass}`}
                    style={{
                        paddingBottom: "max(env(safe-area-inset-bottom, 0px), 20px)",
                        background: "linear-gradient(to top, rgba(0,0,0,0.46) 0%, transparent 100%)",
                    }}
                >
                    <div className="mx-auto max-w-[80vw] truncate text-xs font-medium text-white/75">
                        {currentItem.filename}
                    </div>
                    <div className="mt-1 text-[10px] uppercase tracking-[0.2em] text-white/35">
                        {currentIndex + 1} / {items.length}{hasMore ? "+" : ""}
                    </div>
                </div>

                {notice && (
                    <div className="absolute left-1/2 top-[calc(env(safe-area-inset-top,0px)+4.5rem)] z-30 -translate-x-1/2 rounded-full bg-white/12 px-4 py-2 text-xs font-medium text-white/85 shadow-2xl backdrop-blur-md">
                        {notice}
                    </div>
                )}
            </div>

            {confirmDeleteOpen && (
                <div
                    className="absolute inset-0 z-40 flex items-center justify-center bg-black/60 p-6 backdrop-blur-sm"
                    role="presentation"
                    onClick={() => {
                        if (!deleting) setConfirmDeleteOpen(false)
                    }}
                >
                    <div
                        ref={deleteDialogRef}
                        role="dialog"
                        aria-modal="true"
                        aria-label="Confirm delete"
                        tabIndex={-1}
                        className="w-full max-w-sm rounded-2xl border border-white/10 bg-neutral-950/95 p-5 text-white shadow-2xl"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="mb-1 flex items-center gap-2 text-sm font-semibold">
                            <Trash2 className="h-4 w-4 text-red-300" />
                            {inTrash ? "Delete permanently?" : "Move to trash?"}
                        </div>
                        <p className="mb-5 break-words text-sm text-white/60">
                            {currentItem.filename}
                            {inTrash && (
                                <span className="mt-2 block text-xs text-red-200/70">
                                    This cannot be undone.
                                </span>
                            )}
                        </p>
                        <div className="flex justify-end gap-2">
                            <button
                                ref={deleteCancelRef}
                                type="button"
                                className="rounded-full px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
                                onClick={() => setConfirmDeleteOpen(false)}
                                disabled={deleting}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="inline-flex items-center gap-2 rounded-full bg-red-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-400 disabled:cursor-not-allowed disabled:opacity-70"
                                onClick={confirmDelete}
                                disabled={deleting}
                            >
                                {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
                                {inTrash ? "Delete" : "Move"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Info Dialog ── */}
            <InfoDialog
                mediaId={currentItem?.id ?? 0}
                open={showInfo}
                initialEditMode={initialEditMode}
                onClose={() => setShowInfo(false)}
                onNavigate={() => {
                    setShowInfo(false)
                    return onNavigateAway?.()
                }}
                onDirtyChange={onDirtyChange}
                externalCloseRequested={externalCloseRequested}
                onKeepEditing={onKeepEditing}
                onDiscardClose={onDiscardClose}
            />
        </div>,
        document.body,
    )
}
