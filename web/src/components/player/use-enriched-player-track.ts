import { useCallback, useEffect, useState } from "react"
import { musicRepo, type MusicLyricsResource } from "@/api/music"
import type { PlayerTrack } from "@/stores/player"

export type TrackResourceStatus =
    | "idle"
    | "loading"
    | "ready"
    | "none"
    | "error"
    | "unavailable"

interface LyricsCacheEntry {
    patch: Partial<PlayerTrack>
    status: Extract<TrackResourceStatus, "ready" | "none">
    version: string
    fetchedAt: number
}

class LruCache<K, V> {
    private readonly values = new Map<K, V>()
    private readonly capacity: number

    constructor(capacity: number) {
        this.capacity = capacity
    }

    peek(key: K) {
        return this.values.get(key)
    }

    get(key: K) {
        const value = this.values.get(key)
        if (value === undefined) return undefined
        this.values.delete(key)
        this.values.set(key, value)
        return value
    }

    set(key: K, value: V) {
        this.values.delete(key)
        this.values.set(key, value)
        while (this.values.size > this.capacity) {
            const oldest = this.values.keys().next().value
            if (oldest === undefined) break
            this.values.delete(oldest)
        }
    }

    clear() {
        this.values.clear()
    }

    delete(key: K) {
        this.values.delete(key)
    }
}

const lyricsCache = new LruCache<string, LyricsCacheEntry>(256)
interface InFlightLyrics {
    promise: Promise<LyricsCacheEntry>
    controller: AbortController
}

const inFlight = new Map<string, InFlightLyrics>()
let cacheGeneration = 0
const LYRICS_CACHE_MS = 5 * 60_000

export function useEnrichedPlayerTrack(track: PlayerTrack | null) {
    const key = track?.playbackId || ""
    const staticStatus = trackResourceStatus(track)
    const cached = key ? lyricsCache.peek(key) : undefined
    const [remote, setRemote] = useState<{ key: string, status: TrackResourceStatus }>({
        key: "",
        status: "idle",
    })
    const [refreshVersion, setRefreshVersion] = useState(0)
    const status = staticStatus
        ?? cached?.status
        ?? (remote.key === key ? remote.status : "loading")
    const retry = useCallback(() => {
        if (!key) return
        lyricsCache.delete(key)
        inFlight.get(key)?.controller.abort()
        inFlight.delete(key)
        setRemote({ key, status: "loading" })
        setRefreshVersion((version) => version + 1)
    }, [key])

    useEffect(() => {
        if (
            !track
            || !key
            || staticStatus === "none"
            || staticStatus === "unavailable"
            || staticStatus === "idle"
        ) return
        const generation = cacheGeneration
        const cachedEntry = freshLyricsEntry(key)
        if (cachedEntry) {
            const remaining = Math.max(1, LYRICS_CACHE_MS - (Date.now() - cachedEntry.fetchedAt))
            const timer = window.setTimeout(() => {
                lyricsCache.delete(key)
                setRefreshVersion((version) => version + 1)
            }, remaining)
            return () => window.clearTimeout(timer)
        }
        let cancelled = false
        let refreshTimer: number | null = null
        void fetchLyrics(key).then((entry) => {
            if (cancelled || generation !== cacheGeneration) return
            lyricsCache.set(key, entry)
            setRemote({ key, status: entry.status })
            refreshTimer = window.setTimeout(() => {
                lyricsCache.delete(key)
                setRefreshVersion((version) => version + 1)
            }, LYRICS_CACHE_MS)
        }).catch(() => {
            if (!cancelled && generation === cacheGeneration) {
                setRemote({ key, status: "error" })
            }
        })
        return () => {
            cancelled = true
            if (refreshTimer != null) window.clearTimeout(refreshTimer)
        }
    }, [key, refreshVersion, staticStatus, track])

    return {
        status,
        retry,
        lyrics: cached?.patch.lyrics ?? track?.lyrics,
        syncedLyrics: cached?.patch.syncedLyrics ?? track?.syncedLyrics,
    }
}

export function usePrefetchEnrichedPlayerTracks(queue: PlayerTrack[], index: number) {
    useEffect(() => {
        const generation = cacheGeneration
        for (const track of queue.slice(index + 1, index + 3)) {
            const key = track.playbackId
            if (!key || track.hasLyrics === false || freshLyricsEntry(key) || inFlight.has(key)) {
                continue
            }
            void fetchLyrics(key).then((entry) => {
                if (generation === cacheGeneration) lyricsCache.set(key, entry)
            }).catch(() => undefined)
        }
    }, [index, queue])
}

export function clearPlayerTrackDetails() {
    cacheGeneration += 1
    lyricsCache.clear()
    for (const request of inFlight.values()) request.controller.abort()
    inFlight.clear()
}

function trackResourceStatus(track: PlayerTrack | null): TrackResourceStatus | null {
    if (!track) return "idle"
    if (!track.playbackId) return "unavailable"
    if (track.lyrics || track.syncedLyrics) return "ready"
    if (track.hasLyrics === false) return "none"
    return null
}

function fetchLyrics(playbackId: string) {
    const existing = inFlight.get(playbackId)
    if (existing) return existing.promise
    const controller = new AbortController()
    const request = fetchLyricsWithRetry(playbackId, controller.signal).finally(() => {
        if (inFlight.get(playbackId)?.promise === request) inFlight.delete(playbackId)
    })
    inFlight.set(playbackId, { promise: request, controller })
    return request
}

async function fetchLyricsWithRetry(playbackId: string, signal: AbortSignal) {
    const delays = [0, 2_000, 5_000, 15_000]
    let lastError: unknown
    for (const delay of delays) {
        if (delay > 0) await sleep(delay, signal)
        if (signal.aborted) throw new DOMException("Aborted", "AbortError")
        try {
            return lyricsEntry(await musicRepo.lyrics(playbackId, signal))
        } catch (error) {
            lastError = error
        }
    }
    throw lastError
}

function lyricsEntry(resource: MusicLyricsResource): LyricsCacheEntry {
    const patch = {
        lyrics: resource.lyrics || undefined,
        syncedLyrics: resource.synced_lyrics || undefined,
    }
    return {
        patch,
        status: patch.lyrics || patch.syncedLyrics ? "ready" : "none",
        version: resource.version,
        fetchedAt: Date.now(),
    }
}

function freshLyricsEntry(key: string) {
    const entry = lyricsCache.get(key)
    if (!entry) return undefined
    if (Date.now() - entry.fetchedAt < LYRICS_CACHE_MS) return entry
    lyricsCache.delete(key)
    return undefined
}

function sleep(duration: number, signal: AbortSignal) {
    return new Promise<void>((resolve, reject) => {
        const timer = window.setTimeout(resolve, duration)
        signal.addEventListener("abort", () => {
            window.clearTimeout(timer)
            reject(new DOMException("Aborted", "AbortError"))
        }, { once: true })
    })
}
