import { useEffect, useRef } from "react"

/**
 * Infinite scroll using IntersectionObserver.
 * Observes a sentinel element and calls fetchMore when it enters viewport.
 */
export function useInfiniteScroll(
    sentinelRef: React.RefObject<HTMLDivElement | null>,
    hasMore: boolean,
    loading: boolean,
    fetchMore: (reset?: boolean) => Promise<void>,
    rootMargin = "400px",
) {
    // Stable ref avoids observer thrashing on state changes
    const stateRef = useRef({ hasMore, loading, fetchMore })
    useEffect(() => {
        stateRef.current = { hasMore, loading, fetchMore }
    }, [hasMore, loading, fetchMore])

    useEffect(() => {
        const el = sentinelRef.current
        if (!el) return
        const obs = new IntersectionObserver(
            (entries) => {
                const { hasMore, loading, fetchMore } = stateRef.current
                if (entries[0].isIntersecting && hasMore && !loading) fetchMore()
            },
            { rootMargin },
        )
        obs.observe(el)
        return () => obs.disconnect()
    }, [sentinelRef, rootMargin])
}
