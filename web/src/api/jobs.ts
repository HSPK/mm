import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { OrganizerItem, OrganizerPlanOptions } from "@/api/organizer"
import type { ThumbnailBuildOptions } from "@/api/library"

export interface Job {
    id: string
    kind: string
    status: "queued" | "running" | "canceling" | "done" | "error" | "canceled" | "completed_with_errors" | string
    progress: number
    title: string
    message: string
    detail: string
    result: Record<string, unknown>
    error: string
    created_at: string
    updated_at: string
}

export interface JobsRepository {
    createScrapeJob(items: OrganizerItem[], opts?: OrganizerPlanOptions, idempotencyKey?: string): Promise<Job>
    createSyncJob(paths: string[], recursive: boolean, idempotencyKey?: string): Promise<Job>
    createRenameJob(items: OrganizerItem[], opts?: { root?: string }, idempotencyKey?: string): Promise<Job>
    createThumbnailJob(opts: ThumbnailBuildOptions): Promise<Job>
    job(id: string): Promise<Job>
    list(limit?: number, status?: string): Promise<Job[]>
    cancel(id: string): Promise<Job>
    retry(id: string): Promise<Job>
}

export function createJobsRepository(api: AxiosInstance = defaultApi): JobsRepository {
    return {
        createScrapeJob: async (items, opts = {}, idempotencyKey) =>
            (await api.post<Job>("/jobs/scrape", {
                items,
                source: opts.source,
                language: opts.language,
                overwrite: opts.overwrite ?? true,
                selected_candidates: opts.selectedCandidates ?? {},
            }, { headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined })).data,
        createSyncJob: async (paths, recursive, idempotencyKey) =>
            (await api.post<Job>("/jobs/sync", { paths, recursive }, {
                headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
            })).data,
        createRenameJob: async (items, opts = {}, idempotencyKey) =>
            (await api.post<Job>("/jobs/rename", { items, root: opts.root }, {
                headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
            })).data,
        createThumbnailJob: async (opts) =>
            (await api.post<Job>("/jobs/thumbnails", {
                videos_only: opts.videosOnly ?? false,
                failed_only: opts.failedOnly ?? false,
                force: opts.force ?? false,
                sizes: opts.sizes,
            })).data,
        job: async (id) => (await api.get<Job>(`/jobs/${id}`)).data,
        list: async (limit = 20, status) =>
            (await api.get<Job[]>("/jobs", { params: { limit, status } })).data,
        cancel: async (id) => (await api.post<Job>(`/jobs/${id}/cancel`)).data,
        retry: async (id) => (await api.post<Job>(`/jobs/${id}/retry`)).data,
    }
}

export const jobsRepo = createJobsRepository()
