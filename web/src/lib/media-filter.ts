import type { Media } from "@/api/types"

export interface Filters {
    type: string | null
    tag: string | null
    camera: string | null
    date_from: string | null
    date_to: string | null
    date_ranges: string[][] | null
    sort: string
    order: string
    search: string | null
    min_rating: number | null
    favorites_only: boolean
    lat: number | null
    lon: number | null
    radius: number | null
    no_date: boolean
    deleted: boolean
}

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

export function mediaMatchesFilters(item: Media, filters: Filters) {
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
        if (item.gps_lat == null || item.gps_lon == null) return false
        const dLat = filters.radius / 111.32
        const clat = Math.max(-89.9, Math.min(89.9, filters.lat))
        const dLon = filters.radius / (111.32 * Math.cos(clat * Math.PI / 180))
        if (item.gps_lat < filters.lat - dLat || item.gps_lat > filters.lat + dLat) return false
        if (item.gps_lon < filters.lon - dLon || item.gps_lon > filters.lon + dLon) return false
    }

    return true
}

export function needsServerFilterRecheck(filters: Filters) {
    return Boolean(filters.search || filters.camera)
}

export function sortMediaItems(items: Media[], filters: Filters) {
    const direction = filters.order === "asc" ? 1 : -1
    const value = (item: Media) => {
        switch (filters.sort) {
            case "filename":
                return item.filename.toLocaleLowerCase()
            case "rating":
                return item.rating
            case "size":
                return item.file_size
            case "date_taken":
            default:
                return item.date_taken ? Date.parse(item.date_taken) : Number.NEGATIVE_INFINITY
        }
    }

    return [...items].sort((a, b) => {
        const av = value(a)
        const bv = value(b)
        if (av < bv) return -1 * direction
        if (av > bv) return 1 * direction
        return a.id - b.id
    })
}
