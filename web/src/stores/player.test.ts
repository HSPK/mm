import { beforeEach, describe, expect, it } from "vitest"
import { createPlayerStore, type PlayerTrack } from "./player"

function track(id: string, duration = 0): PlayerTrack {
    return {
        id,
        path: `/music/${id}.flac`,
        playbackId: id,
        title: `Track ${id}`,
        artist: "Artist",
        album: "Album",
        duration,
    }
}

let store: ReturnType<typeof createPlayerStore>

beforeEach(() => {
    store = createPlayerStore({ random: () => 0 })
})

describe("player store", () => {
    it("separates a play request from observed playback state", () => {
        store.getState().setQueue([track("1")], 0, false)
        const requestId = store.getState().transportRequestId

        store.getState().requestPlay()

        expect(store.getState().shouldPlay).toBe(true)
        expect(store.getState().playbackStatus).toBe("loading")
        expect(store.getState().transportRequestId).toBe(requestId + 1)

        store.getState().markPlaybackStatus("paused")
        expect(store.getState().shouldPlay).toBe(true)
        expect(store.getState().playbackStatus).toBe("paused")
    })

    it("uses an explicitly supplied queue as the new playback context", () => {
        const firstQueue = [track("1"), track("2")]
        const secondQueue = [track("3"), track("4")]
        store.getState().setQueue(firstQueue, 0, true)

        store.getState().playTrack(secondQueue[1], secondQueue)

        expect(store.getState().queue.map((item) => item.id)).toEqual(["3", "4"])
        expect(store.getState().index).toBe(1)
        expect(store.getState().shouldPlay).toBe(true)
    })

    it("starts a new playback session when replacing the queue", () => {
        const queue = [track("1", 120), track("2")]
        store.getState().setQueue(queue, 0, true)
        store.getState().setTime(42)
        store.getState().setDuration(120)
        store.getState().markPlaybackStatus("playing")

        store.getState().setQueue([...queue, track("3")], 0, true)

        expect(store.getState().currentTime).toBe(0)
        expect(store.getState().duration).toBe(120)
        expect(store.getState().playbackStatus).toBe("loading")
    })

    it("can clear stale lyrics when detail resources are removed", () => {
        store.getState().setQueue([{ ...track("1"), lyrics: "old lyrics" }], 0, false)

        store.getState().updateTrack("1", { lyrics: undefined })

        expect(store.getState().queue[0].lyrics).toBeUndefined()
    })

    it("refreshes metadata when replaying an item already in the active queue", () => {
        store.getState().setQueue([track("1"), track("2")], 0, true)

        store.getState().playTrack({ ...track("2"), title: "Updated title" })

        expect(store.getState().queue[1].title).toBe("Updated title")
        expect(store.getState().index).toBe(1)
        expect(store.getState().playbackStatus).toBe("loading")
    })

    it("selects queue entries without rebuilding the queue", () => {
        store.getState().setQueue([track("1"), track("2"), track("3")], 0, true)
        const queue = store.getState().queue

        store.getState().selectQueueIndex(2, true, true)

        expect(store.getState().queue).toBe(queue)
        expect(store.getState().index).toBe(2)
        expect(store.getState().currentTime).toBe(0)
    })

    it("gives duplicate tracks distinct queue identities", () => {
        store.getState().setQueue([track("1"), track("1")], 0, true)

        expect(store.getState().queue[0].queueEntryId)
            .not.toBe(store.getState().queue[1].queueEntryId)
        store.getState().selectQueueIndex(1)
        expect(store.getState().index).toBe(1)
    })

    it("applies repeat-one only to natural endings", () => {
        store.getState().setQueue([track("1"), track("2")], 0, true)
        store.getState().cycleRepeat()
        store.getState().cycleRepeat()

        expect(store.getState().nextQueue("manual")).toBe("selected")
        expect(store.getState().index).toBe(1)
        expect(store.getState().nextQueue("ended")).toBe("restart")
    })

    it("finishes a shuffled queue after every entry when repeat is off", () => {
        store.getState().setQueue(
            [track("1"), track("2"), track("3"), track("4")],
            0,
            true,
        )
        store.getState().toggleShuffle()
        const visited = new Set([store.getState().queue[store.getState().index].queueEntryId])

        while (store.getState().nextQueue("ended") === "selected") {
            visited.add(store.getState().queue[store.getState().index].queueEntryId)
        }

        expect(visited.size).toBe(4)
        expect(store.getState().nextQueue("ended")).toBe("finish")
    })

    it("uses shuffle history for previous", () => {
        store.getState().setQueue([track("1"), track("2"), track("3")], 0, true)
        store.getState().toggleShuffle()
        store.getState().nextQueue("ended")
        const previousEntry = store.getState().queue[store.getState().index].queueEntryId
        store.getState().nextQueue("ended")

        expect(store.getState().previousQueue(0)).toBe("selected")
        expect(store.getState().queue[store.getState().index].queueEntryId).toBe(previousEntry)
    })

    it("starts an empty shuffled queue from the selected first item", () => {
        store.getState().toggleShuffle()
        store.getState().addToQueue([track("1"), track("2"), track("3")])
        const active = store.getState().queue[0]

        expect(store.getState().playOrder[0]).toBe(active.queueEntryId)
        expect(store.getState().orderPosition).toBe(0)
    })

    it("starts a fresh shuffle cycle after manually selecting an item", () => {
        store.getState().setQueue([track("1"), track("2"), track("3")], 0, true)
        store.getState().toggleShuffle()

        store.getState().selectQueueIndex(2, true, true)

        expect(store.getState().playOrder[0]).toBe(store.getState().queue[2].queueEntryId)
        expect(store.getState().orderPosition).toBe(0)
    })

    it("explicitly restarts a single-item repeat-all queue", () => {
        store.getState().setQueue([track("1")], 0, true)
        store.getState().cycleRepeat()

        expect(store.getState().nextQueue("ended")).toBe("restart")
    })

    it("updates runtime duration without rebuilding the queue", () => {
        store.getState().setQueue([track("1")], 0, true)
        const queue = store.getState().queue

        store.getState().setDuration(123.5)

        expect(store.getState().duration).toBe(123.5)
        expect(store.getState().queue).toBe(queue)
        expect(store.getState().queue[0].duration).toBe(0)
    })

    it("sanitizes media runtime values", () => {
        store.getState().setTime(Number.NaN)
        store.getState().setDuration(Number.POSITIVE_INFINITY)
        store.getState().setVolume(Number.NaN)

        expect(store.getState().currentTime).toBe(0)
        expect(store.getState().duration).toBe(0)
        expect(store.getState().volume).toBe(0.9)
    })
})
