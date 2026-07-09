import { useCallback, useRef, useState } from "react"
import { addBoundedId } from "@/lib/bounded-set"

export interface MediaLoadState {
    loadedMediaIds: Set<number>
    originalLoadedIds: Set<number>
    originalFailedIds: Set<number>
    mediaError: { id: number; message: string } | null
    activeMediaIdRef: React.MutableRefObject<number | null>
    setActiveMediaId: (id: number | null) => void
    markMediaLoaded: (id: number) => void
    markMediaError: (id: number, message: string) => void
    markOriginalLoaded: (id: number) => void
    markOriginalUnavailable: (id: number) => void
    clearForReset: () => void
    clearRevealFrames: (id?: number) => void
}

/**
 * Encapsulates the bounded-set bookkeeping for the photo viewer:
 *   - which media ids have finished loading (reveal/fade-in target)
 *   - which originals have completed (so we can upgrade preview→file)
 *   - which originals failed (so we don't retry forever)
 *   - the active id, written by the caller and read back via ref so async
 *     image-load callbacks know whether they're stale.
 *
 */
export function useMediaLoadState(): MediaLoadState {
    const [loadedMediaIds, setLoadedMediaIds] = useState<Set<number>>(() => new Set())
    const [originalLoadedIds, setOriginalLoadedIds] = useState<Set<number>>(() => new Set())
    const [originalFailedIds, setOriginalFailedIds] = useState<Set<number>>(() => new Set())
    const [mediaError, setMediaError] = useState<{ id: number; message: string } | null>(null)

    const activeMediaIdRef = useRef<number | null>(null)

    const setActiveMediaId = useCallback((id: number | null) => {
        activeMediaIdRef.current = id
    }, [])

    const clearRevealFrames = useCallback(() => undefined, [])

    const markMediaLoaded = useCallback((id: number) => {
        setLoadedMediaIds((prev) => (prev.has(id) ? prev : addBoundedId(prev, id)))
        setMediaError((prev) => (prev?.id === id ? null : prev))
    }, [])

    const markMediaError = useCallback((id: number, message: string) => {
        if (activeMediaIdRef.current !== id) return
        setMediaError({ id, message })
    }, [])

    const markOriginalLoaded = useCallback((id: number) => {
        setOriginalLoadedIds((prev) => addBoundedId(prev, id))
    }, [])

    const markOriginalUnavailable = useCallback((id: number) => {
        setOriginalFailedIds((prev) => addBoundedId(prev, id))
    }, [])

    const clearForReset = useCallback(() => {
        setMediaError(null)
    }, [])

    return {
        loadedMediaIds,
        originalLoadedIds,
        originalFailedIds,
        mediaError,
        activeMediaIdRef,
        setActiveMediaId,
        markMediaLoaded,
        markMediaError,
        markOriginalLoaded,
        markOriginalUnavailable,
        clearForReset,
        clearRevealFrames,
    }
}
