import type { Media } from "@/api/types"
import type { Filters } from "./filter-types"

function dateKey(value: string | null | undefined) {
    return value ? value.slice(0, 19) : null
}

function matchesDateRanges(value: string | null, ranges: string[][]) {
    if (!value) return false
    return ranges.some((range) => {
        if (range.length < 2) return false
        return value >= `${range[0]}T00:00:00` && value <= `${range[1]}T23:59:59`
    })
}

function matchesGeoBox(item: Media, lat: number, lon: number, radius: number) {
    if (item.gps_lat == null || item.gps_lon == null) return false
    const dLat = radius / 111.32
    const clat = Math.max(-89.9, Math.min(89.9, lat))
    const dLon = radius / (111.32 * Math.cos((clat * Math.PI) / 180))
    if (item.gps_lat < lat - dLat || item.gps_lat > lat + dLat) return false
    if (item.gps_lon < lon - dLon || item.gps_lon > lon + dLon) return false
    return true
}

export function mediaMatchesFilters(item: Media, filters: Filters): boolean {
    if (filters.deleted ? !item.deleted_at : item.deleted_at) return false
    if (filters.type && item.media_type !== filters.type) return false
    if (filters.min_rating && item.rating < filters.min_rating) return false
    if (filters.favorites_only && item.rating < 4) return false

    const taken = dateKey(item.date_taken)
    if (filters.no_date && taken) return false
    if (filters.date_from && (!taken || taken < `${filters.date_from}T00:00:00`)) return false
    if (filters.date_to && (!taken || taken > `${filters.date_to}T23:59:59`)) return false
    if (filters.date_ranges && !matchesDateRanges(taken, filters.date_ranges)) return false

    if (filters.lat != null && filters.lon != null && filters.radius != null) {
        if (!matchesGeoBox(item, filters.lat, filters.lon, filters.radius)) return false
    }

    return true
}

/**
 * Filters whose evaluation depends on data the client doesn't ship in `Media`
 * (camera comes only from metadata; search hits the server-side index). When
 * one of these changes, the cached page must be refetched instead of filtered
 * client-side.
 */
export function needsServerFilterRecheck(filters: Filters): boolean {
    return Boolean(filters.search || filters.camera)
}
