export type SortKey = "date_taken" | "filename" | "rating" | "size"
export type SortOrder = "asc" | "desc"

export interface Filters {
    type: string | null
    tag: string | null
    camera: string | null
    date_from: string | null
    date_to: string | null
    date_ranges: string[][] | null
    sort: SortKey
    order: SortOrder
    search: string | null
    min_rating: number | null
    favorites_only: boolean
    lat: number | null
    lon: number | null
    radius: number | null
    no_date: boolean
    has_location: boolean
    deleted: boolean
}

export const defaultFilters: Filters = {
    type: null,
    tag: null,
    camera: null,
    date_from: null,
    date_to: null,
    date_ranges: null,
    sort: "date_taken",
    order: "desc",
    search: null,
    min_rating: null,
    favorites_only: false,
    lat: null,
    lon: null,
    radius: null,
    no_date: false,
    has_location: false,
    deleted: false,
}
