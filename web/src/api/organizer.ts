import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"

export interface OrganizerItem {
    path: string
    playback_id?: string | null
    media_type: "movie" | "tv" | "album" | "track" | string
    title: string
    artist?: string | null
    album?: string | null
    year?: number | null
    season?: number | null
    episode?: number | null
    episode_end?: number | null
    disc?: number | null
    track?: number | null
    parse_template?: string | null
    parse_relative_path?: string | null
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
    metadata_styles?: string[]
    metadata_composers?: string[]
    metadata_status?: string | null
    metadata_countries?: string[]
    metadata_tagline?: string | null
    metadata_plot?: string | null
    metadata_lyrics?: string | null
    metadata_synced_lyrics?: string | null
    metadata_tags?: string[]
    metadata_ids?: Record<string, string>
    metadata_rating?: number | null
    metadata_rating_source?: string | null
    metadata_studios?: string[]
    metadata_cast?: string[]
    images: boolean
    cover_path?: string | null
    artwork?: OrganizerArtworkAsset[]
    subtitles: boolean
    lyrics: boolean
    related_files?: OrganizerFileAsset[]
    media_info?: OrganizerMediaInfo | null
}

export interface OrganizerFileAsset {
    kind: string
    path: string
    name: string
    extension: string
    size?: number | null
}

export interface OrganizerArtworkAsset {
    kind: string
    path: string
    playback_id?: string | null
    label: string
    width?: number | null
    height?: number | null
}

export interface OrganizerStreamInfo {
    source: string
    codec: string
    channels: string
    bit_rate?: number | null
    bit_depth?: number | null
    language: string
    default: boolean
    forced: boolean
    title: string
    format: string
}

export interface OrganizerMediaInfo {
    duration?: number | null
    width?: number | null
    height?: number | null
    aspect_ratio: string
    video_codec: string
    frame_rate?: number | null
    video_bit_rate?: number | null
    video_bit_depth?: number | null
    hdr_format: string
    audio_streams: OrganizerStreamInfo[]
    subtitle_streams: OrganizerStreamInfo[]
}

export interface OrganizerCandidate {
    source: string
    source_id: string
    media_type: string
    title: string
    original_title: string
    show_title: string
    artist: string
    album: string
    year?: number | null
    disc?: number | null
    track?: number | null
    overview: string
    poster_url: string
    backdrop_url: string
    logo_url: string
    trailer_url: string
    release_date: string
    certification: string
    runtime?: number | null
    status: string
    original_language: string
    genres: string[]
    styles: string[]
    countries: string[]
    studios: string[]
    tags: string[]
    composers: string[]
    external_ids: Record<string, string>
    cast: Array<Record<string, string>>
    crew: Array<Record<string, string>>
    lyrics: string
    synced_lyrics: string
    rating?: number | null
    confidence: number
}

export interface OrganizerMatchResult {
    item: OrganizerItem
    candidates: OrganizerCandidate[]
}

export interface OrganizerLyricsCandidate {
    source: string
    source_id: string
    title: string
    artist: string
    album: string
    duration?: number | null
    lyrics: string
    synced_lyrics: string
    confidence: number
}

export interface OrganizerLibraryEntry {
    key: string
    media_type: string
    title: string
    subtitle: string
    count: number
    cover_id?: number | null
    year?: number | null
    artist?: string | null
    album?: string | null
}

export interface OrganizerLibrary {
    movies: OrganizerLibraryEntry[]
    tv: OrganizerLibraryEntry[]
    music: OrganizerLibraryEntry[]
}

export interface OrganizerMusicTrack {
    playback_id?: string | null
    path: string
    title: string
    artist?: string | null
    album?: string | null
    year?: number | null
    disc?: number | null
    track?: number | null
    metadata: boolean
    images: boolean
    lyrics: boolean
}

export interface OrganizerMusicAlbum {
    key: string
    title: string
    artist: string
    year?: number | null
    count: number
    cover_path?: string | null
    cover_playback_id?: string | null
    tracks: OrganizerMusicTrack[]
}

export interface OrganizerRenameOperation {
    source: string
    target: string
    media_type: string
    status: string
    reason: string
}

export interface OrganizerRenamePlan {
    root: string
    operations: OrganizerRenameOperation[]
    ready: number
    conflicts: number
}

export interface OrganizerNfoOperation {
    target: string
    media_type: string
    status: string
    reason: string
}

export interface OrganizerArtworkOperation extends OrganizerNfoOperation {
    source_url: string
}

export interface OrganizerSourceStatus {
    name: string
    enabled: boolean
    implemented: boolean
    has_credentials: boolean
    base_url: string
    priority: number
}

export interface OrganizerConfig {
    language: string
    chinese_script: "simplified" | "traditional" | string
    lyrics_source: "lrclib" | "netease" | "qq" | "all" | string
    timeout: number
    order: string[]
    sources: OrganizerSourceStatus[]
    templates: Record<string, string>
    default_scrapers: Record<string, string>
    media_sources: Record<string, string[]>
}

export interface OrganizerApplyResponse {
    affected: number
    message: string
    batch_id?: string | null
}

export interface OrganizerRenameLogEntry {
    batch_id: string
    created_at: string
    count: number
    status: string
}

export interface OrganizerArtworkBatchItem {
    playback_id: string
    thumb_url?: string | null
    image_url?: string | null
}

