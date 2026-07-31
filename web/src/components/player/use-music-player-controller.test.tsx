import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { playerRepo } from "@/api/player"
import { config } from "@/lib/config"
import { usePlayerStore, type PlayerTrack } from "@/stores/player"
import { useMusicPlayerController } from "./use-music-player-controller"

function track(id: string): PlayerTrack {
    return {
        id,
        path: `/music/${id}.flac`,
        playbackId: id,
        title: `Track ${id}`,
        artist: "Artist",
        album: "Album",
        hasLyrics: false,
        duration: 120,
    }
}

function PlayerHarness() {
    const {
        audioRef,
        previous,
        next,
        audioHandlers,
    } = useMusicPlayerController()
    return (
        <>
            <audio data-testid="audio" ref={audioRef} {...audioHandlers} />
            <button type="button" onClick={previous}>Previous</button>
            <button type="button" onClick={next}>Next</button>
        </>
    )
}

let playMock: ReturnType<typeof vi.spyOn>
let pauseMock: ReturnType<typeof vi.spyOn>
let loadMock: ReturnType<typeof vi.spyOn>
let canPlayTypeMock: ReturnType<typeof vi.spyOn>
let originalApiBaseUrl: string

beforeEach(() => {
    originalApiBaseUrl = config.apiBaseUrl
    usePlayerStore.setState({
        queue: [],
        index: -1,
        playOrder: [],
        orderPosition: -1,
        shouldPlay: false,
        transportRequestId: 0,
        playbackStatus: "idle",
        currentTime: 0,
        duration: 0,
        volume: 0.9,
        shuffle: false,
        repeatMode: "off",
    })
    playMock = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue()
    pauseMock = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined)
    loadMock = vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => undefined)
    canPlayTypeMock = vi.spyOn(HTMLMediaElement.prototype, "canPlayType").mockReturnValue("probably")
})

afterEach(() => {
    playMock.mockRestore()
    pauseMock.mockRestore()
    loadMock.mockRestore()
    canPlayTypeMock.mockRestore()
    config.apiBaseUrl = originalApiBaseUrl
    vi.restoreAllMocks()
})

