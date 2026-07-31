import { describe, expect, it } from "vitest"
import type { MusicAlbum, MusicTrack } from "@/api/music"
import { buildAlbumGroups, trackFromSummary } from "./music-library-model"

describe("music library model", () => {
    it("uses server-provided opaque album identities", () => {
        const albums: MusicAlbum[] = [{
            album_id: "album_opaque",
            artist_id: "artist_opaque",
            album_artist_id: "artist_opaque",
            key: "album_opaque",
            title: "Album",
            artist: "Artist",
            count: 1,
        }]

        const result = buildAlbumGroups(albums)

        expect(result[0].id).toBe("album_opaque")
        expect(result[0].artistId).toBe("artist_opaque")
        expect(result[0].tracks).toEqual([])
    })

    it("uses playback ids instead of filesystem paths as track identity", () => {
        const track: MusicTrack = {
            track_id: "track-opaque",
            playback_id: "42",
            title: "Track",
            artist: "Artist",
            album: "Album",
            metadata: true,
            images: false,
            lyrics: false,
            duration: 123,
            mime_type: "audio/flac",
        }

        const result = trackFromSummary(track)

        expect(result.id).toBe("42")
        expect(result.duration).toBe(123)
        expect(result.playable).toBe(true)
    })

    it("marks known browser-incompatible audio as unavailable", () => {
        const result = trackFromSummary({
            track_id: "track-legacy",
            playback_id: "43",
            title: "Legacy Track",
            metadata: true,
            images: false,
            lyrics: false,
            mime_type: "audio/x-ms-wma",
        })

        expect(result.playable).toBe(false)
        expect(result.unavailableReason).toContain("cannot play")
    })
})
