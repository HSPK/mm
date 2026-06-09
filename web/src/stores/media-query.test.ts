import { beforeEach, describe, expect, it, vi } from "vitest"
import type { Media } from "@/api/types"
import type { MediaRepository } from "@/api/media"
import { defaultFilters } from "@/lib/filter-types"
import { createMediaQueryStore } from "./media-query"

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

function makeRepo(): MediaRepository {
    return {
        list: vi.fn(async () => ({
            items: [makeMedia({ id: 1 }), makeMedia({ id: 2 })],
            total: 2,
            page: 1,
            per_page: 60,
            pages: 1,
        })),
        get: vi.fn(),
        updateMetadata: vi.fn(),
        setRating: vi.fn(),
        addTags: vi.fn(),
        removeTag: vi.fn(),
        deleteOne: vi.fn(),
        restoreOne: vi.fn(),
        batchDelete: vi.fn(),
        downloadBlob: vi.fn(),
        listTrash: vi.fn(),
        emptyTrash: vi.fn(),
    } as unknown as MediaRepository
}

let store: ReturnType<typeof createMediaQueryStore>

beforeEach(() => {
    store = createMediaQueryStore(makeRepo())
})

describe("useMediaQueryStore", () => {
    it("fetchMedia(true) loads first page and sets hasMore=false when pages<=1", async () => {
        await store.getState().fetchMedia(true)
        const s = store.getState()
        expect(s.items.map((i) => i.id)).toEqual([1, 2])
        expect(s.total).toBe(2)
        expect(s.hasMore).toBe(false)
        expect(s.loading).toBe(false)
    })

    it("setFilter updates filter and triggers refetch", async () => {
        const repo = makeRepo()
        store = createMediaQueryStore(repo)
        store.getState().setFilter("type", "video")
        await Promise.resolve()
        await Promise.resolve()
        expect(store.getState().filters.type).toBe("video")
        expect(repo.list).toHaveBeenCalled()
    })

    it("setFilters with replace=true wipes prior filters and active label", () => {
        store.setState({
            filters: { ...defaultFilters, type: "photo" },
            activeLabel: "Pets",
            albumFilterKeys: new Set(["type"]),
        })
        store.getState().setFilters({ favorites_only: true }, { replace: true })
        const s = store.getState()
        expect(s.filters.type).toBeNull()
        expect(s.filters.favorites_only).toBe(true)
        expect(s.activeLabel).toBeNull()
        expect(s.albumFilterKeys.size).toBe(0)
    })

    it("removeItem removes by id and decrements total", () => {
        store.setState({
            items: [makeMedia({ id: 1 }), makeMedia({ id: 2 })],
            total: 2,
        })
        store.getState().removeItem(1)
        const s = store.getState()
        expect(s.items.map((i) => i.id)).toEqual([2])
        expect(s.total).toBe(1)
    })

    it("updateItem applies patch then re-applies filters", () => {
        store.setState({
            items: [makeMedia({ id: 1, rating: 5 }), makeMedia({ id: 2, rating: 5 })],
            total: 2,
            filters: { ...defaultFilters, min_rating: 4 },
        })
        store.getState().updateItem(1, { rating: 1 })
        const s = store.getState()
        expect(s.items.map((i) => i.id)).toEqual([2])
        expect(s.total).toBe(1)
    })

    it("removeItems removes a batch by ids", () => {
        store.setState({
            items: [makeMedia({ id: 1 }), makeMedia({ id: 2 }), makeMedia({ id: 3 })],
            total: 3,
        })
        store.getState().removeItems([1, 3])
        const s = store.getState()
        expect(s.items.map((i) => i.id)).toEqual([2])
        expect(s.total).toBe(1)
    })

    it("setActiveLabel stores label and locks keys", () => {
        store.getState().setActiveLabel("Birthday", ["type", "date_from"])
        const s = store.getState()
        expect(s.activeLabel).toBe("Birthday")
        expect([...s.albumFilterKeys].sort()).toEqual(["date_from", "type"])
    })
})
