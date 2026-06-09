import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { UserDetail, User } from "@/api/types"

export interface CreateUserBody {
    username: string
    password: string
    display_name?: string
    is_admin?: boolean
}

export interface UsersRepository {
    list(): Promise<UserDetail[]>
    create(body: CreateUserBody): Promise<User>
    remove(id: number): Promise<void>
}

export function createUsersRepository(api: AxiosInstance = defaultApi): UsersRepository {
    return {
        list: async () => (await api.get<UserDetail[]>("/users")).data,
        create: async (body) => (await api.post<User>("/users", body)).data,
        remove: async (id) => {
            await api.delete(`/users/${id}`)
        },
    }
}

export const usersRepo: UsersRepository = createUsersRepository()
