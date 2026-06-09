import { describe, expect, it } from "vitest"
import type { Media } from "@/api/types"
import { defaultFilters, type Filters } from "./filter-types"
import {
    mediaMatchesFilters,
    needsServerFilterRecheck,
} from "./media-predicate"
import { registerSorter, sortMediaItems } from "./media-sorters"

function makeMedia(overrides: Partial<Media>): Media {
    return {
        id: 1,
        filename: "img.jpg",
        extension: ".jpg",
        media_type: "photo",
        file_size: 100,
        rating: 0,
        ...overrides,
    }
}

function filters(overrides: Partial<Filters>): Filters {
    return { ...defaultFilters, ...overrides }
}

describe("mediaMatchesFilters", () => {
    it("filters by deleted flag", () => {
        const live = makeMedia({ deleted_at: null })
        const trash = makeMedia({ deleted_at: "2024-01-01T00:00:00Z" })
        expect(mediaMatchesFilters(live, filters({ deleted: false }))).toBe(true)
        expect(mediaMatchesFilters(trash, filters({ deleted: false }))).toBe(false)
        expect(mediaMatchesFilters(live, filters({ deleted: true }))).toBe(false)
        expect(mediaMatchesFilters(trash, filters({ deleted: true }))).toBe(true)
    })

    it("filters by media type", () => {
        expect(
            mediaMatchesFilters(makeMedia({ media_type: "video" }), filters({ type: "video" })),
        ).toBe(true)
        expect(
            mediaMatchesFilters(makeMedia({ media_type: "photo" }), filters({ type: "video" })),
        ).toBe(false)
    })

    it("filters by minimum rating and favorites-only", () => {
        expect(mediaMatchesFilters(makeMedia({ rating: 3 }), filters({ min_rating: 4 }))).toBe(false)
        expect(mediaMatchesFilters(makeMedia({ rating: 5 }), filters({ min_rating: 4 }))).toBe(true)
        expect(mediaMatchesFilters(makeMedia({ rating: 3 }), filters({ favorites_only: true }))).toBe(false)
        expect(mediaMatchesFilters(makeMedia({ rating: 4 }), filters({ favorites_only: true }))).toBe(true)
    })

    it("filters by date range", () => {
        const m = makeMedia({ date_taken: "2024-03-15T10:00:00Z" })
        expect(
            mediaMatchesFilters(m, filters({ date_from: "2024-03-01", date_to: "2024-03-31" })),
        ).toBe(true)
        expect(
            mediaMatchesFilters(m, filters({ date_from: "2024-04-01" })),
        ).toBe(false)
    })

    it("treats no_date as: only items without a date pass", () => {
        const m = makeMedia({ date_taken: "2024-03-15T10:00:00Z" })
        const noDate = makeMedia({ date_taken: null })
        expect(mediaMatchesFilters(m, filters({ no_date: true }))).toBe(false)
        expect(mediaMatchesFilters(noDate, filters({ no_date: true }))).toBe(true)
    })

    it("filters by geo bounding box", () => {
        const here = makeMedia({ gps_lat: 39.9, gps_lon: 116.4 })
        const far = makeMedia({ gps_lat: 0, gps_lon: 0 })
        const f = filters({ lat: 39.9, lon: 116.4, radius: 5 })
        expect(mediaMatchesFilters(here, f)).toBe(true)
        expect(mediaMatchesFilters(far, f)).toBe(false)
    })
})

describe("needsServerFilterRecheck", () => {
    it("returns true for filters not evaluable from cached items", () => {
        expect(needsServerFilterRecheck(filters({ search: "cat" }))).toBe(true)
        expect(needsServerFilterRecheck(filters({ camera: "Sony" }))).toBe(true)
        expect(needsServerFilterRecheck(filters({}))).toBe(false)
    })
})

describe("sortMediaItems", () => {
    const items = [
        makeMedia({ id: 1, filename: "b.jpg", rating: 3, file_size: 200, date_taken: "2024-01-01T00:00:00Z" }),
        makeMedia({ id: 2, filename: "a.jpg", rating: 5, file_size: 100, date_taken: "2024-03-01T00:00:00Z" }),
        makeMedia({ id: 3, filename: "c.jpg", rating: 1, file_size: 300, date_taken: null }),
    ]

    it("sorts by date_taken desc by default", () => {
        const ids = sortMediaItems(items, filters({})).map((i) => i.id)
        expect(ids).toEqual([2, 1, 3])
    })

    it("sorts by filename asc", () => {
        const ids = sortMediaItems(items, filters({ sort: "filename", order: "asc" })).map((i) => i.id)
        expect(ids).toEqual([2, 1, 3])
    })

    it("sorts by rating desc", () => {
        const ids = sortMediaItems(items, filters({ sort: "rating", order: "desc" })).map((i) => i.id)
        expect(ids).toEqual([2, 1, 3])
    })

    it("sorts by size desc", () => {
        const ids = sortMediaItems(items, filters({ sort: "size", order: "desc" })).map((i) => i.id)
        expect(ids).toEqual([3, 1, 2])
    })

    it("breaks ties by id", () => {
        const same = [
            makeMedia({ id: 4, rating: 3 }),
            makeMedia({ id: 2, rating: 3 }),
            makeMedia({ id: 6, rating: 3 }),
        ]
        const ids = sortMediaItems(same, filters({ sort: "rating", order: "desc" })).map((i) => i.id)
        expect(ids).toEqual([2, 4, 6])
    })

    it("supports registering a new sorter without editing the module", () => {
        registerSorter("filename" as never, (item) => item.id)
        const ids = sortMediaItems(items, filters({ sort: "filename", order: "asc" })).map((i) => i.id)
        expect(ids).toEqual([1, 2, 3])
        // restore default behavior for other tests
        registerSorter("filename" as never, (item) => item.filename.toLocaleLowerCase())
    })
})
