import { act, renderHook, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { usePlayerStore, type PlayerTrack } from "@/stores/player"
import { useMediaQueryStore } from "@/stores/media-query"
import { useAuthStore } from "@/stores/auth"
import { useLibraryEvents } from "./use-library-events"

const track: PlayerTrack = {
    id: "1",
    playbackId: "1",
    title: "Track",
    artist: "Artist",
    album: "Album",
    hasLyrics: false,
}

class FakeEventSource {
    static instance: FakeEventSource | null = null
    onmessage: ((event: MessageEvent<string>) => void) | null = null

    constructor() {
        FakeEventSource.instance = this
    }

    close() {}

    emit(data: object) {
        this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>)
    }
}

beforeEach(() => {
    vi.stubGlobal("EventSource", FakeEventSource)
    usePlayerStore.getState().clearQueue()
    useMediaQueryStore.setState({ fetchMedia: vi.fn(async () => undefined) })
    useAuthStore.setState({
        token: "token",
        user: { id: 1, username: "admin", display_name: "Admin", is_admin: true },
        loading: false,
        fetchUser: vi.fn(async () => undefined),
    })
})

afterEach(() => {
    vi.unstubAllGlobals()
    FakeEventSource.instance = null
})

describe("useLibraryEvents", () => {
    it("clears playback when another client switches the global library", async () => {
        usePlayerStore.getState().setQueue([track], 0, true)
        const changed = vi.fn()
        window.addEventListener("mm:library-changed", changed)
        renderHook(() => useLibraryEvents())

        act(() => FakeEventSource.instance?.emit({ generation: 0, library_id: "one" }))
        expect(usePlayerStore.getState().queue).toHaveLength(1)

        act(() => FakeEventSource.instance?.emit({ generation: 1, library_id: "two" }))
        expect(usePlayerStore.getState().queue).toEqual([])
        await waitFor(() => expect(changed).toHaveBeenCalledTimes(1))
        window.removeEventListener("mm:library-changed", changed)
    })
})
