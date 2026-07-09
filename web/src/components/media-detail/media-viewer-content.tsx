import { ChevronLeft, ChevronRight, Maximize2 } from "lucide-react"
import {
    useRef,
    useState,
    type MouseEvent,
    type RefObject,
    type TouchEvent,
} from "react"
import type { Media } from "@/api/types"
import { Spinner } from "@/components/ui/spinner"
import { ImageStage } from "./media-viewer-image-stage"
import { VideoStage } from "./video-stage"

const ZOOM_THRESHOLD = 1.05

interface MediaViewerContentProps {
    currentItem: Media
    displayItem: Media | undefined
    items: Media[]
    currentIndex: number
    hasMore: boolean
    isVideo: boolean
    mediaLoaded: boolean
    mediaErrorMessage: string | null
    showPreviousImage: boolean
    currentImageSrc: string
    shouldLoadOriginalImage: boolean
    controlsVisible: boolean
    playerKeyboardEnabled: boolean
    requestingMore: boolean
    loadingMore: boolean
    scaleRef: RefObject<number>
    onMediaClick: (e: MouseEvent<HTMLDivElement>) => void
    onTouchStart: (e: TouchEvent) => void
    onTouchEnd: (e: TouchEvent) => void
    onPrev: () => void
    onNext: () => void
    onMarkMediaLoaded: (id: number) => void
    onMarkMediaError: (id: number, message: string) => void
    onMarkOriginalLoaded: (id: number) => void
    onMarkOriginalUnavailable: (id: number) => void
    getBestImageSrc: (item: Media) => string
}

/** The scrollable/zoomable image-or-video stage in the center of the viewer. */
export function MediaViewerContent({
    currentItem,
    displayItem,
    items,
    currentIndex,
    hasMore,
    isVideo,
    mediaLoaded,
    mediaErrorMessage,
    showPreviousImage,
    currentImageSrc,
    shouldLoadOriginalImage,
    controlsVisible,
    playerKeyboardEnabled,
    requestingMore,
    loadingMore,
    scaleRef,
    onMediaClick,
    onTouchStart,
    onTouchEnd,
    onPrev,
    onNext,
    onMarkMediaLoaded,
    onMarkMediaError,
    onMarkOriginalLoaded,
    onMarkOriginalUnavailable,
    getBestImageSrc,
}: MediaViewerContentProps) {
    const visibilityClass = controlsVisible ? "opacity-100" : "pointer-events-none opacity-0"
    const [zoomScale, setZoomScale] = useState(1)
    const resetZoomRef = useRef<(() => void) | null>(null)
    const isZoomed = !isVideo && zoomScale > ZOOM_THRESHOLD
    const primaryMetaClass = isVideo ? "text-white/85" : "text-foreground/85"
    const secondaryMetaClass = isVideo ? "text-white/55" : "text-muted-foreground"
    const countMetaClass = isVideo ? "text-white/35" : "text-muted-foreground/70"

    return (
        <div
            className={`flex-1 relative overflow-hidden ${isVideo ? "touch-auto" : "touch-none"}`}
            onClick={onMediaClick}
            onTouchStart={onTouchStart}
            onTouchEnd={onTouchEnd}
        >
            {isVideo
                ? <VideoStage
                    item={currentItem}
                    keyboardEnabled={playerKeyboardEnabled}
                    onLoaded={onMarkMediaLoaded}
                    onError={onMarkMediaError}
                />
                : <ImageStage
                    item={currentItem}
                    displayItem={displayItem}
                    mediaLoaded={mediaLoaded}
                    mediaErrorMessage={mediaErrorMessage}
                    showPreviousImage={showPreviousImage}
                    currentImageSrc={currentImageSrc}
                    shouldLoadOriginalImage={shouldLoadOriginalImage}
                    scaleRef={scaleRef}
                    resetZoomRef={resetZoomRef}
                    onScaleChange={setZoomScale}
                    onLoaded={onMarkMediaLoaded}
                    onError={onMarkMediaError}
                    onOriginalLoaded={onMarkOriginalLoaded}
                    onOriginalUnavailable={onMarkOriginalUnavailable}
                    getBestImageSrc={getBestImageSrc}
                />
            }

            {!isZoomed && (
                <>
                    <NavArrow
                        direction="prev"
                        disabled={!controlsVisible || currentIndex <= 0}
                        controlsVisible={controlsVisible}
                        onClick={onPrev}
                    />
                    <NavArrow
                        direction="next"
                        disabled={!controlsVisible || (currentIndex >= items.length - 1 && !hasMore)}
                        controlsVisible={controlsVisible}
                        onClick={onNext}
                        loading={requestingMore || loadingMore}
                    />
                </>
            )}

            {isZoomed && (
                <ZoomBadge
                    scale={zoomScale}
                    visible={controlsVisible}
                    onReset={() => resetZoomRef.current?.()}
                />
            )}

            <div
                className={`pointer-events-none absolute bottom-0 left-0 right-0 z-10 px-4 pb-5 pt-16 text-center transition-opacity duration-200 ${visibilityClass}`}
                style={{
                    paddingBottom: "max(env(safe-area-inset-bottom, 0px), 20px)",
                    background: isVideo
                        ? "linear-gradient(to top, rgba(0,0,0,0.48) 0%, transparent 100%)"
                        : "linear-gradient(to top, color-mix(in srgb, var(--color-background) 70%, transparent) 0%, transparent 100%)",
                }}
            >
                <div className={`mx-auto max-w-[80vw] truncate text-xs font-medium ${primaryMetaClass}`}>
                    {currentItem.filename}
                </div>
                <MetadataLine item={currentItem} className={secondaryMetaClass} />
                <div className={`mt-1 text-[10px] uppercase tracking-[0.2em] ${countMetaClass}`}>
                    {currentIndex + 1} / {items.length}{hasMore ? "+" : ""}
                </div>
            </div>
        </div>
    )
}

