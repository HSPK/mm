import { usePlayerStore } from "@/stores/player"
import { clearMusicLibraryCache } from "@/components/music/music-library-loader"
import { clearPlayerTrackDetails } from "./use-enriched-player-track"
import { clearMusicMediaCache } from "./music-media-cache"

let runtimeGeneration = 0
let queueRequestGeneration = 0

export function resetMusicRuntime() {
    runtimeGeneration += 1
    queueRequestGeneration += 1
    usePlayerStore.getState().clearQueue()
    clearPlayerTrackDetails()
    clearMusicMediaCache()
    clearMusicLibraryCache()
    if ("mediaSession" in navigator) {
        navigator.mediaSession.metadata = null
        navigator.mediaSession.playbackState = "none"
    }
}

export function currentMusicRuntimeGeneration() {
    return runtimeGeneration
}

export function beginMusicQueueRequest() {
    return {
        runtime: runtimeGeneration,
        request: ++queueRequestGeneration,
    }
}

export function isCurrentMusicQueueRequest(token: { runtime: number, request: number }) {
    return token.runtime === runtimeGeneration && token.request === queueRequestGeneration
}
