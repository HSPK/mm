import { describe, expect, it, vi } from "vitest"
import { createJobsRepository } from "./jobs"
import { createOrganizerRepository } from "./organizer"

function apiStub() {
    return {
        get: vi.fn(),
        patch: vi.fn(),
        post: vi.fn(),
    }
}

describe("organizer control-plane repository", () => {
    it("loads complete item snapshots, generated patches, and capabilities", async () => {
        const api = apiStub()
        api.get
            .mockResolvedValueOnce({ data: { items: [{ item_uid: "movie-1" }] } })
            .mockResolvedValueOnce({ data: { media_types: [{ media_type: "movie", scrapers: ["tmdb"], outputs: ["nfo"], rename: true, lyrics: false }], scraper_adapters: { tmdb: "tmdb" } } })
        api.patch
            .mockResolvedValueOnce({ data: { item_uid: "movie-1" } })
            .mockResolvedValueOnce({ data: { items: [{ item_uid: "movie-1" }] } })
        api.post.mockResolvedValueOnce({ data: { revealed: true } })
        const repo = createOrganizerRepository(api as never)

        await expect(repo.items({ kind: "movies" })).resolves.toMatchObject({
            items: [{ item_uid: "movie-1" }],
        })
        expect(api.get.mock.calls[0]).toEqual(["/organizer/items", {
            params: { kind: "movies" },
            signal: undefined,
        }])
        await expect(repo.revealDirectory(["track-1", "track-2"])).resolves.toEqual({
            revealed: true,
        })
        expect(api.post).toHaveBeenCalledWith("/organizer/reveal-directory", {
            item_uids: ["track-1", "track-2"],
        })
        await repo.patchItem("movie-1", { revision: 2, title: "Alien", write_nfo: false })
        expect(api.patch).toHaveBeenCalledWith("/organizer/items/movie-1", { revision: 2, title: "Alien", write_nfo: false })
        await repo.patchItems([{ item_uid: "movie-1", revision: 2, title: "Alien", write_nfo: false }])
        expect(api.patch).toHaveBeenCalledWith("/organizer/items", {
            items: [{ item_uid: "movie-1", revision: 2, title: "Alien", write_nfo: false }],
        })
        await expect(repo.capabilities()).resolves.toMatchObject({ scraper_adapters: { tmdb: "tmdb" } })
    })

    it("sends idempotency keys when enqueuing organizer jobs", async () => {
        const api = apiStub()
        api.post.mockResolvedValue({ data: { id: "job-1" } })
        const repo = createJobsRepository(api as never)
        await repo.createScrapeJob([], {
            source: "tmdb",
            language: "ja-JP",
        }, "request-0")
        expect(api.post).toHaveBeenNthCalledWith(1, "/jobs/scrape", {
            items: [],
            source: "tmdb",
            language: "ja-JP",
            overwrite: true,
            selected_candidates: {},
        }, {
            headers: { "Idempotency-Key": "request-0" },
        })
        await repo.createSyncJob(["/media"], true, "request-1")
        expect(api.post).toHaveBeenNthCalledWith(2, "/jobs/sync", { paths: ["/media"], recursive: true }, {
            headers: { "Idempotency-Key": "request-1" },
        })
    })
})
