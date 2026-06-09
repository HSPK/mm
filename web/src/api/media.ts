import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { DuplicateGroup, Media, MediaDetail, PaginatedMedia } from "@/api/types"
import type { Filters } from "@/lib/filter-types"

export interface ListMediaParams {
    page: number
    perPage: number
    filters: Filters
    signal?: AbortSignal
}

/**
 * Encodes filters into the URL params shape the backend expects.
 * Null/false/empty values are dropped; `date_ranges` is JSON-encoded.
 */
export function encodeFilterParams(
    page: number,
    perPage: number,
    filters: Filters,
): Record<string, unknown> {
    const params: Record<string, unknown> = { page, per_page: perPage }
    for (const [k, v] of Object.entries(filters)) {
        if (v === null || v === false || v === "") continue
        params[k] = k === "date_ranges" && Array.isArray(v) ? JSON.stringify(v) : v
    }
    return params
}

export interface MediaRepository {
    list(params: ListMediaParams): Promise<PaginatedMedia>
    get(id: number): Promise<MediaDetail>
    updateMetadata(id: number, patch: Record<string, unknown>): Promise<MediaDetail>
    setRating(id: number, rating: number): Promise<{ rating: number }>
    addTags(id: number, tags: string[]): Promise<void>
    removeTag(id: number, tag: string): Promise<void>
    deleteOne(id: number, opts?: { permanent?: boolean }): Promise<void>
    restoreOne(id: number): Promise<void>
    batchDelete(ids: number[]): Promise<{ affected: number }>
    batchUpdateMetadata(ids: number[], patch: Record<string, unknown>): Promise<{ affected: number }>
    downloadBlob(id: number): Promise<Blob>
    listTrash(): Promise<Media[]>
    emptyTrash(): Promise<void>
    listDuplicates(opts?: { minCount?: number; limit?: number }): Promise<DuplicateGroup[]>
}

export function createMediaRepository(api: AxiosInstance = defaultApi): MediaRepository {
    return {
        list: async ({ page, perPage, filters, signal }) => {
            const params = encodeFilterParams(page, perPage, filters)
            const res = await api.get<PaginatedMedia>("/media", { params, signal })
            return res.data
        },
        get: async (id) => (await api.get<MediaDetail>(`/media/${id}`)).data,
        updateMetadata: async (id, patch) =>
            (await api.patch<MediaDetail>(`/media/${id}/metadata`, patch)).data,
        setRating: async (id, rating) =>
            (await api.put<{ rating: number }>(`/media/${id}/rating`, { rating })).data,
        addTags: async (id, tags) => {
            await api.post(`/media/${id}/tags`, { tags })
        },
        removeTag: async (id, tag) => {
            await api.delete(`/media/${id}/tags/${encodeURIComponent(tag)}`)
        },
        deleteOne: async (id, opts) => {
            await api.delete(`/media/${id}`, opts?.permanent ? { params: { permanent: true } } : undefined)
        },
        restoreOne: async (id) => {
            await api.post(`/media/${id}/restore`)
        },
        batchDelete: async (ids) =>
            (await api.post<{ affected: number }>("/batch/delete", { media_ids: ids })).data,
        batchUpdateMetadata: async (ids, patch) =>
            (await api.post<{ affected: number }>("/batch/metadata", { media_ids: ids, ...patch })).data,
        downloadBlob: async (id) =>
            (await api.get(`/media/${id}/file`, { responseType: "blob" })).data,
        listTrash: async () => (await api.get<Media[]>("/media/trash")).data,
        emptyTrash: async () => {
            await api.delete("/media/trash")
        },
        listDuplicates: async (opts) => {
            const params: Record<string, number> = {}
            if (opts?.minCount) params.min_count = opts.minCount
            if (opts?.limit) params.limit = opts.limit
            return (await api.get<DuplicateGroup[]>("/media/duplicates", { params })).data
        },
    }
}

export const mediaRepo: MediaRepository = createMediaRepository()
