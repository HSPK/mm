import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"

export interface LibraryInfo {
    db_path: string
    name: string
    library_id?: string | null
}

export interface ThumbnailStatus {
    ffmpeg_available: boolean
    cache_dir: string
    file_count: number
    total_size: number
    failed_count: number
    by_type: ThumbnailTypeStatus[]
}

export interface ThumbnailTypeStatus {
    media_type: string
    media_count: number
    expected_files: number
    cached_files: number
    failed_count: number
}

export interface ThumbnailBuildResult {
    total: number
    generated: number
    cached: number
    failed: number
    failed_count: number
    message: string
}

export interface ThumbnailBuildOptions {
    videosOnly?: boolean
    failedOnly?: boolean
    force?: boolean
    sizes?: string[]
}

export interface LibraryRepository {
    getCurrent(): Promise<LibraryInfo>
    listRecent(): Promise<LibraryInfo[]>
    switchTo(dbPath: string): Promise<LibraryInfo & { message: string }>
    getConfig(): Promise<Record<string, string>>
    updateConfig(patch: Record<string, unknown>): Promise<void>
    getThumbnailStatus(): Promise<ThumbnailStatus>
    buildThumbnails(options: ThumbnailBuildOptions): Promise<ThumbnailBuildResult>
}

export function createLibraryRepository(api: AxiosInstance = defaultApi): LibraryRepository {
    return {
        getCurrent: async () => (await api.get<LibraryInfo>("/library")).data,
        listRecent: async () => (await api.get<LibraryInfo[]>("/library/recent")).data,
        switchTo: async (dbPath) =>
            (await api.post<LibraryInfo & { message: string }>("/library/switch", { db_path: dbPath })).data,
        getConfig: async () => (await api.get<Record<string, string>>("/library/config")).data,
        updateConfig: async (patch) => {
            await api.put("/library/config", patch)
        },
        getThumbnailStatus: async () => (await api.get<ThumbnailStatus>("/library/thumbnails")).data,
        buildThumbnails: async (options) =>
            (await api.post<ThumbnailBuildResult>("/library/thumbnails/build", {
                videos_only: options.videosOnly ?? false,
                failed_only: options.failedOnly ?? false,
                force: options.force ?? false,
                sizes: options.sizes,
            })).data,
    }
}

export const libraryRepo: LibraryRepository = createLibraryRepository()
