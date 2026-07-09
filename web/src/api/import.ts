import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"

export interface ImportPlanOperation {
    source: string
    destination: string
    media_type: string
    status: string
    reason: string
}

export interface ImportPlanResponse {
    source: string
    library_root: string
    template: string
    discovered: number
    new_files: number
    intra_duplicates: number
    library_duplicates: number
    importable: number
    errors: number
    operations: ImportPlanOperation[]
}

export interface ImportApplyResponse {
    file_count: number
    indexed_count: number
    message: string
}

export interface ImportRepository {
    plan(source: string, move: boolean, metadataMode: string): Promise<ImportPlanResponse>
    apply(source: string, move: boolean, metadataMode: string): Promise<ImportApplyResponse>
}

export function createImportRepository(api: AxiosInstance = defaultApi): ImportRepository {
    const body = (source: string, move: boolean, metadataMode: string) => ({
        source,
        move,
        metadata_mode: metadataMode,
    })
    return {
        plan: async (source, move, metadataMode) =>
            (await api.post<ImportPlanResponse>("/import/plan", body(source, move, metadataMode))).data,
        apply: async (source, move, metadataMode) =>
            (await api.post<ImportApplyResponse>("/import/apply", body(source, move, metadataMode))).data,
    }
}

export const importRepo = createImportRepository()
