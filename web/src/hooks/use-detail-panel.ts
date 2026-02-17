import { useState, useRef, useCallback, useEffect, useMemo } from "react"
import type { Media } from "@/api/types"

/**
 * Manages detail panel state with browser history integration for mobile back button.
 */
export function useDetailPanel(items: Media[]) {
    const [detailId, setDetailIdRaw] = useState<number | null>(null)
    const detailIdRef = useRef(detailId)

    const openDetail = useCallback((id: number) => {
        setDetailIdRaw(id)
        detailIdRef.current = id
        window.history.pushState({ mediaDetail: true }, "")
    }, [])

    const closeDetail = useCallback(() => {
        if (detailIdRef.current != null) {
            setDetailIdRaw(null)
            detailIdRef.current = null
            if (window.history.state?.mediaDetail) {
                window.history.back()
            }
        }
    }, [])

    // Listen for browser back / mobile back gesture
    useEffect(() => {
        const onPopState = () => {
            if (detailIdRef.current != null) {
                setDetailIdRaw(null)
                detailIdRef.current = null
            }
        }
        window.addEventListener("popstate", onPopState)
        return () => window.removeEventListener("popstate", onPopState)
    }, [])

    const currentIndex = useMemo(
        () => (detailId ? items.findIndex((i) => i.id === detailId) : -1),
        [detailId, items],
    )

    return { detailId, currentIndex, openDetail, closeDetail }
}
