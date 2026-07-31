import {
    type MusicAlbum,
    type MusicArtist,
    type MusicTrack,
} from "@/api/music"
import { type PlayerTrack } from "@/stores/player"
import { config } from "@/lib/config"

export interface AlbumGroup {
    key: string
    id: string
    artistId: string
    title: string
    artist: string
    year?: number | null
    count: number
    artworkUrl?: string
    tracks: PlayerTrack[]
}

export interface ArtistGroup {
    id: string
    name: string
    tracks: PlayerTrack[]
    albums: number
    trackCount: number
    artworkUrl?: string
}

export function buildAlbumGroups(summaries: MusicAlbum[]): AlbumGroup[] {
    return summaries.map(albumFromSummary)
}

export function buildArtistGroups(summaries: MusicArtist[]): ArtistGroup[] {
    return summaries.map((artist) => ({
        id: artist.artist_id,
        name: artist.name,
        tracks: [],
        albums: artist.album_count,
        trackCount: artist.track_count,
        artworkUrl: artworkUrlFromPlaybackId(artist.cover_playback_id),
    }))
}

export function albumFromSummary(album: MusicAlbum): AlbumGroup {
    return {
        key: album.album_id,
        id: album.album_id,
        artistId: album.artist_id,
        title: album.title,
        artist: album.artist,
        year: album.year,
        count: album.count,
        artworkUrl: artworkUrlFromPlaybackId(album.cover_playback_id),
        tracks: [],
    }
}

export function trackFromSummary(track: MusicTrack): PlayerTrack {
    const playable = isKnownBrowserPlayable(track.mime_type)
    return {
        id: track.playback_id || [
            "unavailable",
            track.artist || "",
            track.album || "",
            track.title,
        ].join(":"),
        playbackId: track.playback_id,
        title: stripRedundantArtistPrefix(track.title, track.artist),
        artist: track.artist || "Unknown Artist",
        album: track.album || "Unknown Album",
        artworkUrl: artworkUrlFromPlaybackId(track.playback_id),
        hasLyrics: track.lyrics,
        mimeType: track.mime_type,
        playable,
        unavailableReason: playable
            ? undefined
            : `${track.title} uses an audio format that browsers cannot play directly.`,
        discNumber: track.disc,
        trackNumber: track.track,
        year: track.year,
        duration: track.duration,
    }
}

export function trackSort(a: PlayerTrack, b: PlayerTrack) {
    return a.artist.localeCompare(b.artist)
        || a.album.localeCompare(b.album)
        || albumTrackSort(a, b)
}

export function albumTrackSort(a: PlayerTrack, b: PlayerTrack) {
    return (a.discNumber ?? 0) - (b.discNumber ?? 0)
        || (a.trackNumber ?? 9999) - (b.trackNumber ?? 9999)
        || a.title.localeCompare(b.title)
}

export function shuffleTracks(tracks: PlayerTrack[]) {
    const copy = [...tracks]
    for (let index = copy.length - 1; index > 0; index -= 1) {
        const swapIndex = Math.floor(Math.random() * (index + 1))
        const value = copy[index]
        copy[index] = copy[swapIndex]
        copy[swapIndex] = value
    }
    return copy
}

function isKnownBrowserPlayable(mimeType?: string | null) {
    return mimeType !== "audio/x-ms-wma" && mimeType !== "audio/aiff"
}

function artworkUrlFromPlaybackId(playbackId?: string | null) {
    if (!playbackId) return undefined
    const params = new URLSearchParams({ size: "320" })
    return `${config.apiBaseUrl}/music/artwork/${encodeURIComponent(playbackId)}/thumbnail?${params.toString()}`
}

function stripRedundantArtistPrefix(title: string, artist?: string | null) {
    const normalizedArtist = artist?.trim()
    if (!normalizedArtist) return title
    const escaped = normalizedArtist.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    return title.replace(new RegExp(`^${escaped}(?:\\s*[-–—:]\\s*|\\s+)(.+)$`, "i"), "$1").trim()
}
