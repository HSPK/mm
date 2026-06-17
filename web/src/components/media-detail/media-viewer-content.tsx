import { AlertTriangle, ChevronLeft, ChevronRight, Maximize2 } from "lucide-react"
import {
    useCallback,
    useEffect,
    useRef,
    useState,
    type MouseEvent,
    type MutableRefObject,
    type PointerEvent,
    type RefObject,
    type TouchEvent,
    type WheelEvent,
} from "react"
import type { Media } from "@/api/types"
import { Spinner } from "@/components/ui/spinner"
import {
    clampImagePan,
    distance,
    midpoint,
    MIN_IMAGE_SCALE,
    wheelDeltaToScale,
    zoomAt,
    type ImageTransform,
    type ViewportPoint,
} from "@/lib/image-zoom"
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
    const resetZoomRef = useRef<(() => void) | null>(null)
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
    resetZoomRef,
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
    resetZoomRef: MutableRefObject<(() => void) | null>
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
                className={`absolute inset-0 bg-black transition-opacity duration-200 ease-out ${mediaLoaded && !mediaErrorMessage
                    ? "opacity-100"
                    : "pointer-events-none opacity-0"
                }`}
            >
                <ImageZoomStage
                    item={item}
                    src={currentImageSrc}
                    scaleRef={scaleRef}
                    resetZoomRef={resetZoomRef}
                    onScaleChange={onScaleChange}
                    onLoaded={onLoaded}
                    onError={onError}
                />
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

const RESET_TRANSFORM: ImageTransform = { scale: MIN_IMAGE_SCALE, x: 0, y: 0 }

