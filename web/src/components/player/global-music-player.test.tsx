import { act, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { usePlayerStore, type PlayerTrack } from "@/stores/player"
import { GlobalMusicPlayer } from "./global-music-player"

const track: PlayerTrack = {
    id: "1",
    playbackId: "1",
    title: "Track",
    artist: "Artist",
    album: "Album",
    hasLyrics: false,
    duration: 120,
}

let playMock: ReturnType<typeof vi.spyOn>
let pauseMock: ReturnType<typeof vi.spyOn>
let loadMock: ReturnType<typeof vi.spyOn>

beforeEach(() => {
    usePlayerStore.getState().clearQueue()
    playMock = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue()
    pauseMock = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined)
    loadMock = vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => undefined)
    vi.spyOn(HTMLMediaElement.prototype, "canPlayType").mockReturnValue("probably")
})

afterEach(() => {
    vi.restoreAllMocks()
})

describe("GlobalMusicPlayer", () => {
    it("keeps the audio node mounted and stops it when the queue is cleared", async () => {
        usePlayerStore.getState().setQueue([track], 0, true)
        render(<GlobalMusicPlayer />)
        const audio = document.querySelector("audio")
        expect(audio).not.toBeNull()
        await waitFor(() => expect(playMock).toHaveBeenCalled())
        const pauseCalls = pauseMock.mock.calls.length

        act(() => usePlayerStore.getState().clearQueue())

        expect(document.querySelector("audio")).toBe(audio)
        await waitFor(() => expect(pauseMock.mock.calls.length).toBeGreaterThan(pauseCalls))
        expect(screen.queryByText("Track")).not.toBeInTheDocument()
        expect(audio?.getAttribute("src")).toBeNull()
        expect(loadMock).toHaveBeenCalled()
    })
})
