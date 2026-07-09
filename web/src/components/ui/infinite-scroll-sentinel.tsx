import { useCallback, useRef } from "react"
import { useInfiniteScroll } from "@/hooks/use-infinite-scroll"

export function InfiniteScrollSentinel({
    hasMore,
    onLoadMore,
}: {
    hasMore: boolean
    onLoadMore: () => void
}) {
    const sentinelRef = useRef<HTMLDivElement>(null)
    const loadMore = useCallback(async () => {
        onLoadMore()
    }, [onLoadMore])

    useInfiniteScroll(sentinelRef, hasMore, false, loadMore)

    if (!hasMore) return null
    return <div ref={sentinelRef} className="h-10" aria-hidden="true" />
}