function ImageZoomStage({
    item,
    src,
    scaleRef,
    resetZoomRef,
    onScaleChange,
    onLoaded,
    onError,
}: {
    item: Media
    src: string
    scaleRef: RefObject<number>
    resetZoomRef: MutableRefObject<(() => void) | null>
    onScaleChange: (scale: number) => void
    onLoaded: (id: number) => void
    onError: (id: number, message: string) => void
}) {
    const stageRef = useRef<HTMLDivElement>(null)
    const transformRef = useRef<ImageTransform>(RESET_TRANSFORM)
    const [transform, setTransformState] = useState<ImageTransform>(RESET_TRANSFORM)
    const dragRef = useRef<{
        pointerId: number
        startX: number
        startY: number
        originX: number
        originY: number
        moved: boolean
    } | null>(null)
    const pinchRef = useRef<{
        distance: number
        transform: ImageTransform
        center: ViewportPoint
    } | null>(null)
    const gestureRef = useRef<{ scale: number; transform: ImageTransform } | null>(null)
    const lastDragAtRef = useRef(0)

    const setTransform = useCallback((next: ImageTransform | ((current: ImageTransform) => ImageTransform)) => {
        setTransformState((current) => {
            const value = typeof next === "function" ? next(current) : next
            transformRef.current = value
            return value
        })
    }, [])

    const resetZoom = useCallback(() => {
        setTransform(RESET_TRANSFORM)
    }, [setTransform])

    useEffect(() => {
        resetZoomRef.current = resetZoom
        return () => {
            if (resetZoomRef.current === resetZoom) resetZoomRef.current = null
        }
    }, [resetZoom, resetZoomRef])

    useEffect(() => {
        resetZoom()
    }, [item.id, src, resetZoom])

    useEffect(() => {
        scaleRef.current = transform.scale
        onScaleChange(transform.scale)
    }, [onScaleChange, scaleRef, transform.scale])

    const getViewport = useCallback(() => {
        const rect = stageRef.current?.getBoundingClientRect()
        if (!rect) return null
        return { rect, size: { width: rect.width, height: rect.height } }
    }, [])

    const focalFromClient = useCallback((clientX: number, clientY: number): ViewportPoint | null => {
        const viewport = getViewport()
        if (!viewport) return null
        return {
            x: clientX - viewport.rect.left - viewport.rect.width / 2,
            y: clientY - viewport.rect.top - viewport.rect.height / 2,
        }
    }, [getViewport])

    const touchPoint = useCallback((touch: { clientX: number; clientY: number }): ViewportPoint | null => (
        focalFromClient(touch.clientX, touch.clientY)
    ), [focalFromClient])

    const handleWheel = useCallback((event: WheelEvent<HTMLDivElement>) => {
        const viewport = getViewport()
        if (!viewport) return

        if (event.ctrlKey || event.metaKey) {
            event.preventDefault()
            const focal = focalFromClient(event.clientX, event.clientY)
            if (!focal) return
            setTransform((current) => zoomAt(
                current,
                focal,
                wheelDeltaToScale(current.scale, event.deltaY),
                viewport.size,
            ))
            return
        }

        if (transformRef.current.scale <= ZOOM_THRESHOLD) return
        event.preventDefault()
        setTransform((current) => clampImagePan({
            scale: current.scale,
            x: current.x - event.deltaX,
            y: current.y - event.deltaY,
        }, viewport.size))
    }, [focalFromClient, getViewport, setTransform])

    const handlePointerDown = useCallback((event: PointerEvent<HTMLDivElement>) => {
        if (event.button !== 0 || transformRef.current.scale <= ZOOM_THRESHOLD) return
        event.preventDefault()
        event.currentTarget.setPointerCapture(event.pointerId)
        dragRef.current = {
            pointerId: event.pointerId,
            startX: event.clientX,
            startY: event.clientY,
            originX: transformRef.current.x,
            originY: transformRef.current.y,
            moved: false,
        }
    }, [])

    const handlePointerMove = useCallback((event: PointerEvent<HTMLDivElement>) => {
        const drag = dragRef.current
        const viewport = getViewport()
        if (!drag || drag.pointerId !== event.pointerId || !viewport) return
        const dx = event.clientX - drag.startX
        const dy = event.clientY - drag.startY
        if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true
        event.preventDefault()
        setTransform((current) => clampImagePan({
            scale: current.scale,
            x: drag.originX + dx,
            y: drag.originY + dy,
        }, viewport.size))
    }, [getViewport, setTransform])

    const finishPointer = useCallback((event: PointerEvent<HTMLDivElement>) => {
        const drag = dragRef.current
        if (!drag || drag.pointerId !== event.pointerId) return
        if (drag.moved) lastDragAtRef.current = Date.now()
        dragRef.current = null
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId)
        }
    }, [])

    const handleDoubleClick = useCallback((event: MouseEvent<HTMLDivElement>) => {
        const viewport = getViewport()
        if (!viewport) return
        event.preventDefault()
        event.stopPropagation()
        const focal = focalFromClient(event.clientX, event.clientY)
        if (!focal || transformRef.current.scale > ZOOM_THRESHOLD) {
            resetZoom()
            return
        }
        setTransform((current) => zoomAt(current, focal, 3, viewport.size))
    }, [focalFromClient, getViewport, resetZoom, setTransform])

    const handleTouchStart = useCallback((event: TouchEvent<HTMLDivElement>) => {
        if (event.touches.length !== 2) return
        const a = touchPoint(event.touches[0])
        const b = touchPoint(event.touches[1])
        if (!a || !b) return
        event.preventDefault()
        pinchRef.current = {
            distance: distance(a, b),
            transform: transformRef.current,
            center: midpoint(a, b),
        }
    }, [touchPoint])

    const handleTouchMove = useCallback((event: TouchEvent<HTMLDivElement>) => {
        const pinch = pinchRef.current
        const viewport = getViewport()
        if (!pinch || event.touches.length !== 2 || !viewport || pinch.distance <= 0) return
        const a = touchPoint(event.touches[0])
        const b = touchPoint(event.touches[1])
        if (!a || !b) return
        event.preventDefault()
        const center = midpoint(a, b)
        setTransform(zoomAt(
            pinch.transform,
            center,
            pinch.transform.scale * (distance(a, b) / pinch.distance),
            viewport.size,
        ))
    }, [getViewport, setTransform, touchPoint])

    const handleTouchEnd = useCallback((event: TouchEvent<HTMLDivElement>) => {
        if (event.touches.length < 2) pinchRef.current = null
    }, [])

    useEffect(() => {
        const stage = stageRef.current
        if (!stage) return

        const gestureStart = (event: Event) => {
            const gesture = event as Event & { scale?: number }
            event.preventDefault()
            gestureRef.current = {
                scale: Number(gesture.scale) || 1,
                transform: transformRef.current,
            }
        }
        const gestureChange = (event: Event) => {
            const gesture = event as Event & { scale?: number; clientX?: number; clientY?: number }
            const viewport = getViewport()
            if (!gestureRef.current || !viewport) return
            event.preventDefault()
            const focal = focalFromClient(
                Number(gesture.clientX) || viewport.rect.left + viewport.rect.width / 2,
                Number(gesture.clientY) || viewport.rect.top + viewport.rect.height / 2,
            )
            if (!focal) return
            setTransform(zoomAt(
                gestureRef.current.transform,
                focal,
                gestureRef.current.transform.scale * ((Number(gesture.scale) || 1) / gestureRef.current.scale),
                viewport.size,
            ))
        }
        const gestureEnd = () => {
            gestureRef.current = null
        }

        stage.addEventListener("gesturestart", gestureStart)
        stage.addEventListener("gesturechange", gestureChange)
        stage.addEventListener("gestureend", gestureEnd)
        return () => {
            stage.removeEventListener("gesturestart", gestureStart)
            stage.removeEventListener("gesturechange", gestureChange)
            stage.removeEventListener("gestureend", gestureEnd)
        }
    }, [focalFromClient, getViewport, setTransform])

    return (
        <div
            ref={stageRef}
            className={`absolute inset-0 flex items-center justify-center overflow-hidden ${transform.scale > ZOOM_THRESHOLD ? "cursor-grab" : "cursor-zoom-in"}`}
            onWheel={handleWheel}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={finishPointer}
            onPointerCancel={finishPointer}
            onDoubleClick={handleDoubleClick}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            onClickCapture={(event) => {
                if (Date.now() - lastDragAtRef.current < 250) {
                    event.preventDefault()
                    event.stopPropagation()
                }
            }}
        >
            <img
                src={src}
                alt={item.filename}
                crossOrigin="use-credentials"
                draggable={false}
                onLoad={() => onLoaded(item.id)}
                onError={() => onError(item.id, "Could not load photo")}
                className="max-h-screen max-w-screen object-contain will-change-transform"
                style={{
                    transform: `translate3d(${transform.x}px, ${transform.y}px, 0) scale(${transform.scale})`,
                    transformOrigin: "center",
                    userSelect: "none",
                    WebkitUserSelect: "none",
                    touchAction: "none",
                }}
            />
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
