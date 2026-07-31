import { create } from "zustand"

export interface PlayerTrack {
    id: string
    path?: string
    playbackId?: string | null
    title: string
    artist: string
    album: string
    artworkUrl?: string
    lyrics?: string
    syncedLyrics?: string
    hasLyrics?: boolean
    mimeType?: string | null
    playable?: boolean
    unavailableReason?: string
    discNumber?: number | null
    trackNumber?: number | null
    year?: number | null
    duration?: number | null
}

export interface PlayerQueueItem extends PlayerTrack {
    queueEntryId: string
}

export type RepeatMode = "off" | "all" | "one"
export type PlaybackStatus = "idle" | "loading" | "playing" | "paused" | "error"
export type QueueAdvanceReason = "manual" | "ended"
export type QueueTransition = "restart" | "selected" | "finish" | "none"

const queueIndexCache = new WeakMap<PlayerQueueItem[], Map<string, number>>()

export interface PlayerState {
    queue: PlayerQueueItem[]
    index: number
    playOrder: string[]
    orderPosition: number
    shouldPlay: boolean
    transportRequestId: number
    playbackStatus: PlaybackStatus
    currentTime: number
    duration: number
    volume: number
    shuffle: boolean
    repeatMode: RepeatMode
    setQueue: (queue: PlayerTrack[], index?: number, play?: boolean) => void
    selectQueueIndex: (index: number, play?: boolean, restart?: boolean) => void
    playTrack: (track: PlayerTrack, queue?: PlayerTrack[]) => void
    playNext: (tracks: PlayerTrack | PlayerTrack[]) => void
    addToQueue: (tracks: PlayerTrack | PlayerTrack[]) => void
    nextQueue: (reason: QueueAdvanceReason) => QueueTransition
    previousQueue: (currentTime: number) => QueueTransition
    clearQueue: () => void
    requestPlay: () => void
    requestPause: () => void
    failPlayback: () => void
    finishPlayback: (position?: number) => void
    markPlaybackStatus: (status: PlaybackStatus) => void
    toggleShuffle: () => void
    cycleRepeat: () => void
    updateTrack: (id: string, patch: Partial<PlayerTrack>) => void
    setTime: (time: number) => void
    setDuration: (duration: number) => void
    setVolume: (volume: number) => void
}

interface PlayerStoreOptions {
    random?: () => number
}

