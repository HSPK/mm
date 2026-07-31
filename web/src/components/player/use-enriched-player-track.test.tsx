import { act, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import type { PlayerTrack } from "@/stores/player"
import { clearPlayerTrackDetails, useEnrichedPlayerTrack } from "./use-enriched-player-track"

const { lyricsMock } = vi.hoisted(() => ({
    lyricsMock: vi.fn(),
}))

vi.mock("@/api/music", async () => {
    const actual = await vi.importActual<typeof import("@/api/music")>("@/api/music")
    return {
        ...actual,
        musicRepo: {
            ...actual.musicRepo,
            lyrics: lyricsMock,
        },
    }
})

const lyricTrack: PlayerTrack = {
    id: "lyric-track",
    path: "/music/lyric-track.flac",
    playbackId: "lyric-track",
    title: "Lyric Track",
    artist: "Artist",
    album: "Album",
    hasLyrics: true,
}

function EnrichmentHarness({ track = lyricTrack }: { track?: PlayerTrack }) {
    const { status, retry } = useEnrichedPlayerTrack(track)
    return (
        <>
            <span>{status}</span>
            <button type="button" onClick={retry}>Retry</button>
        </>
    )
}

beforeEach(() => {
    vi.useFakeTimers()
    lyricsMock.mockReset()
    clearPlayerTrackDetails()
})

afterEach(() => {
    vi.useRealTimers()
})

describe("useEnrichedPlayerTrack", () => {
    it("retries transient lyric failures with bounded backoff", async () => {
        lyricsMock
            .mockRejectedValueOnce(new Error("temporary failure"))
            .mockResolvedValue({
                playback_id: "lyric-track",
                lyrics: "lyrics",
                synced_lyrics: "",
                version: "v1",
            })
        render(<EnrichmentHarness />)

        await act(async () => {
            await vi.advanceTimersByTimeAsync(2_000)
        })

        expect(lyricsMock).toHaveBeenCalledTimes(2)
        expect(screen.getByText("ready")).toBeInTheDocument()
    })

    it("does not request lyrics when the catalog says none exist", () => {
        render(<EnrichmentHarness track={{ ...lyricTrack, hasLyrics: false }} />)

        expect(screen.getByText("none")).toBeInTheDocument()
        expect(lyricsMock).not.toHaveBeenCalled()
    })

    it("revalidates a negative lyric result after its TTL", async () => {
        lyricsMock.mockResolvedValue({
            playback_id: "lyric-track",
            lyrics: "",
            synced_lyrics: "",
            version: "empty",
        })
        render(<EnrichmentHarness />)
        await act(async () => {
            await vi.advanceTimersByTimeAsync(0)
        })
        expect(lyricsMock).toHaveBeenCalledTimes(1)

        await act(async () => {
            await vi.advanceTimersByTimeAsync(5 * 60_000)
        })
        expect(lyricsMock).toHaveBeenCalledTimes(2)
    })
})
