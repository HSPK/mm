import {
    organizerRepo,
    type OrganizerItem,
    type OrganizerMusicAlbum,
    type OrganizerMusicTrack,
} from "@/api/organizer"
import { type PlayerTrack } from "@/stores/player"
import { config } from "@/lib/config"

export interface AlbumGroup {
    key: string
    title: string
    artist: string
    year?: number | null
    artworkUrl?: string
    tracks: PlayerTrack[]
}

export interface ArtistGroup {
    name: string
    tracks: PlayerTrack[]
    albums: number
    artworkUrl?: string
}

export async function loadMusicDetailsByAlbum(
    items: OrganizerItem[],
    onDetails: (items: OrganizerItem[]) => void,
) {
    const albums = Array.from(groupItemsByAlbumDirectory(items).values())
    const flatItems = albums.flat()
    for (let index = 0; index < flatItems.length; index += 80) {
        const batch = flatItems.slice(index, index + 80)
        try {
            onDetails(await organizerRepo.details(batch))
        } catch {
            // Details enrichment is best-effort; summaries remain usable.
        }
    }
}

export function buildAlbumGroups(
    summaries: OrganizerMusicAlbum[],
    items: OrganizerItem[],
): AlbumGroup[] {
    const itemsByPath = new Map(items.map((item) => [item.path, item]))
    const summaryAlbums = summaries.map((album) => ({
        key: album.key,
        title: album.title,
        artist: album.artist,
        year: album.year,
        artworkUrl: artworkUrlFromPlaybackId(album.cover_playback_id),
        tracks: album.tracks
            .map((track) => trackFromSummary(track, itemsByPath.get(track.path), artworkUrlFromPlaybackId(album.cover_playback_id)))
            .sort(trackSort),
    }))
    if (summaryAlbums.length > 0) {
        return summaryAlbums.sort(albumSort)
    }
    return fallbackAlbums(items)
}

export function groupArtists(albums: AlbumGroup[]): ArtistGroup[] {
    const map = new Map<string, { tracks: PlayerTrack[], albums: number, artworkUrl?: string }>()
    for (const album of albums) {
        const entry = map.get(album.artist) ?? { tracks: [], albums: 0, artworkUrl: album.artworkUrl }
        entry.tracks.push(...album.tracks)
        entry.albums += 1
        entry.artworkUrl ||= album.artworkUrl
        map.set(album.artist, entry)
    }
    return Array.from(map.entries()).map(([name, value]) => ({
        name,
        tracks: value.tracks.sort(trackSort),
        albums: value.albums,
        artworkUrl: value.artworkUrl,
    })).sort((a, b) => a.name.localeCompare(b.name))
}

export function filterAlbums(albums: AlbumGroup[], query: string) {
    const tokens = searchTokens(query)
    if (tokens.length === 0) return albums
    return albums.filter((album) => tokens.every((token) => (
        searchable(album.title).includes(token)
        || searchable(album.artist).includes(token)
        || (album.year ? String(album.year).includes(token) : false)
        || album.tracks.some((track) => trackMatchesToken(track, token))
    )))
}

export function filterTracks(tracks: PlayerTrack[], query: string) {
    const tokens = searchTokens(query)
    if (tokens.length === 0) return tracks
    return tracks.filter((track) => tokens.every((token) => trackMatchesToken(track, token)))
}

export function mergeOrganizerItems(current: OrganizerItem[], updates: OrganizerItem[]) {
    const byPath = new Map(updates.map((item) => [item.path, item]))
    return current.map((item) => {
        const update = byPath.get(item.path)
        if (!update) return item
        return {
            ...update,
            playback_id: update.playback_id ?? item.playback_id,
            cover_path: update.cover_path ?? item.cover_path,
        }
    })
}

