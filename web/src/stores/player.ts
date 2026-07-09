import { create } from "zustand"

export interface PlayerTrack {
    id: string
    path: string
    playbackId?: string | null
    title: string
    artist: string
    album: string
    artworkUrl?: string
    lyrics?: string
    syncedLyrics?: string
    discNumber?: number | null
    trackNumber?: number | null
    year?: number | null
    duration?: number | null
}

export type RepeatMode = "off" | "all" | "one"

interface PlayerState {
    queue: PlayerTrack[]
    index: number
    isPlaying: boolean
    currentTime: number
    duration: number
    volume: number
    shuffle: boolean
    repeatMode: RepeatMode
    playCounts: Record<string, number>
    recentTrackIds: string[]
    setQueue: (queue: PlayerTrack[], index?: number, play?: boolean) => void
    playTrack: (track: PlayerTrack, queue?: PlayerTrack[]) => void
    playNext: (tracks: PlayerTrack | PlayerTrack[]) => void
    addToQueue: (tracks: PlayerTrack | PlayerTrack[]) => void
    play: () => void
    pause: () => void
    toggle: () => void
    next: () => void
    previous: () => void
    toggleShuffle: () => void
    cycleRepeat: () => void
    registerPlay: (track: PlayerTrack) => void
    updateTrack: (id: string, patch: Partial<PlayerTrack>) => void
    setTime: (time: number) => void
    setDuration: (duration: number) => void
    setVolume: (volume: number) => void
}

const initialStats = loadPlayStats()

export const usePlayerStore = create<PlayerState>((set, get) => ({
    queue: [],
    index: -1,
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    volume: 0.9,
    shuffle: false,
    repeatMode: "off",
    playCounts: initialStats.playCounts,
    recentTrackIds: initialStats.recentTrackIds,
    setQueue: (queue, index = 0, play = true) => set((state) => {
        const enrichedQueue = mergeExistingTrackMetadata(queue, state.queue)
        const nextIndex = enrichedQueue.length > 0 ? Math.min(Math.max(index, 0), enrichedQueue.length - 1) : -1
        const nextTrack = nextIndex >= 0 ? enrichedQueue[nextIndex] : null
        const current = currentTrack(state)
        const sameTrack = Boolean(nextTrack && current && nextTrack.id === current.id)
        return {
            queue: enrichedQueue,
            index: nextIndex,
            isPlaying: play && queue.length > 0,
            currentTime: sameTrack ? state.currentTime : 0,
            duration: sameTrack ? state.duration : 0,
        }
    }),
    playTrack: (track, queue) => {
        const state = get()
        if (state.queue.length > 0 && state.index >= 0) {
            set((state) => playTrackInActiveQueue(state, track))
            return
        }
        const nextQueue = queue?.length ? queue : [track]
        const index = nextQueue.findIndex((item) => item.id === track.id)
        get().setQueue(nextQueue, index >= 0 ? index : 0, true)
    },
    playNext: (tracks) => set((state) => {
        const items = mergeExistingTrackMetadata(
            Array.isArray(tracks) ? tracks : [tracks],
            state.queue,
        )
        if (items.length === 0) return state
        if (state.queue.length === 0 || state.index < 0) {
            return { queue: items, index: 0, isPlaying: true, currentTime: 0, duration: 0 }
        }
        const insertAt = Math.max(0, state.index + 1)
        return {
            queue: [
                ...state.queue.slice(0, insertAt),
                ...items,
                ...state.queue.slice(insertAt),
            ],
        }
    }),
    addToQueue: (tracks) => set((state) => {
        const items = mergeExistingTrackMetadata(
            Array.isArray(tracks) ? tracks : [tracks],
            state.queue,
        )
        if (items.length === 0) return state
        if (state.queue.length === 0 || state.index < 0) {
            return { queue: items, index: 0 }
        }
        return { queue: [...state.queue, ...items] }
    }),
    play: () => set({ isPlaying: true }),
    pause: () => set({ isPlaying: false }),
    toggle: () => set((state) => ({ isPlaying: !state.isPlaying })),
    next: () => set((state) => {
        if (state.queue.length === 0) return state
        if (state.repeatMode === "one") return { currentTime: 0, duration: 0, isPlaying: true }
        const nextIndex = state.shuffle
            ? randomQueueIndex(state.queue.length, state.index)
            : state.index + 1
        if (nextIndex >= state.queue.length) {
            if (state.repeatMode === "all") {
                return { index: 0, currentTime: 0, duration: 0, isPlaying: true }
            }
            return { index: state.queue.length - 1, currentTime: 0, duration: 0, isPlaying: false }
        }
        const index = nextIndex
        return { index, currentTime: 0, duration: 0, isPlaying: true }
    }),
    previous: () => set((state) => {
        if (state.queue.length === 0) return state
        if (state.currentTime > 3) return { currentTime: 0 }
        const index = Math.max(state.index - 1, 0)
        return { index, currentTime: 0, duration: 0, isPlaying: true }
    }),
    toggleShuffle: () => set((state) => ({ shuffle: !state.shuffle })),
    cycleRepeat: () => set((state) => ({
        repeatMode: state.repeatMode === "off" ? "all" : state.repeatMode === "all" ? "one" : "off",
    })),
    registerPlay: (track) => set((state) => {
        const playCounts = {
            ...state.playCounts,
            [track.id]: (state.playCounts[track.id] ?? 0) + 1,
        }
        const recentTrackIds = [track.id, ...state.recentTrackIds.filter((id) => id !== track.id)].slice(0, 200)
        savePlayStats({ playCounts, recentTrackIds })
        return { playCounts, recentTrackIds }
    }),
    updateTrack: (id, patch) => set((state) => {
        let changed = false
        const queue = state.queue.map((track) => {
            if (track.id !== id) return track
            const next = mergeTrackPatch(track, patch)
            if (next !== track) changed = true
            return next
        })
        return changed ? { queue } : state
    }),
    setTime: (currentTime) => set({ currentTime }),
    setDuration: (duration) => set({ duration }),
    setVolume: (volume) => set({ volume: Math.min(1, Math.max(0, volume)) }),
}))

