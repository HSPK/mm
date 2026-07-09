import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"

export interface FileBrowserEntry {
    name: string
    path: string
    is_dir: boolean
    is_file: boolean
    extension: string
    size?: number | null
    modified_at?: number | null
    selectable: boolean
}

export interface FileBrowserResponse {
    path: string
    parent?: string | null
    roots: string[]
    entries: FileBrowserEntry[]
}

export type FileSelectMode = "any" | "file" | "directory" | "media"

export interface FilesRepository {
    browse(path?: string, select?: FileSelectMode): Promise<FileBrowserResponse>
}

export function createFilesRepository(api: AxiosInstance = defaultApi): FilesRepository {
    return {
        browse: async (path, select = "any") =>
            (await api.get<FileBrowserResponse>("/files/browse", { params: { path, select } })).data,
    }
}

export const filesRepo = createFilesRepository()
