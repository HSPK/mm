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
    const targetSizeRef = useRef(thumbSize)
    const frameRef = useRef<number | null>(null)
    useEffect(() => {
        thumbSizeRef.current = thumbSize
        targetSizeRef.current = thumbSize
    }, [thumbSize])

    useEffect(() => {
        const el = galleryRef.current
        if (!el) return

        const clampSize = (size: number) => Math.min(max, Math.max(min, Math.round(size)))
        const commitSize = (size: number) => {
            targetSizeRef.current = clampSize(size)
            if (frameRef.current != null) return
            frameRef.current = window.requestAnimationFrame(() => {
                frameRef.current = null
                thumbSizeRef.current = targetSizeRef.current
                setThumbSize(targetSizeRef.current)
            })
        }

        const onWheel = (e: WheelEvent) => {
            if (!e.ctrlKey) return
            e.preventDefault()
            const next = targetSizeRef.current * Math.exp(-e.deltaY * 0.004)
            commitSize(next)
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
                initSize = targetSizeRef.current
            }
        }
        const onTouchMove = (e: TouchEvent) => {
            if (e.touches.length === 2 && initDist > 0) {
                e.preventDefault()
                const scale = dist(e.touches) / initDist
                commitSize(initSize * scale)
            }
        }

        el.addEventListener("wheel", onWheel, { passive: false })
        el.addEventListener("touchstart", onTouchStart, { passive: true })
        el.addEventListener("touchmove", onTouchMove, { passive: false })
        return () => {
            if (frameRef.current != null) {
                window.cancelAnimationFrame(frameRef.current)
                frameRef.current = null
            }
            el.removeEventListener("wheel", onWheel)
            el.removeEventListener("touchstart", onTouchStart)
            el.removeEventListener("touchmove", onTouchMove)
        }
    }, [galleryRef, setThumbSize, min, max])
}