export function currentTrack(state: Pick<PlayerState, "queue" | "index">) {
    return state.index >= 0 ? state.queue[state.index] ?? null : null
}

function randomQueueIndex(length: number, current: number) {
    if (length <= 1) return current
    let next = Math.floor(Math.random() * length)
    if (next === current) next = (next + 1) % length
    return next
}

function mergeExistingTrackMetadata(incoming: PlayerTrack[], existing: PlayerTrack[]) {
    const existingById = new Map(existing.map((track) => [track.id, track]))
    return incoming.map((track) => {
        const prior = existingById.get(track.id)
        if (!prior) return track
        return {
            ...track,
            artworkUrl: track.artworkUrl ?? prior.artworkUrl,
            lyrics: track.lyrics ?? prior.lyrics,
            syncedLyrics: track.syncedLyrics ?? prior.syncedLyrics,
            duration: track.duration ?? prior.duration,
            playbackId: track.playbackId ?? prior.playbackId,
            discNumber: track.discNumber ?? prior.discNumber,
            trackNumber: track.trackNumber ?? prior.trackNumber,
            year: track.year ?? prior.year,
        }
    })
}

function playTrackInActiveQueue(
    state: PlayerState,
    track: PlayerTrack,
): Partial<PlayerState> {
    const incoming = mergeExistingTrackMetadata([track], state.queue)[0]
    const existingIndex = state.queue.findIndex((item) => item.id === incoming.id)
    const sameTrack = existingIndex === state.index
    if (sameTrack) {
        return { isPlaying: true }
    }
    if (existingIndex >= 0) {
        return {
            index: existingIndex,
            isPlaying: true,
            currentTime: 0,
            duration: 0,
        }
    }
    const insertAt = Math.max(0, state.index + 1)
    return {
        queue: [
            ...state.queue.slice(0, insertAt),
            incoming,
            ...state.queue.slice(insertAt),
        ],
        index: insertAt,
        isPlaying: true,
        currentTime: 0,
        duration: 0,
    }
}

function mergeTrackPatch(track: PlayerTrack, patch: Partial<PlayerTrack>) {
    const changed = Object.entries(patch).some(([key, value]) => (
        track[key as keyof PlayerTrack] !== value
    ))
    return changed ? { ...track, ...patch } : track
}

function loadPlayStats() {
    if (typeof window === "undefined") return { playCounts: {}, recentTrackIds: [] }
    try {
        const raw = window.localStorage.getItem("mm:music-play-stats")
        if (!raw) return { playCounts: {}, recentTrackIds: [] }
        const value = JSON.parse(raw) as { playCounts?: Record<string, number>, recentTrackIds?: string[] }
        return {
            playCounts: value.playCounts ?? {},
            recentTrackIds: value.recentTrackIds ?? [],
        }
    } catch {
        return { playCounts: {}, recentTrackIds: [] }
    }
}

function savePlayStats(stats: { playCounts: Record<string, number>, recentTrackIds: string[] }) {
    if (typeof window === "undefined") return
    window.localStorage.setItem("mm:music-play-stats", JSON.stringify(stats))
}
