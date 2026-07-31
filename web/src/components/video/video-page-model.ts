import type { VideoLibraryItem } from "@/api/videos"
import { config } from "@/lib/config"

export type VideoPageKind = "movies" | "tv"

export interface ShowGroup {
    key: string
    id: string
    title: string
    year?: number | null
    episodes: VideoLibraryItem[]
    seasons: Array<{ season: number; episodes: VideoLibraryItem[] }>
    representative: VideoLibraryItem
}

export function filterVideoItems(items: VideoLibraryItem[], query: string) {
    const tokens = searchTokens(query)
    if (tokens.length === 0) return items
    return items.filter((item) => tokens.every((token) => itemMatchesToken(item, token)))
}

export function filterShows(shows: ShowGroup[], query: string) {
    const tokens = searchTokens(query)
    if (tokens.length === 0) return shows
    return shows.filter((show) => tokens.every((token) => (
        searchable(show.title).includes(token)
        || (show.year ? String(show.year).includes(token) : false)
        || show.episodes.some((episode) => itemMatchesToken(episode, token))
    )))
}

export function groupShows(items: VideoLibraryItem[]): ShowGroup[] {
    const groups = new Map<string, VideoLibraryItem[]>()
    for (const item of items) {
        const title = showTitle(item)
        groups.set(title, [...(groups.get(title) ?? []), item])
    }
    return Array.from(groups.entries())
        .map(([title, episodes]) => showGroup(title, episodes.sort(episodeSort)))
        .sort((a, b) => a.title.localeCompare(b.title) || (a.year ?? 0) - (b.year ?? 0))
}

export function videoTitle(item: VideoLibraryItem) {
    return item.metadata_title || item.title
}

export function showTitle(item: VideoLibraryItem) {
    return item.metadata_show_title || item.title
}

export function videoYear(item: VideoLibraryItem) {
    return item.metadata_year ?? item.year
}

export function ratingText(item: VideoLibraryItem) {
    if (item.metadata_rating == null) return ""
    return item.metadata_rating.toFixed(item.metadata_rating % 1 === 0 ? 0 : 1)
}

export function runtimeText(item: VideoLibraryItem) {
    const runtime = item.metadata_runtime
    if (!runtime) return ""
    const hours = Math.floor(runtime / 60)
    const minutes = runtime % 60
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
}

export function artworkUrlFromItem(item?: VideoLibraryItem, size = 420, kind?: string) {
    if (!item?.playback_id) return undefined
    const params = new URLSearchParams({ size: String(size) })
    if (kind) params.set("kind", kind)
    return `${config.apiBaseUrl}/videos/artwork/thumb/item/${encodeURIComponent(item.playback_id)}?${params.toString()}`
}

export function backdropUrlFromItem(item?: VideoLibraryItem) {
    if (!item?.playback_id) return undefined
    return `${config.apiBaseUrl}/videos/artwork/image/item/${encodeURIComponent(item.playback_id)}?kind=fanart`
}

export function logoUrlFromItem(item?: VideoLibraryItem) {
    if (!item?.playback_id) return undefined
    return `${config.apiBaseUrl}/videos/artwork/image/item/${encodeURIComponent(item.playback_id)}?kind=clearlogo`
}

export function itemSubtitle(item: VideoLibraryItem) {
    const parts = [
        videoYear(item) ? String(videoYear(item)) : "",
        runtimeText(item),
        item.subtitles ? "Subtitles" : "",
    ].filter(Boolean)
    return parts.join(" · ")
}

function showGroup(title: string, episodes: VideoLibraryItem[]): ShowGroup {
    const representative = episodes.find((item) => item.images || item.metadata) ?? episodes[0]
    const seasonMap = new Map<number, VideoLibraryItem[]>()
    for (const item of episodes) {
        const season = item.season ?? 0
        seasonMap.set(season, [...(seasonMap.get(season) ?? []), item])
    }
    return {
        key: title.toLowerCase(),
        id: representative.playback_id || title.toLowerCase(),
        title,
        year: episodes.find((item) => videoYear(item)) ? videoYear(episodes.find((item) => videoYear(item))!) : null,
        episodes,
        representative,
        seasons: Array.from(seasonMap.entries())
            .map(([season, rows]) => ({ season, episodes: rows.sort(episodeSort) }))
            .sort((a, b) => a.season - b.season),
    }
}

function episodeSort(a: VideoLibraryItem, b: VideoLibraryItem) {
    return (a.season ?? 0) - (b.season ?? 0)
        || (a.episode ?? 0) - (b.episode ?? 0)
        || videoTitle(a).localeCompare(videoTitle(b))
}

function itemMatchesToken(item: VideoLibraryItem, token: string) {
    return (
        searchable(videoTitle(item)).includes(token)
        || searchable(showTitle(item)).includes(token)
        || (videoYear(item) ? String(videoYear(item)).includes(token) : false)
        || (item.metadata_genres ?? []).some((genre) => searchable(genre).includes(token))
        || (item.metadata_cast ?? []).some((name) => searchable(name).includes(token))
    )
}

function searchTokens(query: string) {
    return searchable(query).split(/\s+/).filter(Boolean)
}

function searchable(value: string) {
    return value.trim().toLocaleLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
}
