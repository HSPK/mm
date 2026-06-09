import type { Media } from "@/api/types"
import type { Filters, SortKey } from "./filter-types"

type Comparable = number | string

type SortValue = (item: Media) => Comparable

// Registry of sort dimensions. To add a new sort, register here — no callers
// to update. Each entry returns a single value used for asc/desc comparison.
const sortValues: Record<SortKey, SortValue> = {
    date_taken: (item) =>
        item.date_taken ? Date.parse(item.date_taken) : Number.NEGATIVE_INFINITY,
    filename: (item) => item.filename.toLocaleLowerCase(),
    rating: (item) => item.rating,
    size: (item) => item.file_size,
}

export function registerSorter(key: SortKey, value: SortValue): void {
    sortValues[key] = value
}

export function sortMediaItems(items: Media[], filters: Filters): Media[] {
    const value = sortValues[filters.sort] ?? sortValues.date_taken
    const direction = filters.order === "asc" ? 1 : -1
    return [...items].sort((a, b) => {
        const av = value(a)
        const bv = value(b)
        if (av < bv) return -1 * direction
        if (av > bv) return 1 * direction
        return a.id - b.id
    })
}