export function createPlayerStore(options: PlayerStoreOptions = {}) {
    const random = options.random ?? Math.random
    let queueSequence = 0
    const makeQueueItem = (track: PlayerTrack): PlayerQueueItem => ({
        ...track,
        queueEntryId: `queue-${++queueSequence}`,
    })

    return create<PlayerState>((set, get) => ({
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
        setQueue: (tracks, index = 0, play = true) => set((state) => {
            const metadata = existingTrackMetadata(state.queue)
            const queue = tracks.map((track) => makeQueueItem(
                mergeTrackMetadata(track, metadata.get(track.id)),
            ))
            if (queue.length === 0) return clearedPlayerState(state)
            const nextIndex = clampIndex(index, queue.length)
            const nextTrack = queue[nextIndex]
            const shouldPlay = play
            const playOrder = state.shuffle
                ? shuffledOrder(queue, nextTrack.queueEntryId, random)
                : queue.map((track) => track.queueEntryId)
            return {
                queue,
                index: nextIndex,
                playOrder,
                orderPosition: playOrder.indexOf(nextTrack.queueEntryId),
                shouldPlay,
                transportRequestId: state.transportRequestId + 1,
                playbackStatus: shouldPlay ? "loading" : "paused",
                currentTime: 0,
                duration: sanitizeDuration(nextTrack.duration),
            }
        }),
        selectQueueIndex: (index, play = true, restart = true) => set((state) => {
            if (state.queue.length === 0) return state
            const nextIndex = clampIndex(index, state.queue.length)
            const nextTrack = state.queue[nextIndex]
            const sameEntry = nextTrack.queueEntryId === currentTrack(state)?.queueEntryId
            const playOrder = state.shuffle && restart && !sameEntry
                ? shuffledOrder(state.queue, nextTrack.queueEntryId, random)
                : normalizedPlayOrder(state)
            const orderPosition = playOrder.indexOf(nextTrack.queueEntryId)
            return {
                index: nextIndex,
                playOrder,
                orderPosition,
                shouldPlay: play,
                transportRequestId: state.transportRequestId + 1,
                playbackStatus: play ? "loading" : "paused",
                currentTime: sameEntry && !restart ? state.currentTime : 0,
                duration: sameEntry && !restart
                    ? state.duration
                    : sanitizeDuration(nextTrack.duration),
            }
        }),
        playTrack: (track, queue) => {
            if (queue?.length) {
                const index = queue.findIndex((item) => item.id === track.id)
                get().setQueue(queue, index >= 0 ? index : 0, true)
                return
            }
            const state = get()
            const existingIndex = state.queue.findIndex((item) => item.id === track.id)
            if (existingIndex >= 0) {
                set((current) => ({
                    queue: replaceQueueTrack(
                        current.queue,
                        existingIndex,
                        mergeTrackMetadata(track, current.queue[existingIndex]),
                    ),
                }))
                get().selectQueueIndex(existingIndex, true, existingIndex !== state.index)
                return
            }
            if (state.queue.length === 0 || state.index < 0) {
                get().setQueue([track], 0, true)
                return
            }
            const item = makeQueueItem(track)
            set((current) => insertAfterCurrent(current, [item], true))
        },
        playNext: (tracks) => {
            const incoming = Array.isArray(tracks) ? tracks : [tracks]
            if (incoming.length === 0) return
            const state = get()
            const metadata = existingTrackMetadata(state.queue)
            const items = incoming.map((track) => makeQueueItem(
                mergeTrackMetadata(track, metadata.get(track.id)),
            ))
            if (state.queue.length === 0 || state.index < 0) {
                get().setQueue(items, 0, true)
                return
            }
            set((current) => insertAfterCurrent(current, items, false))
        },
        addToQueue: (tracks) => {
            const incoming = Array.isArray(tracks) ? tracks : [tracks]
            if (incoming.length === 0) return
            const state = get()
            const metadata = existingTrackMetadata(state.queue)
            const items = incoming.map((track) => makeQueueItem(
                mergeTrackMetadata(track, metadata.get(track.id)),
            ))
            if (state.queue.length === 0 || state.index < 0) {
                set((current) => {
                    const playOrder = current.shuffle
                        ? shuffledOrder(items, items[0].queueEntryId, random)
                        : items.map((item) => item.queueEntryId)
                    return {
                        queue: items,
                        index: 0,
                        playOrder,
                        orderPosition: playOrder.indexOf(items[0].queueEntryId),
                        shouldPlay: false,
                        playbackStatus: "paused",
                        currentTime: 0,
                        duration: sanitizeDuration(items[0].duration),
                    }
                })
                return
            }
            set((current) => {
                const ids = items.map((item) => item.queueEntryId)
                return {
                    queue: [...current.queue, ...items],
                    playOrder: [
                        ...normalizedPlayOrder(current),
                        ...(current.shuffle ? shuffledIds(ids, random) : ids),
                    ],
                }
            })
        },
        nextQueue: (reason) => {
            const state = get()
            const active = currentTrack(state)
            if (!active) return "none"
            if (reason === "ended" && state.repeatMode === "one") return "restart"

            let playOrder = normalizedPlayOrder(state)
            let orderPosition = state.orderPosition
            if (playOrder[orderPosition] !== active.queueEntryId) {
                orderPosition = playOrder.indexOf(active.queueEntryId)
            }
            if (orderPosition + 1 < playOrder.length) {
                const entryId = playOrder[orderPosition + 1]
                const index = queueIndexByEntryId(state.queue, entryId)
                if (index < 0) return "none"
                set(selectionState(state, index, playOrder, orderPosition + 1))
                return "selected"
            }

            if (state.repeatMode === "off") return "finish"
            if (state.shuffle) {
                playOrder = shuffledIds(
                    state.queue.map((item) => item.queueEntryId),
                    random,
                )
                avoidFirstRepeat(playOrder, active.queueEntryId)
            } else {
                playOrder = state.queue.map((item) => item.queueEntryId)
            }
            const nextEntryId = playOrder[0]
            if (!nextEntryId || nextEntryId === active.queueEntryId) return "restart"
            const index = queueIndexByEntryId(state.queue, nextEntryId)
            if (index < 0) return "none"
            set(selectionState(state, index, playOrder, 0))
            return "selected"
        },
        previousQueue: (position) => {
            const state = get()
            const active = currentTrack(state)
            if (!active) return "none"
            if (position > 3) return "restart"
            const playOrder = normalizedPlayOrder(state)
            const orderPosition = playOrder.indexOf(active.queueEntryId)
            if (orderPosition <= 0) return "restart"
            const entryId = playOrder[orderPosition - 1]
            const index = queueIndexByEntryId(state.queue, entryId)
            if (index < 0) return "none"
            set(selectionState(state, index, playOrder, orderPosition - 1))
            return "selected"
        },
        clearQueue: () => set((state) => clearedPlayerState(state)),
        requestPlay: () => set((state) => {
            if (!currentTrack(state)) return state
            return {
                shouldPlay: true,
                transportRequestId: state.transportRequestId + 1,
                playbackStatus: state.playbackStatus === "playing" ? "playing" : "loading",
            }
        }),
        requestPause: () => set((state) => ({
            shouldPlay: false,
            transportRequestId: state.transportRequestId + 1,
        })),
        failPlayback: () => set({
            shouldPlay: false,
            playbackStatus: "error",
        }),
        finishPlayback: (position) => set((state) => ({
            shouldPlay: false,
            playbackStatus: "paused",
            currentTime: sanitizeTime(position ?? state.duration),
        })),
        markPlaybackStatus: (playbackStatus) => set({ playbackStatus }),
        toggleShuffle: () => set((state) => {
            const shuffle = !state.shuffle
            const active = currentTrack(state)
            if (!active) return { shuffle, playOrder: [], orderPosition: -1 }
            const playOrder = shuffle
                ? shuffledOrder(state.queue, active.queueEntryId, random)
                : state.queue.map((item) => item.queueEntryId)
            return {
                shuffle,
                playOrder,
                orderPosition: playOrder.indexOf(active.queueEntryId),
            }
        }),
        cycleRepeat: () => set((state) => ({
            repeatMode: state.repeatMode === "off" ? "all" : state.repeatMode === "all" ? "one" : "off",
        })),
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
        setTime: (currentTime) => set({ currentTime: sanitizeTime(currentTime) }),
        setDuration: (duration) => set({ duration: sanitizeDuration(duration) }),
        setVolume: (volume) => set({ volume: sanitizeVolume(volume) }),
    }))
}