function ZoomBadge({
    scale,
    visible,
    onReset,
}: {
    scale: number
    visible: boolean
    onReset: () => void
}) {
    const percent = Math.round(scale * 100)
    return (
        <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onReset() }}
            className={`pointer-events-auto absolute right-4 top-1/2 z-20 -translate-y-1/2 flex items-center gap-1.5 rounded-full bg-black/50 px-3 py-1.5 text-xs font-semibold text-white/90 shadow-lg transition-opacity duration-200 hover:bg-black/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/35 ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}`}
            aria-label={`Reset zoom (currently ${percent}%)`}
        >
            <Maximize2 className="h-3.5 w-3.5" />
            <span className="tabular-nums">{percent}%</span>
        </button>
    )
}

function MetadataLine({ item, className }: { item: Media; className: string }) {
    const parts: string[] = []
    if (item.date_taken) {
        const d = new Date(item.date_taken)
        if (!Number.isNaN(d.getTime())) {
            parts.push(d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }))
        }
    }
    if (item.camera_model) parts.push(item.camera_model)
    if (item.width && item.height) parts.push(`${item.width}×${item.height}`)

    if (parts.length === 0) return null

    return (
        <div className={`mx-auto mt-1 max-w-[80vw] truncate text-[11px] ${className}`}>
            {parts.join(" · ")}
        </div>
    )
}

function NavArrow({
    direction,
    disabled,
    controlsVisible,
    onClick,
    loading,
}: {
    direction: "prev" | "next"
    disabled: boolean
    controlsVisible: boolean
    onClick: () => void
    loading?: boolean
}) {
    const visibilityClass = controlsVisible ? "opacity-100" : "pointer-events-none opacity-0"
    const positionClass = direction === "prev" ? "left-4" : "right-4"
    const Icon = direction === "prev" ? ChevronLeft : ChevronRight
    return (
        <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            className={`hidden sm:flex absolute ${positionClass} top-1/2 z-20 h-10 w-10 -translate-y-1/2 items-center justify-center rounded-xl bg-black/42 text-white/78 shadow-lg transition hover:bg-black/62 hover:text-white disabled:pointer-events-none disabled:opacity-0 ${visibilityClass}`}
            aria-hidden={!controlsVisible}
            aria-label={direction === "prev" ? "Previous media" : "Next media"}
        >
            {loading
                ? <Spinner size="md" />
                : <Icon className="h-6 w-6" />}
        </button>
    )
}
