import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"

export interface MusicTrack {
    track_id: string
    playback_id?: string | null
    title: string
    artist?: string | null
    album?: string | null
    year?: number | null
    disc?: number | null
    track?: number | null
    metadata: boolean
    images: boolean
    lyrics: boolean
    duration?: number | null
    mime_type?: string | null
    title_variants?: Record<string, string>
    artist_variants?: Record<string, string>
    album_variants?: Record<string, string>
}

export interface MusicAlbum {
    album_id: string
    artist_id: string
    album_artist_id: string
    key: string
    title: string
    artist: string
    year?: number | null
    count: number
    cover_playback_id?: string | null
    title_variants?: Record<string, string>
    artist_variants?: Record<string, string>
}

export interface MusicArtist {
    artist_id: string
    name: string
    album_count: number
    track_count: number
    cover_playback_id?: string | null
    name_variants?: Record<string, string>
}

export interface MusicAlbumsPage {
    albums: MusicAlbum[]
    offset: number
    limit: number
    total: number
}

export interface MusicTracksPage {
    tracks: MusicTrack[]
    offset: number
    limit: number
    total: number
}

export interface MusicArtistsPage {
    artists: MusicArtist[]
    offset: number
    limit: number
    total: number
}

export interface MusicLyricsResource {
    playback_id: string
    lyrics: string
    synced_lyrics: string
    version: string
}

export interface MusicQuery {
    offset?: number
    limit?: number
    query?: string
    album_id?: string
    artist_id?: string
}

export interface MusicRepository {
    albums(params?: MusicQuery): Promise<MusicAlbumsPage>
    album(albumId: string): Promise<MusicAlbum>
    tracks(params?: MusicQuery): Promise<MusicTracksPage>
    artists(params?: MusicQuery): Promise<MusicArtistsPage>
    artist(artistId: string): Promise<MusicArtist>
    lyrics(playbackId: string, signal?: AbortSignal): Promise<MusicLyricsResource>
}

export function createMusicRepository(api: AxiosInstance = defaultApi): MusicRepository {
    return {
        albums: async (params) =>
            (await api.get<MusicAlbumsPage>("/music/albums", { params })).data,
        album: async (albumId) =>
            (await api.get<MusicAlbum>(`/music/albums/${encodeURIComponent(albumId)}`)).data,
        tracks: async (params) =>
            (await api.get<MusicTracksPage>("/music/tracks", { params })).data,
        artists: async (params) =>
            (await api.get<MusicArtistsPage>("/music/artists", { params })).data,
        artist: async (artistId) =>
            (await api.get<MusicArtist>(`/music/artists/${encodeURIComponent(artistId)}`)).data,
        lyrics: async (playbackId, signal) =>
            (await api.get<MusicLyricsResource>(
                `/music/tracks/${encodeURIComponent(playbackId)}/lyrics`,
                { signal },
            )).data,
    }
}

export const musicRepo = createMusicRepository()
