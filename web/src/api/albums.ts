import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"

export interface AlbumSummary {
    id: number
    name: string
}

export interface AlbumRepository {
    list(): Promise<AlbumSummary[]>
    create(name: string): Promise<{ id: number }>
    addMedia(albumId: number, mediaIds: number[]): Promise<void>
}

export function createAlbumRepository(api: AxiosInstance = defaultApi): AlbumRepository {
    return {
        list: async () => (await api.get<AlbumSummary[]>("/albums")).data,
        create: async (name) => (await api.post<{ id: number }>("/albums", { name })).data,
        addMedia: async (albumId, mediaIds) => {
            await api.post(`/albums/${albumId}/media`, { media_ids: mediaIds })
        },
    }
}

export const albumRepo: AlbumRepository = createAlbumRepository()
