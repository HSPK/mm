import AxiosMockAdapter from "axios-mock-adapter"
import { describe, expect, it } from "vitest"
import { createApiClient } from "./client"
import { createMusicRepository } from "./music"
import { createMemoryTokenStorage } from "@/lib/token-storage"

describe("music repository routes", () => {
    it("uses the music data-plane namespace", async () => {
        const api = createApiClient({
            baseUrl: "/api",
            tokenStorage: createMemoryTokenStorage("token"),
        })
        const mock = new AxiosMockAdapter(api)
        mock.onGet("/music/tracks").reply(200, {
            tracks: [],
            offset: 0,
            limit: 100,
            total: 0,
        })
        const repo = createMusicRepository(api)

        await expect(repo.tracks({ offset: 1000, limit: 200 })).resolves.toEqual({
            tracks: [],
            offset: 0,
            limit: 100,
            total: 0,
        })
        expect(mock.history.get[0].url).toBe("/music/tracks")
        expect(mock.history.get[0].params).toEqual({ offset: 1000, limit: 200 })
    })
})
