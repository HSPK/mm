import { api } from "@/api/client"

export interface VideoState {
    playback_id: string
    favorite: boolean
    watched: boolean
    notes: string
    progress: number
    duration: number
    updated_at: string
}

export interface VideoStatePatch {
    playback_id: string
    favorite?: boolean
    watched?: boolean
    notes?: string
    progress?: number
    duration?: number
}

export interface VideoTrack {
    index: number
    label: string
    language: string
    codec: string
    default: boolean
    forced: boolean
    url?: string | null
}

export interface VideoPlaybackSource {
    mode: "direct" | "hls" | string
    url: string
    mime_type: string
    audio_tracks: VideoTrack[]
    subtitle_tracks: VideoTrack[]
    selected_audio_stream?: number | null
    preserves_video: boolean
}

export const playerRepo = {
    videoSource: async (playbackId: string, audioStream?: number | null) =>
        (await api.get<VideoPlaybackSource>("/player/video/source", {
            params: { playback_id: playbackId, audio_stream: audioStream ?? undefined },
        })).data,
    videoStates: async () => (await api.get<VideoState[]>("/player/video/states")).data,
    videoState: async (playbackId: string) =>
        (await api.get<VideoState>("/player/video/state", { params: { playback_id: playbackId } })).data,
    updateVideoState: async (patch: VideoStatePatch) =>
        (await api.patch<VideoState>("/player/video/state", patch)).data,
    videoPreviewUrl: (playbackId: string, time: number) => {
        const params = new URLSearchParams({
            playback_id: playbackId,
            time: String(Math.max(0, Math.floor(time / 10) * 10)),
        })
        return `${api.defaults.baseURL ?? "/api"}/player/video/preview?${params.toString()}`
    },
}
