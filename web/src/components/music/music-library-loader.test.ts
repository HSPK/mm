import { beforeEach, describe, expect, it, vi } from "vitest"
import type { MusicRepository } from "@/api/music"
import { clearMusicLibraryCache, loadMusicLibrary } from "./music-library-loader"

type MusicLibraryRepository = Pick<MusicRepository, "albums" | "tracks" | "artists">

function repository(): MusicLibraryRepository {
    return {
        albums: vi.fn(async (params) => ({
            albums: [],
            offset: params?.offset ?? 0,
            limit: params?.limit ?? 50,
            total: 0,
        })),
        tracks: vi.fn(async (params) => ({
            tracks: [],
            offset: params?.offset ?? 0,
            limit: params?.limit ?? 100,
            total: 0,
        })),
        artists: vi.fn(async (params) => ({
            artists: [],
            offset: params?.offset ?? 0,
            limit: params?.limit ?? 100,
            total: 0,
        })),
    }
}

beforeEach(() => {
    clearMusicLibraryCache()
})

describe("loadMusicLibrary", () => {
    it("loads bounded album, track, and artist pages", async () => {
        const repo = repository()

        await expect(loadMusicLibrary("", repo)).resolves.toEqual({
            albums: { albums: [], offset: 0, limit: 50, total: 0 },
            tracks: { tracks: [], offset: 0, limit: 100, total: 0 },
            artists: { artists: [], offset: 0, limit: 100, total: 0 },
        })
        expect(repo.albums).toHaveBeenCalledWith({ offset: 0, limit: 50 })
        expect(repo.tracks).toHaveBeenCalledWith({ offset: 0, limit: 100 })
        expect(repo.artists).toHaveBeenCalledWith({ offset: 0, limit: 100 })
    })

    it("passes server-side search to every catalog surface", async () => {
        const repo = repository()

        await loadMusicLibrary("query", repo)

        expect(repo.albums).toHaveBeenCalledWith(expect.objectContaining({ query: "query" }))
        expect(repo.tracks).toHaveBeenCalledWith(expect.objectContaining({ query: "query" }))
        expect(repo.artists).toHaveBeenCalledWith(expect.objectContaining({ query: "query" }))
    })
})
