import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { SmartAlbumsResponse } from "@/api/types"

export interface CameraInfo {
    make: string
    model: string
    count: number
}

export interface CatalogRepository {
    listCameras(): Promise<CameraInfo[]>
    listSmartAlbums(): Promise<SmartAlbumsResponse>
}

export function createCatalogRepository(api: AxiosInstance = defaultApi): CatalogRepository {
    return {
        listCameras: async () => (await api.get<CameraInfo[]>("/cameras")).data,
        listSmartAlbums: async () => (await api.get<SmartAlbumsResponse>("/smart-albums")).data,
    }
}

export const catalogRepo: CatalogRepository = createCatalogRepository()
