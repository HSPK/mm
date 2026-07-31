import { describe, expect, it } from "vitest"
import { config } from "@/lib/config"
import {
    activeLyricLine,
    organizerFileUrl,
    parseLyrics,
    parseSyncedLyrics,
} from "./music-player-utils"

describe("music lyrics", () => {
    it("parses multiple LRC timestamps and applies the offset", () => {
        const lines = parseSyncedLyrics([
            "[offset:+500]",
            "[00:01.00][00:02.250]Line",
        ].join("\n"))

        expect(lines).toEqual([
            { time: 1.5, text: "Line" },
            { time: 2.75, text: "Line" },
        ])
    })

    it("ignores invalid timestamp seconds", () => {
        expect(parseSyncedLyrics("[01:72.00]Invalid")).toEqual([])
    })

    it("finds the active lyric with a sorted binary search", () => {
        const lines = [
            { time: 1, text: "one" },
            { time: 3, text: "two" },
            { time: 8, text: "three" },
        ]

        expect(activeLyricLine(lines, 2.9)).toBe(1)
        expect(activeLyricLine(lines, 0)).toBe(-1)
    })

    it("falls back to plain lyrics when synced lyrics are not valid LRC", () => {
        expect(parseLyrics({
            id: "1",
            path: "/music/1.flac",
            title: "Track",
            artist: "Artist",
            album: "Album",
            syncedLyrics: "not timed",
        }).plain).toEqual(["not timed"])
    })

    it("preserves stanza breaks in plain lyrics", () => {
        expect(parseLyrics({
            id: "1",
            title: "Track",
            artist: "Artist",
            album: "Album",
            lyrics: "Verse one\n\nVerse two",
        }).plain).toEqual(["Verse one", "", "Verse two"])
    })

    it("keeps bearer tokens out of same-origin audio URLs", () => {
        expect(organizerFileUrl("42")).toBe("/api/player/audio?playback_id=42")
    })

    it("resolves short-lived signed URLs for cross-origin audio", () => {
        const originalBaseUrl = config.apiBaseUrl
        config.apiBaseUrl = "https://media.example.test/api"
        try {
            expect(organizerFileUrl(
                "42",
                "/api/player/audio?playback_id=42&ticket=signed",
            )).toBe("https://media.example.test/api/player/audio?playback_id=42&ticket=signed")
        } finally {
            config.apiBaseUrl = originalBaseUrl
        }
    })
})
