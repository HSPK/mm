import { describe, expect, it } from "vitest"
import type { MusicTracksPage } from "@/api/music"
import { loadMusicQueue } from "./music-queue-loader"

function page(id: string): MusicTracksPage {
    return {
        tracks: [{
            track_id: `track-${id}`,
            playback_id: id,
            title: `Track ${id}`,
            metadata: true,
            images: false,
            lyrics: false,
            duration: 120,
            mime_type: "audio/mpeg",
        }],
        offset: 0,
        limit: 200,
        total: 1,
    }
}

describe("loadMusicQueue", () => {
    it("drops a slower queue request after a newer request starts", async () => {
        let resolveFirst: ((value: MusicTracksPage) => void) | undefined
        const first = loadMusicQueue(
            { album_id: "first" },
            () => new Promise((resolve) => {
                resolveFirst = resolve
            }),
        )
        const second = loadMusicQueue(
            { album_id: "second" },
            async () => page("second"),
        )

        await expect(second).resolves.toEqual([
            expect.objectContaining({ id: "second" }),
        ])
        resolveFirst?.(page("first"))
        await expect(first).resolves.toBeNull()
    })
})
