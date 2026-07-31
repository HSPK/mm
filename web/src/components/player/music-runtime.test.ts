import { beforeEach, describe, expect, it } from "vitest"
import { usePlayerStore, type PlayerTrack } from "@/stores/player"
import { currentMusicRuntimeGeneration, resetMusicRuntime } from "./music-runtime"

const track: PlayerTrack = {
    id: "1",
    playbackId: "1",
    title: "Track",
    artist: "Artist",
    album: "Album",
    hasLyrics: false,
}

beforeEach(() => {
    usePlayerStore.getState().clearQueue()
})

describe("resetMusicRuntime", () => {
    it("stops and clears playback when the active library changes", () => {
        usePlayerStore.getState().setQueue([track], 0, true)
        const generation = currentMusicRuntimeGeneration()

        resetMusicRuntime()

        expect(usePlayerStore.getState().queue).toEqual([])
        expect(usePlayerStore.getState().index).toBe(-1)
        expect(usePlayerStore.getState().shouldPlay).toBe(false)
        expect(usePlayerStore.getState().playbackStatus).toBe("idle")
        expect(currentMusicRuntimeGeneration()).toBe(generation + 1)
    })
})
