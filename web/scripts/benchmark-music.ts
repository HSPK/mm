import { performance } from "node:perf_hooks"
import { createPlayerStore, type PlayerTrack } from "../src/stores/player"

const count = Number(process.argv[2] ?? 50_000)
const tracks: PlayerTrack[] = Array.from({ length: count }, (_, index) => ({
    id: String(index + 1),
    playbackId: String(index + 1),
    title: `Track ${index + 1}`,
    artist: `Artist ${Math.floor(index / 100)}`,
    album: `Album ${Math.floor(index / 10)}`,
    duration: 180,
    hasLyrics: index % 4 === 0,
    mimeType: "audio/mpeg",
    playable: true,
}))

const store = createPlayerStore({ random: () => 0.42 })
const setQueueStarted = performance.now()
store.getState().setQueue(tracks, 0, true)
const setQueueMs = performance.now() - setQueueStarted

store.getState().cycleRepeat()
const transitions = Math.min(10_000, Math.max(1, count - 1))
const transitionStarted = performance.now()
for (let index = 0; index < transitions; index += 1) {
    store.getState().nextQueue("ended")
}
const transitionMs = performance.now() - transitionStarted

const durationStarted = performance.now()
for (let index = 0; index < 10_000; index += 1) {
    store.getState().setDuration(180 + index % 2)
}
const durationMs = performance.now() - durationStarted

const metadataStarted = performance.now()
for (let index = 0; index < 100; index += 1) {
    store.getState().updateTrack(String(index + 1), { lyrics: `Lyrics ${index}` })
}
const metadataMs = performance.now() - metadataStarted

console.log(JSON.stringify({
    tracks: count,
    setQueueMs: Number(setQueueMs.toFixed(2)),
    transitions,
    transitionMs: Number(transitionMs.toFixed(2)),
    durationUpdates: 10_000,
    durationMs: Number(durationMs.toFixed(2)),
    metadataUpdates: 100,
    metadataMs: Number(metadataMs.toFixed(2)),
}, null, 2))