export const usePlayerStore = createPlayerStore()

export function currentTrack(state: Pick<PlayerState, "queue" | "index">) {
    return state.index >= 0 ? state.queue[state.index] ?? null : null
}

function insertAfterCurrent(
    state: PlayerState,
    items: PlayerQueueItem[],
    selectInserted: boolean,
): Partial<PlayerState> {
    const insertAt = Math.max(0, state.index + 1)
    const queue = [
        ...state.queue.slice(0, insertAt),
        ...items,
        ...state.queue.slice(insertAt),
    ]
    const playOrder = normalizedPlayOrder(state)
    const orderPosition = playOrder.indexOf(currentTrack(state)?.queueEntryId ?? "")
    const itemIds = items.map((item) => item.queueEntryId)
    const nextOrder = [
        ...playOrder.slice(0, orderPosition + 1),
        ...itemIds,
        ...playOrder.slice(orderPosition + 1),
    ]
    if (!selectInserted) return { queue, playOrder: nextOrder }
    return {
        queue,
        index: insertAt,
        playOrder: nextOrder,
        orderPosition: orderPosition + 1,
        shouldPlay: true,
        transportRequestId: state.transportRequestId + 1,
        playbackStatus: "loading",
        currentTime: 0,
        duration: sanitizeDuration(items[0]?.duration),
    }
}

