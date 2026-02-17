import { useEffect, useRef } from "react"

/**
 * Pinch-to-zoom for thumbnail size adjustment.
 * Handles both trackpad ctrl+wheel and touch pinch gestures.
 */
export function usePinchZoom(
    galleryRef: React.RefObject<HTMLDivElement | null>,
    thumbSize: number,
    setThumbSize: (size: number) => void,
    min = 80,
    max = 400,
) {
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
            setThumbSize(Math.min(max, Math.max(min, next)))
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
                setThumbSize(Math.min(max, Math.max(min, Math.round(initSize * scale))))
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
    }, [galleryRef, setThumbSize, min, max])
}
