import { useEffect, useState } from "react"
import { mediaRepo } from "@/api/media"
import type { MediaDetail } from "@/api/types"

export interface UseMediaDetailResult {
    detail: MediaDetail | null
    loading: boolean
    loadError: string | null
    reload: () => void
    setDetail: React.Dispatch<React.SetStateAction<MediaDetail | null>>
}

/**
 * Loads a media detail document by id. Refetches when `mediaId` changes,
 * when `open` flips to true, or when `reload()` is invoked.
 */
export function useMediaDetail(mediaId: number, open: boolean): UseMediaDetailResult {
    const [detail, setDetail] = useState<MediaDetail | null>(null)
    const [loading, setLoading] = useState(false)
    const [loadError, setLoadError] = useState<string | null>(null)
    const [retryTick, setRetryTick] = useState(0)

    useEffect(() => {
        if (!open || !mediaId) return
        let alive = true
        // eslint-disable-next-line react-hooks/set-state-in-effect -- standard fetch hook pattern
        setLoading(true)
        setLoadError(null)
        setDetail(null)

        mediaRepo.get(mediaId)
            .then((data) => { if (alive) setDetail(data) })
            .catch(() => { if (alive) setLoadError("Could not load details") })
            .finally(() => { if (alive) setLoading(false) })

        return () => { alive = false }
    }, [mediaId, open, retryTick])

    return {
        detail,
        loading,
        loadError,
        reload: () => setRetryTick((t) => t + 1),
        setDetail,
    }
}
