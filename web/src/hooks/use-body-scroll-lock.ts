import { useEffect } from "react"

/** Locks document.body scroll for the lifetime of the calling component. */
export function useBodyScrollLock(): void {
    useEffect(() => {
        const prev = document.body.style.overflow
        document.body.style.overflow = "hidden"
        return () => { document.body.style.overflow = prev }
    }, [])
}
