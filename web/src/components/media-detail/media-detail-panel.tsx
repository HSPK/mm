import {
    useCallback,
    useEffect,
    useRef,
    useState,
    type MouseEvent,
    type TouchEvent,
} from "react"
import { createPortal } from "react-dom"
import type { Media } from "@/api/types"
import { useBodyScrollLock } from "@/hooks/use-body-scroll-lock"
import { useFocusRestore } from "@/hooks/use-focus-restore"
import { useMediaLoadState } from "@/hooks/use-media-load-state"
import { useMediaPreload } from "@/hooks/use-media-preload"
import { useMediaViewerActions } from "@/hooks/use-media-viewer-actions"
import { useMediaViewerNavigation } from "@/hooks/use-media-viewer-navigation"
import { trapFocus } from "@/lib/focus"
import { canDisplayOriginalImage } from "@/lib/media-kind"
import { openOriginal, shareMedia } from "@/lib/media-share"
import { mediaUrl } from "@/lib/media-url"
import { toast } from "@/stores/toast"
import { DeleteConfirmDialog } from "./delete-confirm-dialog"
import { InfoDialog } from "./info-dialog"
import { MediaViewerChrome } from "./media-viewer-chrome"
import { MediaViewerContent } from "./media-viewer-content"
import { ShortcutsOverlay } from "./shortcuts-overlay"
import { markShortcutsSeen, shouldAutoShowShortcuts } from "./shortcuts-preferences"

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