function selectionState(
    state: PlayerState,
    index: number,
    playOrder: string[],
    orderPosition: number,
): Partial<PlayerState> {
    return {
        index,
        playOrder,
        orderPosition,
        shouldPlay: true,
        transportRequestId: state.transportRequestId + 1,
        playbackStatus: "loading",
        currentTime: 0,
        duration: sanitizeDuration(state.queue[index]?.duration),
    }
}

function clearedPlayerState(state: PlayerState): Partial<PlayerState> {
    return {
        queue: [],
        index: -1,
        playOrder: [],
        orderPosition: -1,
        shouldPlay: false,
        transportRequestId: state.transportRequestId + 1,
        playbackStatus: "idle",
        currentTime: 0,
        duration: 0,
    }
}

function normalizedPlayOrder(state: Pick<PlayerState, "queue" | "playOrder">) {
    if (state.playOrder.length === state.queue.length) return state.playOrder
    return state.queue.map((item) => item.queueEntryId)
}

function shuffledOrder(
    queue: PlayerQueueItem[],
    currentEntryId: string,
    random: () => number,
) {
    return [
        currentEntryId,
        ...shuffledIds(
            queue
                .map((item) => item.queueEntryId)
                .filter((id) => id !== currentEntryId),
            random,
        ),
    ]
}

function shuffledIds(ids: string[], random: () => number) {
    const result = [...ids]
    for (let index = result.length - 1; index > 0; index -= 1) {
        const swapIndex = Math.floor(random() * (index + 1))
        const value = result[index]
        result[index] = result[swapIndex]
        result[swapIndex] = value
    }
    return result
}

function avoidFirstRepeat(order: string[], currentEntryId: string) {
    if (order.length <= 1 || order[0] !== currentEntryId) return
    const first = order[0]
    order[0] = order[1]
    order[1] = first
}

function existingTrackMetadata(queue: PlayerQueueItem[]) {
    return new Map(queue.map((track) => [track.id, track]))
}

function mergeTrackMetadata(track: PlayerTrack, prior?: PlayerTrack): PlayerTrack {
    if (!prior) return track
    return {
        ...track,
        artworkUrl: track.artworkUrl ?? prior.artworkUrl,
        lyrics: track.lyrics ?? prior.lyrics,
        syncedLyrics: track.syncedLyrics ?? prior.syncedLyrics,
        hasLyrics: track.hasLyrics ?? prior.hasLyrics,
        duration: track.duration ?? prior.duration,
        playbackId: track.playbackId ?? prior.playbackId,
        mimeType: track.mimeType ?? prior.mimeType,
        playable: track.playable ?? prior.playable,
        unavailableReason: track.unavailableReason ?? prior.unavailableReason,
        discNumber: track.discNumber ?? prior.discNumber,
        trackNumber: track.trackNumber ?? prior.trackNumber,
        year: track.year ?? prior.year,
    }
}

function replaceQueueTrack(
    queue: PlayerQueueItem[],
    index: number,
    track: PlayerTrack,
) {
    return queue.map((item, itemIndex) => (
        itemIndex === index ? { ...item, ...track, queueEntryId: item.queueEntryId } : item
    ))
}

function mergeTrackPatch(track: PlayerQueueItem, patch: Partial<PlayerTrack>) {
    const changed = Object.entries(patch).some(([key, value]) => (
        track[key as keyof PlayerTrack] !== value
    ))
    return changed ? { ...track, ...patch } : track
}

function queueIndexByEntryId(queue: PlayerQueueItem[], entryId: string) {
    let index = queueIndexCache.get(queue)
    if (!index) {
        index = new Map(queue.map((item, itemIndex) => [item.queueEntryId, itemIndex]))
        queueIndexCache.set(queue, index)
    }
    return index.get(entryId) ?? -1
}

function clampIndex(index: number, length: number) {
    return Math.min(Math.max(index, 0), Math.max(0, length - 1))
}

function sanitizeTime(value: number) {
    return Number.isFinite(value) ? Math.max(0, value) : 0
}

function sanitizeDuration(value?: number | null) {
    return value != null && Number.isFinite(value) && value > 0 ? value : 0
}

function sanitizeVolume(value: number) {
    return Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0.9
}
