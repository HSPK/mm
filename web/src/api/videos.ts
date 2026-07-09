import { api } from "@/api/client"

export type VideoLibraryKind = "movies" | "tv"

export interface VideoLibraryItem {
    path: string
    playback_id?: string | null
    media_type: "movie" | "tv" | string
    title: string
    year?: number | null
    season?: number | null
    episode?: number | null
    confidence: number
    is_new: boolean
    metadata: boolean
    metadata_title?: string | null
    metadata_original_title?: string | null
    metadata_show_title?: string | null
    metadata_year?: number | null
    metadata_premiered?: string | null
    metadata_certification?: string | null
    metadata_runtime?: number | null
    metadata_genres?: string[]
    metadata_status?: string | null
    metadata_countries?: string[]
    metadata_tagline?: string | null
    metadata_plot?: string | null
    metadata_tags?: string[]
    metadata_ids?: Record<string, string>
    metadata_rating?: number | null
    metadata_rating_source?: string | null
    metadata_studios?: string[]
    metadata_cast?: string[]
    images: boolean
    cover_path?: string | null
    subtitles: boolean
}

export interface VideoArtworkBatchItem {
    playback_id: string
    thumb_url?: string | null
    image_url?: string | null
}

export const videoRepo = {
    items: async (kind: VideoLibraryKind) =>
        (await api.get<{ items: VideoLibraryItem[] }>("/videos/items", { params: { kind } })).data.items,
    artworkBatch: async (playbackIds: string[], size = 320) =>
        (await api.post<{ items: VideoArtworkBatchItem[] }>("/videos/artwork/batch", {
            playback_ids: playbackIds,
            size,
        })).data.items,
}
