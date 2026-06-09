import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"

export interface LibraryInfo {
    db_path: string
    name: string
}

export interface LibraryRepository {
    getCurrent(): Promise<LibraryInfo>
    listRecent(): Promise<LibraryInfo[]>
    switchTo(dbPath: string): Promise<LibraryInfo & { message: string }>
    getConfig(): Promise<Record<string, string>>
    updateConfig(patch: Record<string, unknown>): Promise<void>
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
    }
}

export const libraryRepo: LibraryRepository = createLibraryRepository()