export interface OrganizerRepository {
    getConfig(): Promise<OrganizerConfig>
    updateConfig(patch: Record<string, unknown>): Promise<OrganizerConfig>
    library(): Promise<OrganizerLibrary>
    musicAlbums(): Promise<OrganizerMusicAlbum[]>
    items(kind?: string): Promise<OrganizerItem[]>
    details(items: OrganizerItem[]): Promise<OrganizerItem[]>
    mediaInfo(playbackId: string): Promise<OrganizerMediaInfo | null>
    lyricsSearch(input: { path: string, title: string, artist?: string | null, album?: string | null, source?: string, limit?: number }): Promise<OrganizerLyricsCandidate[]>
    lyricsApply(input: { path: string, lyrics?: string, synced_lyrics?: string, overwrite?: boolean }): Promise<OrganizerApplyResponse>
    scan(paths: string[], recursive: boolean): Promise<OrganizerItem[]>
    match(items: OrganizerItem[], source?: string, limit?: number, language?: string): Promise<OrganizerMatchResult[]>
    renamePlan(items: OrganizerItem[], root?: string): Promise<OrganizerRenamePlan>
    renameApply(items: OrganizerItem[], root?: string): Promise<OrganizerApplyResponse>
    renameLogs(limit?: number): Promise<OrganizerRenameLogEntry[]>
    renameUndo(batchId: string): Promise<OrganizerApplyResponse>
    nfoPlan(items: OrganizerItem[], opts?: OrganizerPlanOptions): Promise<OrganizerNfoOperation[]>
    nfoApply(items: OrganizerItem[], opts?: OrganizerPlanOptions): Promise<OrganizerApplyResponse>
    artworkPlan(items: OrganizerItem[], opts?: OrganizerPlanOptions): Promise<OrganizerArtworkOperation[]>
    artworkApply(items: OrganizerItem[], opts?: OrganizerPlanOptions): Promise<OrganizerApplyResponse>
    artworkBatch(playbackIds: string[], size?: number): Promise<OrganizerArtworkBatchItem[]>
}

export interface OrganizerPlanOptions {
    source?: string
    overwrite?: boolean
    selectedCandidates?: Record<string, OrganizerCandidate>
}

export function createOrganizerRepository(api: AxiosInstance = defaultApi): OrganizerRepository {
    return {
        getConfig: async () => (await api.get<OrganizerConfig>("/organizer/config")).data,
        updateConfig: async (patch) => (await api.put<OrganizerConfig>("/organizer/config", patch)).data,
        library: async () => (await api.get<OrganizerLibrary>("/organizer/library")).data,
        musicAlbums: async () =>
            (await api.get<{ albums: OrganizerMusicAlbum[] }>("/organizer/music/albums")).data.albums,
        items: async (kind) =>
            (await api.get<{ items: OrganizerItem[] }>("/organizer/items", { params: { kind } })).data.items,
        details: async (items) =>
            (await api.post<{ items: OrganizerItem[] }>("/organizer/details", { items })).data.items,
        mediaInfo: async (playbackId) =>
            (await api.get<OrganizerMediaInfo | null>("/organizer/media-info", { params: { playback_id: playbackId } })).data,
        lyricsSearch: async (input) =>
            (await api.post<{ candidates: OrganizerLyricsCandidate[] }>("/organizer/lyrics/search", input)).data.candidates,
        lyricsApply: async (input) =>
            (await api.post<OrganizerApplyResponse>("/organizer/lyrics/apply", input)).data,
        scan: async (paths, recursive) =>
            (await api.post<{ items: OrganizerItem[] }>("/organizer/scan", { paths, recursive })).data.items,
        match: async (items, source, limit = 3, language) =>
            (await api.post<{ results: OrganizerMatchResult[] }>("/organizer/match", { items, source, limit, language })).data.results,
        renamePlan: async (items, root) =>
            (await api.post<OrganizerRenamePlan>("/organizer/rename/plan", { items, root })).data,
        renameApply: async (items, root) =>
            (await api.post<OrganizerApplyResponse>("/organizer/rename/apply", { items, root })).data,
        renameLogs: async (limit = 10) =>
            (await api.get<OrganizerRenameLogEntry[]>("/organizer/rename/logs", { params: { limit } })).data,
        renameUndo: async (batchId) =>
            (await api.post<OrganizerApplyResponse>(`/organizer/rename/undo/${batchId}`)).data,
        nfoPlan: async (items, opts = {}) =>
            (await api.post<{ operations: OrganizerNfoOperation[] }>("/organizer/nfo/plan", planBody(items, opts))).data.operations,
        nfoApply: async (items, opts = {}) =>
            (await api.post<OrganizerApplyResponse>("/organizer/nfo/apply", planBody(items, opts))).data,
        artworkPlan: async (items, opts = {}) =>
            (await api.post<{ operations: OrganizerArtworkOperation[] }>("/organizer/artwork/plan", planBody(items, opts))).data.operations,
        artworkApply: async (items, opts = {}) =>
            (await api.post<OrganizerApplyResponse>("/organizer/artwork/apply", planBody(items, opts))).data,
        artworkBatch: async (playbackIds, size = 320) =>
            (await api.post<{ items: OrganizerArtworkBatchItem[] }>("/organizer/artwork/batch", {
                playback_ids: playbackIds,
                size,
            })).data.items,
    }
}

export const organizerRepo = createOrganizerRepository()

function planBody(items: OrganizerItem[], opts: OrganizerPlanOptions) {
    return {
        items,
        source: opts.source,
        overwrite: opts.overwrite ?? false,
        selected_candidates: opts.selectedCandidates ?? {},
    }
}
