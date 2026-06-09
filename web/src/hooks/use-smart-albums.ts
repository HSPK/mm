import { useCallback, useEffect, useState } from "react"
import { catalogRepo } from "@/api/catalog"
import type { SmartAlbumsResponse } from "@/api/types"

export interface UseSmartAlbumsResult {
    data: SmartAlbumsResponse | null
    loading: boolean
    error: string | null
    retry: () => void
}

/**
 * Fetches the smart-albums payload, exposes a retry trigger, and tracks
 * loading/error state. Unsubscribes if unmounted before the fetch resolves.
 */
export function useSmartAlbums(): UseSmartAlbumsResult {
    const [data, setData] = useState<SmartAlbumsResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [tick, setTick] = useState(0)

    useEffect(() => {
        let mounted = true
        catalogRepo.listSmartAlbums()
            .then((res) => {
                if (!mounted) return
                setData(res)
                setError(null)
                setLoading(false)
            })
            .catch(() => {
                if (!mounted) return
                setData(null)
                setError("Could not load albums")
                setLoading(false)
            })
        return () => { mounted = false }
    }, [tick])

    const retry = useCallback(() => {
        setLoading(true)
        setError(null)
        setTick((t) => t + 1)
    }, [])

    return { data, loading, error, retry }
}
