import type { MusicQuery, MusicTracksPage } from "@/api/music"
import type { PlayerTrack } from "@/stores/player"
import {
    beginMusicQueueRequest,
    isCurrentMusicQueueRequest,
} from "@/components/player/music-runtime"
import { loadMusicTracks } from "./music-library-loader"
import { trackFromSummary } from "./music-library-model"

type TrackPageLoader = (params: MusicQuery) => Promise<MusicTracksPage>

export async function loadMusicQueue(
    params: Omit<MusicQuery, "offset" | "limit">,
    loadPage: TrackPageLoader = loadMusicTracks,
): Promise<PlayerTrack[] | null> {
    const requestToken = beginMusicQueueRequest()
    const tracks: PlayerTrack[] = []
    let offset = 0
    let total = 1
    while (offset < total) {
        if (!isCurrentMusicQueueRequest(requestToken)) return null
        let page: MusicTracksPage
        try {
            page = await loadPage({ ...params, offset, limit: 200 })
        } catch (error) {
            if (!isCurrentMusicQueueRequest(requestToken)) return null
            throw error
        }
        if (!isCurrentMusicQueueRequest(requestToken)) return null
        tracks.push(...page.tracks.map(trackFromSummary))
        total = page.total
        offset += page.tracks.length
        if (page.tracks.length === 0) break
    }
    return tracks
}
