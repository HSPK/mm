import type { VideoLibraryItem } from "@/api/videos"
import type { ShowGroup } from "./video-page-model"
import { readVideoState } from "./video-user-state"

export type VideoFilter = "all" | "favorites" | "unwatched"

export function filterCollectionMovies(items: VideoLibraryItem[], collection: string) {
    if (collection === "All") return items
    return items.filter((item) => {
        const state = readVideoState(item.playback_id)
        if (collection === "Favorites") return state.favorite
        if (collection === "Unwatched") return !state.watched
        return item.metadata_genres?.some((genre) => genre.trim() === collection) ?? false
    })
}

export function filterCollectionShows(shows: ShowGroup[], collection: string) {
    if (collection === "All") return shows
    return shows.filter((show) => {
        const states = show.episodes.map((episode) => readVideoState(episode.playback_id))
        if (collection === "Favorites") return states.some((state) => state.favorite)
        if (collection === "Unwatched") return states.some((state) => !state.watched)
        return show.episodes.some((episode) => (
            episode.metadata_genres?.some((genre) => genre.trim() === collection) ?? false
        ))
    })
}

export function hasProgress(item: VideoLibraryItem) {
    const state = readVideoState(item.playback_id)
    return state.progress > 30 && (!state.duration || state.progress < state.duration - 60)
}

export function showHasProgress(show: ShowGroup) {
    return show.episodes.some(hasProgress)
}

export function recentItems(items: VideoLibraryItem[]) {
    return [...items]
        .sort((a, b) => Number(b.is_new) - Number(a.is_new) || videoPathName(a).localeCompare(videoPathName(b)))
        .slice(0, 14)
}

export function recentShowsList(shows: ShowGroup[]) {
    return [...shows]
        .sort((a, b) => (
            Number(b.episodes.some((episode) => episode.is_new))
            - Number(a.episodes.some((episode) => episode.is_new))
            || a.title.localeCompare(b.title)
        ))
        .slice(0, 14)
}

export function collectionNames(items: VideoLibraryItem[]) {
    const names = new Set<string>()
    for (const item of items) {
        for (const genre of item.metadata_genres ?? []) {
            if (genre.trim()) names.add(genre.trim())
            if (names.size >= 8) break
        }
        if (names.size >= 8) break
    }
    return [...names]
}

function videoPathName(item: VideoLibraryItem) {
    return item.path.split(/[\\/]/).pop() ?? item.path
}
