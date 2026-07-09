import { AlertTriangle } from "lucide-react"
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

const ZOOM_THRESHOLD = 1.05
const RESET_TRANSFORM: ImageTransform = { scale: MIN_IMAGE_SCALE, x: 0, y: 0 }

export function ImageStage({
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
                        <Spinner size="md" className="text-muted-foreground" />
                    </div>
                </>
            )}
            {mediaErrorMessage && <ErrorOverlay message={mediaErrorMessage} />}
            <div
                className={`absolute inset-0 bg-background transition-opacity duration-200 ease-out ${mediaLoaded && !mediaErrorMessage
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
    const imgRef = useRef<HTMLImageElement>(null)
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

    const handleImageLoaded = useCallback(() => {
        onLoaded(item.id)
    }, [item.id, onLoaded])

    useEffect(() => {
        const img = imgRef.current
        if (!img?.complete) return
        if (img.naturalWidth > 0) {
            handleImageLoaded()
        } else {
            onError(item.id, "Could not load photo")
        }
    }, [handleImageLoaded, item.id, onError, src])

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
        setTransform(zoomAt(
            pinch.transform,
            midpoint(a, b),
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
            className={`absolute inset-0 flex items-center justify-center overflow-hidden ${transform.scale > ZOOM_THRESHOLD ? "cursor-grab" : "cursor-default"}`}
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
                ref={imgRef}
                src={src}
                alt={item.filename}
                crossOrigin="use-credentials"
                draggable={false}
                onLoad={handleImageLoaded}
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
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 text-foreground/70">
            <AlertTriangle className="h-7 w-7 text-muted-foreground" />
            <span className="text-sm">{message}</span>
        </div>
    )
}
