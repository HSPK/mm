import { useEffect, useRef, useState } from "react"

/**
 * Auto-hide UI on scroll-down, show on scroll-up. When `pinned` is true the
 * UI stays visible regardless of scroll direction.
 *
 * Returns `setVisible` so callers can force-show in response to external
 * events (e.g. opening a menu).
 */
export function useAutoHideOnScroll(
    container: HTMLElement | null,
    pinned: boolean,
): { visible: boolean; setVisible: (v: boolean) => void } {
    const [scrollVisible, setScrollVisible] = useState(true)
    const lastYRef = useRef(0)

    useEffect(() => {
        if (!container || pinned) return
        lastYRef.current = container.scrollTop
        const handle = () => {
            const y = container.scrollTop
            const last = lastYRef.current
            lastYRef.current = y
            setScrollVisible(!(y > last && y > 60))
        }
        container.addEventListener("scroll", handle, { passive: true })
        return () => container.removeEventListener("scroll", handle)
    }, [container, pinned])

    return {
        visible: pinned || scrollVisible,
        setVisible: setScrollVisible,
    }
}