describe("useMusicPlayerController", () => {
    it("seeks the actual audio element when previous restarts a track", async () => {
        usePlayerStore.getState().setQueue([track("1")], 0, true)
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement
        audio.currentTime = 10
        act(() => usePlayerStore.getState().setTime(10))

        fireEvent.click(screen.getByRole("button", { name: "Previous" }))

        expect(audio.currentTime).toBe(0)
        expect(usePlayerStore.getState().currentTime).toBe(0)
        await waitFor(() => expect(playMock).toHaveBeenCalledTimes(1))
    })

    it("restarts the source for repeat-one instead of only resetting UI state", async () => {
        usePlayerStore.getState().setQueue([track("1")], 0, true)
        usePlayerStore.getState().cycleRepeat()
        usePlayerStore.getState().cycleRepeat()
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement
        audio.currentTime = 55

        fireEvent.click(screen.getByRole("button", { name: "Next" }))

        expect(audio.currentTime).toBe(0)
        expect(usePlayerStore.getState().currentTime).toBe(0)
        await waitFor(() => expect(playMock).toHaveBeenCalledTimes(2))
    })

    it("pauses the old source and loads the selected queue item", async () => {
        usePlayerStore.getState().setQueue([track("1"), track("2")], 0, true)
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement
        await waitFor(() => expect(audio.src).toContain("playback_id=1"))
        const pauseCalls = pauseMock.mock.calls.length

        fireEvent.click(screen.getByRole("button", { name: "Next" }))

        await waitFor(() => expect(audio.src).toContain("playback_id=2"))
        expect(pauseMock.mock.calls.length).toBeGreaterThan(pauseCalls)
        expect(usePlayerStore.getState().index).toBe(1)
    })

    it("marks a track without a playback id unavailable", async () => {
        usePlayerStore.getState().setQueue([{ ...track("1"), playbackId: null }], 0, true)
        render(<PlayerHarness />)

        await waitFor(() => expect(usePlayerStore.getState().playbackStatus).toBe("error"))
        expect(usePlayerStore.getState().shouldPlay).toBe(false)
        expect(playMock).not.toHaveBeenCalled()
    })

    it("explicitly seeks a single-track repeat-all queue on ended", async () => {
        usePlayerStore.getState().setQueue([track("1")], 0, true)
        usePlayerStore.getState().cycleRepeat()
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement
        audio.currentTime = 120

        fireEvent.ended(audio)

        expect(audio.currentTime).toBe(0)
        await waitFor(() => expect(playMock).toHaveBeenCalledTimes(2))
    })

    it("reloads duplicate queue entries that share the same track id", async () => {
        usePlayerStore.getState().setQueue([track("1"), track("1")], 0, true)
        render(<PlayerHarness />)
        const initialLoads = loadMock.mock.calls.length

        fireEvent.click(screen.getByRole("button", { name: "Next" }))

        await waitFor(() => expect(usePlayerStore.getState().index).toBe(1))
        expect(loadMock.mock.calls.length).toBeGreaterThan(initialLoads)
    })

    it("skips a failed track while preserving the rest of the queue", async () => {
        usePlayerStore.getState().setQueue([track("1"), track("2")], 0, true)
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement

        fireEvent.error(audio)

        await waitFor(() => expect(usePlayerStore.getState().index).toBe(1))
        await waitFor(() => expect(playMock).toHaveBeenCalledTimes(2))
    })

    it("stops after every queue entry fails without looping forever", async () => {
        usePlayerStore.getState().setQueue([track("1"), track("2")], 0, true)
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement

        fireEvent.play(audio)
        fireEvent.error(audio)
        await waitFor(() => expect(usePlayerStore.getState().index).toBe(1))
        fireEvent.play(audio)
        fireEvent.error(audio)

        await new Promise((resolve) => window.setTimeout(resolve, 20))
        expect(usePlayerStore.getState().index).toBe(1)
        expect(usePlayerStore.getState().playbackStatus).toBe("error")
        expect(playMock).toHaveBeenCalledTimes(2)
    })

    it("skips a source when play rejects before an error event", async () => {
        playMock
            .mockRejectedValueOnce(new Error("decode failed"))
            .mockResolvedValue(undefined)
        usePlayerStore.getState().setQueue([track("1"), track("2")], 0, true)

        render(<PlayerHarness />)

        await waitFor(() => expect(usePlayerStore.getState().index).toBe(1))
        await waitFor(() => expect(playMock).toHaveBeenCalledTimes(2))
    })

    it("uses a signed media ticket for cross-origin playback", async () => {
        config.apiBaseUrl = "https://media.example.test/api"
        vi.spyOn(playerRepo, "audioSource").mockResolvedValue({
            url: "/api/player/audio?playback_id=1&ticket=signed",
            mime_type: "audio/flac",
            directly_supported: true,
            known_unsupported: false,
            unsupported_reason: "",
        })
        usePlayerStore.getState().setQueue([track("1")], 0, true)

        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement

        await waitFor(() => expect(audio.src).toContain("ticket=signed"))
        expect(audio.src).not.toContain("token=")
    })

    it("renews an expired cross-origin media ticket once", async () => {
        config.apiBaseUrl = "https://media.example.test/api"
        vi.spyOn(playerRepo, "audioSource")
            .mockResolvedValueOnce({
                url: "/api/player/audio?playback_id=1&ticket=old",
                mime_type: "audio/flac",
                directly_supported: true,
                known_unsupported: false,
                unsupported_reason: "",
            })
            .mockResolvedValueOnce({
                url: "/api/player/audio?playback_id=1&ticket=new",
                mime_type: "audio/flac",
                directly_supported: true,
                known_unsupported: false,
                unsupported_reason: "",
            })
        usePlayerStore.getState().setQueue([track("1")], 0, true)
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement
        await waitFor(() => expect(audio.src).toContain("ticket=old"))

        fireEvent.error(audio)

        await waitFor(() => expect(audio.src).toContain("ticket=new"))
        expect(playerRepo.audioSource).toHaveBeenCalledTimes(2)
        expect(usePlayerStore.getState().index).toBe(0)
    })

    it("ignores a late error event from the previous source", async () => {
        usePlayerStore.getState().setQueue([track("1"), track("2")], 0, true)
        render(<PlayerHarness />)
        const audio = screen.getByTestId("audio") as HTMLAudioElement
        fireEvent.click(screen.getByRole("button", { name: "Next" }))
        await waitFor(() => expect(usePlayerStore.getState().index).toBe(1))
        Object.defineProperty(audio, "currentSrc", {
            configurable: true,
            value: "http://localhost/api/player/audio?playback_id=1",
        })

        fireEvent.error(audio)

        expect(usePlayerStore.getState().index).toBe(1)
        expect(usePlayerStore.getState().playbackStatus).not.toBe("error")
    })
})
