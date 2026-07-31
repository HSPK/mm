import {
    musicRepo,
    type MusicAlbumsPage,
    type MusicArtistsPage,
    type MusicQuery,
    type MusicRepository,
    type MusicTracksPage,
} from "@/api/music"

type MusicLibraryRepository = Pick<MusicRepository, "albums" | "tracks" | "artists">

export const MUSIC_ALBUM_PAGE_SIZE = 50
export const MUSIC_TRACK_PAGE_SIZE = 100
export const MUSIC_ARTIST_PAGE_SIZE = 100

export interface MusicLibraryData {
    albums: MusicAlbumsPage
    tracks: MusicTracksPage
    artists: MusicArtistsPage
}

interface CachedRequest {
    createdAt: number
    promise: Promise<unknown>
}

const requestCache = new Map<string, CachedRequest>()
const REQUEST_CACHE_MS = 30_000

export async function loadMusicLibrary(
    query = "",
    repo: MusicLibraryRepository = musicRepo,
): Promise<MusicLibraryData> {
    const params = query ? { query } : undefined
    const [albums, tracks, artists] = await Promise.all([
        loadMusicAlbums({ ...params, offset: 0, limit: MUSIC_ALBUM_PAGE_SIZE }, repo),
        loadMusicTracks({ ...params, offset: 0, limit: MUSIC_TRACK_PAGE_SIZE }, repo),
        loadMusicArtists({ ...params, offset: 0, limit: MUSIC_ARTIST_PAGE_SIZE }, repo),
    ])
    return { albums, tracks, artists }
}

export function loadMusicAlbums(
    params: MusicQuery,
    repo: MusicLibraryRepository = musicRepo,
) {
    return cachedRequest("albums", params, () => repo.albums(params))
}

export function loadMusicTracks(
    params: MusicQuery,
    repo: MusicLibraryRepository = musicRepo,
) {
    return cachedRequest("tracks", params, () => repo.tracks(params))
}

export function loadMusicArtists(
    params: MusicQuery,
    repo: MusicLibraryRepository = musicRepo,
) {
    return cachedRequest("artists", params, () => repo.artists(params))
}

export function clearMusicLibraryCache() {
    requestCache.clear()
}

function cachedRequest<T>(
    kind: string,
    params: MusicQuery,
    request: () => Promise<T>,
): Promise<T> {
    const key = `${kind}:${JSON.stringify(params)}`
    const existing = requestCache.get(key)
    if (existing && Date.now() - existing.createdAt < REQUEST_CACHE_MS) {
        return existing.promise as Promise<T>
    }
    requestCache.delete(key)
    const pending: Promise<T> = request().catch((error) => {
        if (requestCache.get(key)?.promise === pending) requestCache.delete(key)
        throw error
    })
    requestCache.set(key, { createdAt: Date.now(), promise: pending })
    trimCache()
    return pending
}

function trimCache() {
    while (requestCache.size > 30) {
        const oldest = requestCache.keys().next().value
        if (oldest === undefined) return
        requestCache.delete(oldest)
    }
}
