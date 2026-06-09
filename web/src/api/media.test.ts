import MockAdapter from "axios-mock-adapter"
import axios from "axios"
import { describe, expect, it } from "vitest"
import { defaultFilters } from "@/lib/filter-types"
import { createMediaRepository, encodeFilterParams } from "./media"

function harness() {
    const ax = axios.create({ baseURL: "" })
    const mock = new MockAdapter(ax)
    const repo = createMediaRepository(ax)
    return { ax, mock, repo }
}

describe("encodeFilterParams", () => {
    it("includes page + per_page", () => {
        const p = encodeFilterParams(2, 60, defaultFilters)
        expect(p.page).toBe(2)
        expect(p.per_page).toBe(60)
    })

    it("drops null/false/empty filters", () => {
        const p = encodeFilterParams(1, 20, defaultFilters)
        expect(p).not.toHaveProperty("type")
        expect(p).not.toHaveProperty("favorites_only")
        expect(p).not.toHaveProperty("deleted")
    })

    it("JSON-encodes date_ranges", () => {
        const p = encodeFilterParams(1, 20, {
            ...defaultFilters,
            date_ranges: [["2024-01-01", "2024-01-31"]],
        })
        expect(p.date_ranges).toBe(JSON.stringify([["2024-01-01", "2024-01-31"]]))
    })

    it("passes through scalar filters", () => {
        const p = encodeFilterParams(1, 20, { ...defaultFilters, type: "photo", min_rating: 4 })
        expect(p.type).toBe("photo")
        expect(p.min_rating).toBe(4)
    })
})

describe("createMediaRepository", () => {
    it("list passes encoded filters to GET /media", async () => {
        const { mock, repo } = harness()
        mock.onGet("/media").reply((config) => {
            expect(config.params).toMatchObject({ page: 1, per_page: 60, type: "video" })
            return [200, { items: [], total: 0, page: 1, per_page: 60, pages: 0 }]
        })
        await repo.list({ page: 1, perPage: 60, filters: { ...defaultFilters, type: "video" } })
    })

    it("deleteOne adds permanent=true when requested", async () => {
        const { mock, repo } = harness()
        mock.onDelete("/media/9").reply((config) => {
            expect(config.params).toEqual({ permanent: true })
            return [204]
        })
        await repo.deleteOne(9, { permanent: true })
    })

    it("deleteOne omits permanent param when not requested", async () => {
        const { mock, repo } = harness()
        mock.onDelete("/media/9").reply((config) => {
            expect(config.params).toBeUndefined()
            return [204]
        })
        await repo.deleteOne(9)
    })

    it("removeTag encodes the tag name", async () => {
        const { mock, repo } = harness()
        mock.onDelete("/media/3/tags/has%20space").reply(204)
        await repo.removeTag(3, "has space")
    })

    it("setRating returns the new rating", async () => {
        const { mock, repo } = harness()
        mock.onPut("/media/3/rating").reply(200, { rating: 5 })
        const out = await repo.setRating(3, 5)
        expect(out.rating).toBe(5)
    })

    it("batchDelete posts to /batch/delete", async () => {
        const { mock, repo } = harness()
        mock.onPost("/batch/delete").reply((config) => {
            expect(JSON.parse(config.data)).toEqual({ media_ids: [1, 2, 3] })
            return [200, { affected: 3 }]
        })
        const out = await repo.batchDelete([1, 2, 3])
        expect(out.affected).toBe(3)
    })
})
