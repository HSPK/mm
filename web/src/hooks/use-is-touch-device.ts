import { useEffect, useState } from "react"

/**
 * Returns true when the primary input is a touchscreen. Used to mount mobile
 * gesture layers only on phones/tablets so the desktop UX stays untouched.
 *
 * Reacts to changes (e.g. user docks a tablet to a keyboard+mouse).
 */
export function useIsTouchDevice(): boolean {
    const [touch, setTouch] = useState(() => detect())

    useEffect(() => {
        if (typeof window === "undefined" || !window.matchMedia) return
        const mq = window.matchMedia("(pointer: coarse)")
        const onChange = () => setTouch(detect())
        mq.addEventListener("change", onChange)
        return () => mq.removeEventListener("change", onChange)
    }, [])

    return touch
}

function detect(): boolean {
    if (typeof window === "undefined") return false
    if (window.matchMedia?.("(pointer: coarse)").matches) return true
    if ("ontouchstart" in window) return true
    if (typeof navigator !== "undefined" && navigator.maxTouchPoints > 0) return true
    return false
}
