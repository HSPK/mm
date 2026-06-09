import { useEffect, type RefObject } from "react"

/**
 * On mount, focus `ref.current` once it's laid out. On unmount, restore focus
 * to whatever element held it before mount. Useful for modal/overlay panels.
 */
export function useFocusRestore<T extends HTMLElement>(ref: RefObject<T | null>): void {
    useEffect(() => {
        const previous = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null
        const frame = window.requestAnimationFrame(() => {
            ref.current?.focus()
        })
        return () => {
            window.cancelAnimationFrame(frame)
            previous?.focus()
        }
    }, [ref])
}
