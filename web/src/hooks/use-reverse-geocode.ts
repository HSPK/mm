import { useEffect, useState, useMemo } from "react"
import { api } from "@/api/client"

/** Simple in-memory cache keyed by rounded lat,lon */
const cache = new Map<string, string>()

function cacheKey(lat: number, lon: number) {
    return `${lat.toFixed(3)},${lon.toFixed(3)}`
}

/**
 * Reverse geocode lat/lon → city-level place name via BACKEND API.
 * Results are cached in memory to avoid redundant requests.
 */
export function useReverseGeocode(lat: number | null | undefined, lon: number | null | undefined) {
    const key = useMemo(() => (lat != null && lon != null ? cacheKey(lat, lon) : null), [lat, lon])
    const cached = key ? cache.get(key) : undefined
    const [resolved, setResolved] = useState<Map<string, string>>(new Map())

    useEffect(() => {
        if (lat == null || lon == null || key == null) return
        if (cache.has(key)) return

        let cancelled = false

        // Fetch from backend API instead of OSM directly
        api.get("/media/geocode", { params: { lat, lon } })
            .then((res) => {
                if (cancelled) return
                const label = res.data.city || `${lat.toFixed(4)}, ${lon.toFixed(4)}`
                cache.set(key, label)
                setResolved((prev) => new Map(prev).set(key, label))
            })
            .catch(() => {
                if (!cancelled) {
                    // Fallback on error
                    const fallback = `${lat.toFixed(4)}, ${lon.toFixed(4)}`
                    // Do NOT cache failures aggressively in case network recovers
                    setResolved((prev) => new Map(prev).set(key, fallback))
                }
            })

        return () => {
            cancelled = true
        }
    }, [lat, lon, key])

    if (key == null) return null
    return cached ?? resolved.get(key) ?? null
}
