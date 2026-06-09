import { AlertTriangle, ChevronLeft, ChevronRight, Maximize2 } from "lucide-react"
import { useRef, useState, type MouseEvent, type RefObject, type TouchEvent } from "react"
import {
    TransformComponent,
    TransformWrapper,
    type ReactZoomPanPinchRef,
} from "react-zoom-pan-pinch"
import type { Media } from "@/api/types"
import { Spinner } from "@/components/ui/spinner"
import { mediaUrl } from "@/lib/media-url"
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
    const zoomRef = useRef<ReactZoomPanPinchRef>(null)
    const isZoomed = !isVideo && zoomScale > ZOOM_THRESHOLD

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
                    zoomRef={zoomRef}
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
                    onReset={() => zoomRef.current?.resetTransform()}
                />
            )}

            <div
                className={`pointer-events-none absolute bottom-0 left-0 right-0 z-10 px-4 pb-5 pt-16 text-center transition-opacity duration-200 ${visibilityClass}`}
                style={{
                    paddingBottom: "max(env(safe-area-inset-bottom, 0px), 20px)",
                    background: "linear-gradient(to top, rgba(0,0,0,0.46) 0%, transparent 100%)",
                }}
            >
                <div className="mx-auto max-w-[80vw] truncate text-xs font-medium text-white/85">
                    {currentItem.filename}
                </div>
                <MetadataLine item={currentItem} />
                <div className="mt-1 text-[10px] uppercase tracking-[0.2em] text-white/35">
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
            className={`pointer-events-auto absolute right-4 top-1/2 z-20 -translate-y-1/2 flex items-center gap-1.5 rounded-full bg-black/50 px-3 py-1.5 text-xs font-semibold text-white/90 backdrop-blur-md shadow-lg transition-opacity duration-200 hover:bg-black/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}`}
            aria-label={`Reset zoom (currently ${percent}%)`}
        >
            <Maximize2 className="h-3.5 w-3.5" />
            <span className="tabular-nums">{percent}%</span>
        </button>
    )
}

function MetadataLine({ item }: { item: Media }) {
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
        <div className="mt-1 text-[11px] text-white/55 truncate max-w-[80vw] mx-auto">
            {parts.join(" · ")}
        </div>
    )
}

function ImageStage({
    item,
    displayItem,
    mediaLoaded,
    mediaErrorMessage,
    showPreviousImage,
    currentImageSrc,
    shouldLoadOriginalImage,
    scaleRef,
    zoomRef,
    onScaleChange,
    onLoaded,
    onError,
    onOriginalLoaded,
    onOriginalUnavailable,
    getBestImageSrc,
}: {
    item: Media
    displayItem: Media | undefined
    mediaLoaded: boolean
    mediaErrorMessage: string | null
    showPreviousImage: boolean
    currentImageSrc: string
    shouldLoadOriginalImage: boolean
    scaleRef: RefObject<number>
    zoomRef: RefObject<ReactZoomPanPinchRef | null>
    onScaleChange: (scale: number) => void
    onLoaded: (id: number) => void
    onError: (id: number, message: string) => void
    onOriginalLoaded: (id: number) => void
    onOriginalUnavailable: (id: number) => void
    getBestImageSrc: (item: Media) => string
}) {
    return (
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
                            src={mediaUrl.thumbnail(item.id)}
                            alt=""
                            crossOrigin="use-credentials"
                            className="absolute inset-0 h-full w-full scale-105 animate-pulse object-contain opacity-40 blur-xl"
                            draggable={false}
                        />
                    )}
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3">
                        <Spinner size="md" className="text-white/35" />
                    </div>
                </>
            )}
            {mediaErrorMessage && <ErrorOverlay message={mediaErrorMessage} />}
            <div
                className={`absolute inset-0 transition-opacity duration-300 ease-out ${mediaLoaded && !mediaErrorMessage
                    ? "opacity-100"
                    : "pointer-events-none opacity-0"
                }`}
            >
                <TransformWrapper
                    key={item.id}
                    ref={zoomRef}
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
                        onScaleChange(ref.state.scale)
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
                            alt={item.filename}
                            crossOrigin="use-credentials"
                            draggable={false}
                            onLoad={() => onLoaded(item.id)}
                            onError={() => onError(item.id, "Could not load photo")}
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
                        src={mediaUrl.file(item.id)}
                        alt=""
                        crossOrigin="use-credentials"
                        draggable={false}
                        onLoad={() => onOriginalLoaded(item.id)}
                        onError={() => onOriginalUnavailable(item.id)}
                        className="pointer-events-none absolute h-px w-px opacity-0"
                    />
                )}
            </div>
        </div>
    )
}

function ErrorOverlay({ message }: { message: string }) {
    return (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 text-white/70">
            <AlertTriangle className="h-7 w-7 text-white/45" />
            <span className="text-sm">{message}</span>
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
            className={`hidden sm:flex absolute ${positionClass} top-1/2 z-20 h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/30 text-white/70 backdrop-blur-md transition hover:bg-black/45 hover:text-white disabled:pointer-events-none disabled:opacity-0 ${visibilityClass}`}
            aria-hidden={!controlsVisible}
            aria-label={direction === "prev" ? "Previous media" : "Next media"}
        >
            {loading
                ? <Spinner size="md" />
                : <Icon className="h-6 w-6" />}
        </button>
    )
}
