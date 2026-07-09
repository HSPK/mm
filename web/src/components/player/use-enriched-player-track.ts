import { useEffect } from "react"
import { organizerRepo, type OrganizerItem } from "@/api/organizer"
import { usePlayerStore, type PlayerTrack } from "@/stores/player"
import { config } from "@/lib/config"

const detailCache = new Map<string, Partial<PlayerTrack>>()
const fetchedAt = new Map<string, number>()
const inFlight = new Map<string, Promise<Partial<PlayerTrack>>>()
const pendingTracks = new Map<string, PlayerTrack>()
const pendingResolvers = new Map<string, Array<(patch: Partial<PlayerTrack>) => void>>()
let flushTimer: number | null = null
const REFRESH_INTERVAL_MS = 60_000

export function useEnrichedPlayerTrack(track: PlayerTrack | null) {
    const updateTrack = usePlayerStore((state) => state.updateTrack)

    useEffect(() => {
        if (!track?.path || isComplete(track)) return
        const cached = detailCache.get(track.path)
        if (cached) {
            if (hasUsefulPatch(track, cached)) updateTrack(track.id, cached)
        }
        const lastFetch = fetchedAt.get(track.path) ?? 0
        if (Date.now() - lastFetch < REFRESH_INTERVAL_MS) {
            return
        }

        let cancelled = false
        void fetchTrackDetails(track)
            .then((patch) => {
                fetchedAt.set(track.path, Date.now())
                if (!hasUsefulPatch(track, patch)) return
                detailCache.set(track.path, patch)
                if (cancelled) return
                updateTrack(track.id, patch)
            })
            .catch(() => undefined)

        return () => {
            cancelled = true
        }
    }, [
        track?.album,
        track?.artist,
        track?.artworkUrl,
        track?.duration,
        track?.id,
        track?.lyrics,
        track?.path,
        track?.syncedLyrics,
        track?.title,
        updateTrack,
    ])
}

export function usePrefetchEnrichedPlayerTracks(queue: PlayerTrack[], index: number) {
    const updateTrack = usePlayerStore((state) => state.updateTrack)

    useEffect(() => {
        if (index < 0 || queue.length === 0) return
        const candidates = queue.slice(index + 1, index + 3).filter((track) => (
            track?.path && !isComplete(track) && shouldFetch(track.path)
        ))
        if (candidates.length === 0) return
        let cancelled = false
        for (const track of candidates) {
            void fetchTrackDetails(track)
                .then((patch) => {
                    fetchedAt.set(track.path, Date.now())
                    if (!hasUsefulPatch(track, patch)) return
                    detailCache.set(track.path, patch)
                    if (!cancelled) updateTrack(track.id, patch)
                })
                .catch(() => undefined)
        }
        return () => {
            cancelled = true
        }
    }, [index, queue, updateTrack])
}

function isComplete(track: PlayerTrack) {
    return Boolean(track.artworkUrl && (track.lyrics || track.syncedLyrics) && track.duration)
}

function shouldFetch(path: string) {
    return Date.now() - (fetchedAt.get(path) ?? 0) >= REFRESH_INTERVAL_MS
}

function hasUsefulPatch(track: PlayerTrack, patch: Partial<PlayerTrack>) {
    return Object.entries(patch).some(([key, value]) => (
        value != null
        && value !== ""
        && track[key as keyof PlayerTrack] !== value
    ))
}

function fetchTrackDetails(track: PlayerTrack) {
    const existing = inFlight.get(track.path)
    if (existing) return existing
    const request = new Promise<Partial<PlayerTrack>>((resolve) => {
        const key = track.path
        pendingTracks.set(key, track)
        pendingResolvers.set(key, [...(pendingResolvers.get(key) ?? []), resolve])
        if (flushTimer != null) return
        flushTimer = window.setTimeout(() => {
            flushTimer = null
            void flushTrackDetails()
        }, 40)
    }).finally(() => {
        inFlight.delete(track.path)
    })
    inFlight.set(track.path, request)
    return request
}

async function flushTrackDetails() {
    const tracks = Array.from(pendingTracks.values())
    const resolvers = new Map(pendingResolvers)
    pendingTracks.clear()
    pendingResolvers.clear()
    if (tracks.length === 0) return
    try {
        const items = await organizerRepo.details(tracks.map(organizerItemFromTrack))
        const byPath = new Map(items.map((item) => [item.path, item]))
        for (const track of tracks) {
            const patch = patchFromOrganizerItem(byPath.get(track.path), track)
            for (const resolve of resolvers.get(track.path) ?? []) resolve(patch)
        }
    } catch {
        for (const track of tracks) {
            for (const resolve of resolvers.get(track.path) ?? []) resolve({})
        }
    }
}

export function primePlayerTrackDetails(tracks: PlayerTrack[]) {
    const targets = tracks.filter((track) => (
        track.path && !isComplete(track) && shouldFetch(track.path)
    ))
    if (targets.length === 0) return
    void organizerRepo.details(targets.map(organizerItemFromTrack))
        .then((items) => {
            for (const item of items) {
                const track = targets.find((candidate) => candidate.path === item.path)
                if (!track) continue
                const patch = patchFromOrganizerItem(item, track)
                if (!hasUsefulPatch(track, patch)) continue
                fetchedAt.set(track.path, Date.now())
                detailCache.set(track.path, patch)
            }
        })
        .catch(() => undefined)
}

function organizerItemFromTrack(track: PlayerTrack): OrganizerItem {
    return {
        path: track.path,
        playback_id: track.playbackId,
        media_type: "track",
        title: track.title || basename(track.path),
        artist: track.artist,
        album: track.album,
        year: track.year,
        disc: track.discNumber,
        track: track.trackNumber,
        confidence: 1,
        is_new: false,
        metadata: false,
        images: Boolean(track.artworkUrl),
        subtitles: false,
        lyrics: Boolean(track.lyrics || track.syncedLyrics),
    }
}

function patchFromOrganizerItem(item: OrganizerItem | undefined, current: PlayerTrack): Partial<PlayerTrack> {
    if (!item) return {}
    return {
        title: item.metadata_title || item.title || current.title,
        playbackId: item.playback_id || current.playbackId,
        artist: item.artist || current.artist,
        album: item.album || current.album,
        artworkUrl: artworkUrlFromItem(item) || current.artworkUrl,
        lyrics: item.metadata_lyrics || current.lyrics,
        syncedLyrics: item.metadata_synced_lyrics || current.syncedLyrics,
        discNumber: item.disc ?? current.discNumber,
        trackNumber: item.track ?? current.trackNumber,
        year: item.metadata_year ?? item.year ?? current.year,
        duration: item.media_info?.duration ?? current.duration,
    }
}

function artworkUrlFromItem(item: OrganizerItem) {
    if (!item.playback_id) return undefined
    const params = new URLSearchParams({ size: "512" })
    return `${config.apiBaseUrl}/organizer/artwork/thumb/item/${encodeURIComponent(item.playback_id)}?${params.toString()}`
}

function basename(path: string) {
    return path.split(/[\\/]/).pop() ?? path
}
