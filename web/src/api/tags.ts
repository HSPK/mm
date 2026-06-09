import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { Tag } from "@/api/types"

export interface TagsRepository {
    list(): Promise<Tag[]>
    rename(id: number, name: string): Promise<void>
    remove(id: number): Promise<void>
}

export function createTagsRepository(api: AxiosInstance = defaultApi): TagsRepository {
    return {
        list: async () => (await api.get<Tag[]>("/tags")).data,
        rename: async (id, name) => {
            await api.put(`/tags/${id}`, { name })
        },
        remove: async (id) => {
            await api.delete(`/tags/${id}`)
        },
    }
}

export const tagsRepo: TagsRepository = createTagsRepository()
