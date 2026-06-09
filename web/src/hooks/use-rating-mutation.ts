import { useRef } from "react"
import { mediaRepo } from "@/api/media"
import type { MediaDetail } from "@/api/types"
import { useMediaQueryStore } from "@/stores/media-query"

export interface UseRatingMutationOpts {
    mediaId: number
    setDetail: React.Dispatch<React.SetStateAction<MediaDetail | null>>
    notify: (message: string) => void
}

/**
 * Updates rating both locally (detail + store) and on the server. Uses a
 * sequence ref so a slow earlier request can't overwrite a newer one.
 */
export function useRatingMutation({ mediaId, setDetail, notify }: UseRatingMutationOpts) {
    const updateItem = useMediaQueryStore((s) => s.updateItem)
    const seqRef = useRef(0)

    return async function setRating(rating: number) {
        const requestSeq = ++seqRef.current
        try {
            const res = await mediaRepo.setRating(mediaId, rating)
            if (requestSeq !== seqRef.current) return
            const nextRating = res.rating
            setDetail((d) => (d ? { ...d, rating: nextRating } : d))
            updateItem(mediaId, { rating: nextRating })
        } catch {
            if (requestSeq !== seqRef.current) return
            notify("Failed to update rating")
        }
    }
}
