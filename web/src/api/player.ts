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

export interface VideoMediaInfo {
    video_codec: string
    audio_codec: string
    width?: number | null
    height?: number | null
    hdr: string
    bit_depth?: number | null
    frame_rate?: number | null
}

export interface VideoPlaybackSource {
    mode: "direct" | "unsupported" | string
    url: string
    mime_type: string
    audio_tracks: VideoTrack[]
    subtitle_tracks: VideoTrack[]
    selected_audio_stream?: number | null
    preserves_video: boolean
    playable: boolean
    unsupported_reason: string
    media_info?: VideoMediaInfo | null
}

export interface AudioPlaybackSource {
    url: string
    mime_type: string
    directly_supported: boolean
    known_unsupported: boolean
    unsupported_reason: string
}

export const playerRepo = {
    audioSource: async (playbackId: string) =>
        (await api.get<AudioPlaybackSource>("/player/audio/source", {
            params: { playback_id: playbackId },
        })).data,
    videoSource: async (playbackId: string, audioStream?: number | null, refresh?: boolean) =>
        (await api.get<VideoPlaybackSource>("/player/video/source", {
            params: { playback_id: playbackId, audio_stream: audioStream ?? undefined, refresh: refresh || undefined },
        })).data,
    videoStates: async () => (await api.get<VideoState[]>("/player/video/states")).data,
    videoState: async (playbackId: string) =>
        (await api.get<VideoState>("/player/video/state", { params: { playback_id: playbackId } })).data,
    updateVideoState: async (patch: VideoStatePatch) =>
        (await api.patch<VideoState>("/player/video/state", patch)).data,
}
