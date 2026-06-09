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
 * The reveal-frames map double-rAFs setState so the browser has a frame to
 * paint the image before React removes the loading shimmer.
 */
export function useMediaLoadState(): MediaLoadState {
    const [loadedMediaIds, setLoadedMediaIds] = useState<Set<number>>(() => new Set())
    const [originalLoadedIds, setOriginalLoadedIds] = useState<Set<number>>(() => new Set())
    const [originalFailedIds, setOriginalFailedIds] = useState<Set<number>>(() => new Set())
    const [mediaError, setMediaError] = useState<{ id: number; message: string } | null>(null)

    const activeMediaIdRef = useRef<number | null>(null)
    const revealFramesRef = useRef<Map<number, number[]>>(new Map())

    const setActiveMediaId = useCallback((id: number | null) => {
        activeMediaIdRef.current = id
    }, [])

    const clearRevealFrames = useCallback((id?: number) => {
        if (id != null) {
            const frames = revealFramesRef.current.get(id) ?? []
            for (const frame of frames) window.cancelAnimationFrame(frame)
            revealFramesRef.current.delete(id)
            return
        }
        for (const frames of revealFramesRef.current.values()) {
            for (const frame of frames) window.cancelAnimationFrame(frame)
        }
        revealFramesRef.current.clear()
    }, [])

    const markMediaLoaded = useCallback((id: number) => {
        clearRevealFrames(id)
        const first = window.requestAnimationFrame(() => {
            const second = window.requestAnimationFrame(() => {
                setLoadedMediaIds((prev) => (prev.has(id) ? prev : addBoundedId(prev, id)))
                setMediaError((prev) => (prev?.id === id ? null : prev))
                revealFramesRef.current.delete(id)
            })
            revealFramesRef.current.set(id, [second])
        })
        revealFramesRef.current.set(id, [first])
    }, [clearRevealFrames])

    const markMediaError = useCallback((id: number, message: string) => {
        if (activeMediaIdRef.current !== id) return
        clearRevealFrames(id)
        setMediaError({ id, message })
    }, [clearRevealFrames])

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