export function trackSort(a: PlayerTrack, b: PlayerTrack) {
    return a.album.localeCompare(b.album)
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

function fallbackAlbums(items: OrganizerItem[]): AlbumGroup[] {
    const grouped = groupItemsByAlbumDirectory(items)
    return Array.from(grouped.entries()).map(([key, rows]) => ({
        key,
        title: rows[0]?.album || rows[0]?.metadata_title || rows[0]?.title || "Unknown Album",
        artist: rows[0]?.artist || "Unknown Artist",
        year: rows.find((row) => row.metadata_year || row.year)?.metadata_year ?? rows[0]?.year,
        artworkUrl: artworkUrlFromItem(rows[0]),
        tracks: rows.map(trackFromItem).sort(trackSort),
    })).sort(albumSort)
}

function groupItemsByAlbumDirectory(items: OrganizerItem[]) {
    const map = new Map<string, OrganizerItem[]>()
    for (const item of items) {
        const key = musicAlbumDirectory(item.path)
        const rows = map.get(key)
        if (rows) rows.push(item)
        else map.set(key, [item])
    }
    return map
}

function trackFromSummary(
    track: OrganizerMusicTrack,
    detail?: OrganizerItem,
    albumArtworkUrl?: string,
): PlayerTrack {
    if (detail) return trackFromItem(detail)
    return {
        id: track.path,
        path: track.path,
        playbackId: track.playback_id,
        title: stripRedundantArtistPrefix(track.title || basename(track.path), track.artist),
        artist: track.artist || "Unknown Artist",
        album: track.album || "Unknown Album",
        artworkUrl: albumArtworkUrl,
        discNumber: track.disc,
        trackNumber: track.track,
        year: track.year,
    }
}

function trackFromItem(item: OrganizerItem): PlayerTrack {
    return {
        id: item.path,
        path: item.path,
        playbackId: item.playback_id,
        title: stripRedundantArtistPrefix(item.metadata_title || item.title || basename(item.path), item.artist),
        artist: item.artist || "Unknown Artist",
        album: item.album || "Unknown Album",
        artworkUrl: artworkUrlFromItem(item),
        lyrics: item.metadata_lyrics || undefined,
        syncedLyrics: item.metadata_synced_lyrics || undefined,
        discNumber: item.disc,
        trackNumber: item.track,
        year: item.metadata_year ?? item.year,
        duration: item.media_info?.duration,
    }
}

function trackMatchesToken(track: PlayerTrack, token: string) {
    return (
        searchable(track.title).includes(token)
        || searchable(track.artist).includes(token)
        || searchable(track.album).includes(token)
        || (track.year ? String(track.year).includes(token) : false)
    )
}

function searchTokens(query: string) {
    return searchable(query).split(/\s+/).filter(Boolean)
}

function searchable(value: string) {
    return value.trim().toLocaleLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
}

function musicAlbumDirectory(path: string) {
    const parts = path.split(/[\\/]/)
    parts.pop()
    if (parts.length > 0 && /^cd\s*\d+$/i.test(parts[parts.length - 1] ?? "")) {
        parts.pop()
    }
    return parts.join("/")
}

function artworkUrlFromItem(item?: OrganizerItem) {
    return artworkUrlFromPlaybackId(item?.playback_id)
}

function artworkUrlFromPlaybackId(playbackId?: string | null) {
    if (!playbackId) return undefined
    const params = new URLSearchParams({ size: "320" })
    return `${config.apiBaseUrl}/organizer/artwork/thumb/item/${encodeURIComponent(playbackId)}?${params.toString()}`
}

function albumSort(a: AlbumGroup, b: AlbumGroup) {
    return a.artist.localeCompare(b.artist) || a.title.localeCompare(b.title)
}

function basename(path: string) {
    return path.split(/[\\/]/).pop() ?? path
}

function stripRedundantArtistPrefix(title: string, artist?: string | null) {
    const normalizedArtist = artist?.trim()
    if (!normalizedArtist) return title
    const escaped = normalizedArtist.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    return title.replace(new RegExp(`^${escaped}(?:\\s*[-–—:]\\s*|\\s+)(.+)$`, "i"), "$1").trim()
}
