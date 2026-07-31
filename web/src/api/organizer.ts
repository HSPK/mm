import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { components } from "@/api/schema"

export type OrganizerItem = components["schemas"]["OrganizerItem-Output"]
export type OrganizerItemPatch = components["schemas"]["OrganizerItemPatch"]
export type OrganizerItemsResponse = components["schemas"]["OrganizerItemsResponse"]
export type OrganizerFileAsset = components["schemas"]["OrganizerFileAsset"]
export type OrganizerArtworkAsset = components["schemas"]["OrganizerArtworkAsset"]
export type OrganizerStreamInfo = components["schemas"]["OrganizerStreamInfo"]
export type OrganizerMediaInfo = components["schemas"]["OrganizerMediaInfo"]

export interface OrganizerItemsQuery {
    kind?: string
}

export interface OrganizerItemPatchRequest extends OrganizerItemPatch {
    item_uid: string
}

export interface OrganizerCapability {
    media_type: string
    scrapers: string[]
    outputs: string[]
    rename: boolean
    lyrics: boolean
}

export interface OrganizerCapabilities {
    media_types: OrganizerCapability[]
    scraper_adapters: Record<string, string>
}

export interface RequestOptions {
    signal?: AbortSignal
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
    items(query?: OrganizerItemsQuery, options?: RequestOptions): Promise<OrganizerItemsResponse>
    revealDirectory(itemUids: string[]): Promise<{ revealed: boolean }>
    patchItem(itemUid: string, patch: OrganizerItemPatch): Promise<OrganizerItem>
    patchItems(items: OrganizerItemPatchRequest[]): Promise<OrganizerItem[]>
    capabilities(options?: RequestOptions): Promise<OrganizerCapabilities>
    details(items: OrganizerItem[]): Promise<OrganizerItem[]>
    mediaInfo(playbackId: string): Promise<OrganizerMediaInfo | null>
    lyricsSearch(input: { path: string, title: string, artist?: string | null, album?: string | null, source?: string, limit?: number }, options?: RequestOptions): Promise<OrganizerLyricsCandidate[]>
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
    language?: string
    overwrite?: boolean
    selectedCandidates?: Record<string, OrganizerCandidate>
}

export function createOrganizerRepository(api: AxiosInstance = defaultApi): OrganizerRepository {
    return {
        getConfig: async () => (await api.get<OrganizerConfig>("/organizer/config")).data,
        updateConfig: async (patch) => (await api.put<OrganizerConfig>("/organizer/config", patch)).data,
        items: async (query = {}, options = {}) =>
            (await api.get<OrganizerItemsResponse>("/organizer/items", {
                params: query,
                signal: options.signal,
            })).data,
        revealDirectory: async (itemUids) =>
            (await api.post<{ revealed: boolean }>("/organizer/reveal-directory", {
                item_uids: itemUids,
            })).data,
        patchItem: async (itemUid, patch) =>
            (await api.patch<OrganizerItem>(`/organizer/items/${encodeURIComponent(itemUid)}`, patch)).data,
        patchItems: async (items) =>
            (await api.patch<{ items: OrganizerItem[] }>("/organizer/items", { items })).data.items,
        capabilities: async (options = {}) => {
            const data = (await api.get<Record<string, unknown>>("/organizer/capabilities", {
                signal: options.signal,
            })).data
            return {
                media_types: Array.isArray(data.media_types) ? data.media_types as OrganizerCapability[] : [],
                scraper_adapters: typeof data.scraper_adapters === "object" && data.scraper_adapters
                    ? data.scraper_adapters as Record<string, string>
                    : {},
            }
        },
        details: async (items) =>
            (await api.post<{ items: OrganizerItem[] }>("/organizer/details", { items })).data.items,
        mediaInfo: async (playbackId) =>
            (await api.get<OrganizerMediaInfo | null>("/organizer/media-info", { params: { playback_id: playbackId } })).data,
        lyricsSearch: async (input, options = {}) =>
            (await api.post<{ candidates: OrganizerLyricsCandidate[] }>("/organizer/lyrics/search", input, {
                signal: options.signal,
            })).data.candidates,
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