const SETTLE_DELAY_MS = 320

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
    const [showInfo, setShowInfo] = useState(false)
    const [initialEditMode, setInitialEditMode] = useState(false)
    const [chromeVisible, setChromeVisible] = useState(true)
    const [shortcutsOpen, setShortcutsOpen] = useState(() => shouldAutoShowShortcuts())
    const panelRef = useRef<HTMLDivElement>(null)
    const settleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const touchRef = useRef<{ x: number; y: number; time: number } | null>(null)
    const lastSwipeAtRef = useRef(0)
    const scaleRef = useRef(1)

    const notify = useCallback((message: string) => { toast.error(message) }, [])

    const nav = useMediaViewerNavigation({
        items, startIndex, onClose, onActiveChange,
        onLoadMore, hasMore, loadingMore, notify,
    })
    const load = useMediaLoadState()

    const {
        currentItem, displayItem, currentIndex,
        activeMediaId, displayMediaId,
        setActiveMediaId, setDisplayMediaId,
        goPrev, goNext, requestingMore,
    } = nav
    const isVideo = currentItem?.media_type === "video"
    const currentMediaId = currentItem?.id ?? null
    const mediaLoaded = currentMediaId != null && load.loadedMediaIds.has(currentMediaId)
    const mediaErrorMessage = load.mediaError?.id === currentMediaId ? load.mediaError.message : null
    const showPreviousImage = Boolean(
        currentItem
        && displayItem
        && currentItem.media_type !== "video"
        && displayItem.media_type !== "video"
        && displayItem.id !== currentItem.id,
    )

    const getBestImageSrc = useCallback((item: Media) => (
        canDisplayOriginalImage(item) && load.originalLoadedIds.has(item.id)
            ? mediaUrl.file(item.id)
            : mediaUrl.image(item.id)
    ), [load.originalLoadedIds])

    const currentImageSrc = currentItem && !isVideo ? getBestImageSrc(currentItem) : ""
    const shouldLoadOriginalImage = Boolean(
        currentItem
        && !isVideo
        && mediaLoaded
        && canDisplayOriginalImage(currentItem)
        && !load.originalLoadedIds.has(currentItem.id)
        && !load.originalFailedIds.has(currentItem.id),
    )

    useEffect(() => {
        load.setActiveMediaId(activeMediaId)
    }, [activeMediaId, load])

    // Settle: once the new currentItem is loaded (or is video), flip displayId.
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
        if (!load.loadedMediaIds.has(currentItem.id)) return
        if (displayMediaId === currentItem.id) return

        settleTimerRef.current = window.setTimeout(() => {
            if (load.activeMediaIdRef.current === currentItem.id) {
                setDisplayMediaId(currentItem.id)
            }
            settleTimerRef.current = null
        }, SETTLE_DELAY_MS)

        return () => {
            if (settleTimerRef.current) {
                window.clearTimeout(settleTimerRef.current)
                settleTimerRef.current = null
            }
        }
    }, [currentItem, displayMediaId, load.activeMediaIdRef, load.loadedMediaIds, setDisplayMediaId])

    // Reset transient state on every navigation.
    useEffect(() => {
        scaleRef.current = 1
        load.clearForReset()
        setChromeVisible(true)
    }, [currentMediaId, load])

    const openInfo = (edit = false) => {
        setInitialEditMode(edit)
        setShowInfo(true)
    }

    useMediaPreload(currentIndex, items)

    const actions = useMediaViewerActions({
        currentItem,
        currentIndex,
        items,
        inTrash,
        onClose,
        onDelete,
        onActiveChange,
        setActiveMediaId,
        setDisplayMediaId,
        notify,
    })

    const controlsVisible = isVideo || showInfo || actions.confirmDeleteOpen || chromeVisible

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (showInfo) return
            if (shortcutsOpen) {
                if (e.key === "Escape") {
                    setShortcutsOpen(false)
                    markShortcutsSeen()
                }
                return
            }
            if (actions.confirmDeleteOpen) {
                if (e.key === "Escape" && !actions.deleting) actions.closeDeleteConfirm()
                return
            }
            if (e.key === "Tab") {
                trapFocus(e, panelRef.current)
                return
            }
            if (e.key === "?" || (e.key === "/" && e.shiftKey)) {
                setShortcutsOpen(true)
                return
            }
            if (e.key === "ArrowLeft") goPrev()
            else if (e.key === "ArrowRight") goNext()
            else if (e.key === "Escape") onClose()
        }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
    }, [actions, goPrev, goNext, onClose, showInfo, shortcutsOpen])

    useBodyScrollLock()
    useFocusRestore(panelRef)

    useEffect(() => {
        return () => {
            if (settleTimerRef.current) window.clearTimeout(settleTimerRef.current)
            load.clearRevealFrames()
        }
    }, [load])

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
        const adx = Math.abs(dx)
        const ady = Math.abs(dy)
        const vy = ady / elapsed
        const vx = adx / elapsed

        // Vertical swipe down → close (mobile gesture)
        if (dy > 90 && ady > adx * 1.3 && vy > 0.25) {
            lastSwipeAtRef.current = Date.now()
            onClose()
            return
        }

        // Horizontal swipe → prev/next
        if (adx < 56 || adx < ady * 1.35 || vx < 0.22) return
        lastSwipeAtRef.current = Date.now()
        if (dx > 0) goPrev()
        else goNext()
    }, [goNext, goPrev, isVideo, onClose])

    const handleMediaClick = useCallback((e: MouseEvent<HTMLDivElement>) => {
        if (isVideo || showInfo || actions.confirmDeleteOpen || Date.now() - lastSwipeAtRef.current < 350) return
        if (e.target instanceof HTMLElement && e.target.closest("button, video, input, textarea, select, a")) return
        setChromeVisible((visible) => !visible)
    }, [actions.confirmDeleteOpen, isVideo, showInfo])

    const onDeleteClicked = () => {
        setChromeVisible(true)
        actions.openDeleteConfirm()
    }

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
            <MediaViewerChrome
                showInfo={showInfo}
                isEditing={initialEditMode}
                controlsVisible={controlsVisible}
                downloading={actions.downloading}
                deleting={actions.deleting}
                inTrash={inTrash}
                onClose={onClose}
                onOpenInfo={() => openInfo(false)}
                onOpenEdit={() => openInfo(true)}
                onDownload={actions.download}
                onShare={() => { void shareMedia(currentItem) }}
                onOpenOriginal={() => openOriginal(currentItem)}
                onDelete={onDeleteClicked}
            />

            <MediaViewerContent
                currentItem={currentItem}
                displayItem={displayItem}
                items={items}
                currentIndex={currentIndex}
                hasMore={hasMore}
                isVideo={isVideo}
                mediaLoaded={mediaLoaded}
                mediaErrorMessage={mediaErrorMessage}
                showPreviousImage={showPreviousImage}
                currentImageSrc={currentImageSrc}
                shouldLoadOriginalImage={shouldLoadOriginalImage}
                controlsVisible={controlsVisible}
                requestingMore={requestingMore}
                loadingMore={loadingMore}
                scaleRef={scaleRef}
                onMediaClick={handleMediaClick}
                onTouchStart={handleTouchStart}
                onTouchEnd={handleTouchEnd}
                onPrev={goPrev}
                onNext={goNext}
                onMarkMediaLoaded={load.markMediaLoaded}
                onMarkMediaError={load.markMediaError}
                onMarkOriginalLoaded={load.markOriginalLoaded}
                onMarkOriginalUnavailable={load.markOriginalUnavailable}
                getBestImageSrc={getBestImageSrc}
            />

            <DeleteConfirmDialog
                open={actions.confirmDeleteOpen}
                filename={currentItem.filename}
                inTrash={inTrash}
                deleting={actions.deleting}
                onCancel={actions.closeDeleteConfirm}
                onConfirm={actions.confirmDelete}
            />

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

            <ShortcutsOverlay
                open={shortcutsOpen}
                onClose={() => { setShortcutsOpen(false); markShortcutsSeen() }}
            />
        </div>,
        document.body,
    )
}
