import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { OrganizerItem, OrganizerPlanOptions } from "@/api/organizer"
import type { ThumbnailBuildOptions } from "@/api/library"

export interface Job {
    id: string
    kind: string
    status: "queued" | "running" | "done" | "error" | string
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
    createScrapeJob(items: OrganizerItem[], opts?: OrganizerPlanOptions): Promise<Job>
    createSyncJob(paths: string[], recursive: boolean): Promise<Job>
    createRenameJob(items: OrganizerItem[], opts?: { root?: string }): Promise<Job>
    createThumbnailJob(opts: ThumbnailBuildOptions): Promise<Job>
    job(id: string): Promise<Job>
    list(limit?: number, status?: string): Promise<Job[]>
    cancel(id: string): Promise<Job>
    retry(id: string): Promise<Job>
}

export function createJobsRepository(api: AxiosInstance = defaultApi): JobsRepository {
    return {
        createScrapeJob: async (items, opts = {}) =>
            (await api.post<Job>("/jobs/scrape", {
                items,
                source: opts.source,
                overwrite: opts.overwrite ?? true,
                selected_candidates: opts.selectedCandidates ?? {},
            })).data,
        createSyncJob: async (paths, recursive) =>
            (await api.post<Job>("/jobs/sync", { paths, recursive })).data,
        createRenameJob: async (items, opts = {}) =>
            (await api.post<Job>("/jobs/rename", { items, root: opts.root })).data,
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
