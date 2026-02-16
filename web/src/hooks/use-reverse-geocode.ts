import { useEffect, useState, useMemo } from "react"

/** Simple in-memory cache keyed by rounded lat,lon */
const cache = new Map<string, string>()

function cacheKey(lat: number, lon: number) {
    return `${lat.toFixed(3)},${lon.toFixed(3)}`
}

/**
 * Reverse geocode lat/lon → city-level place name via OpenStreetMap Nominatim.
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

        fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10&accept-language=zh`,
            { headers: { "User-Agent": "uom-media-app/1.0" } }
        )
            .then((r) => r.json())
            .then((data) => {
                if (cancelled) return
                const addr = data.address ?? {}
                const city =
                    addr.city ||
                    addr.town ||
                    addr.county ||
                    addr.state_district ||
                    addr.state ||
                    data.display_name?.split(",").slice(0, 2).join(",") ||
                    `${lat.toFixed(4)}, ${lon.toFixed(4)}`
                const country = addr.country || ""
                const label = country && city !== country ? `${city}, ${country}` : city
                cache.set(key, label)
                setResolved((prev) => new Map(prev).set(key, label))
            })
            .catch(() => {
                if (!cancelled) {
                    const fallback = `${lat.toFixed(4)}, ${lon.toFixed(4)}`
                    cache.set(key, fallback)
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
