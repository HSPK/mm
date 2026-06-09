import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type { User } from "@/api/types"

export interface AuthRepository {
    login(username: string, password: string): Promise<{ token: string; user: User }>
    me(): Promise<User>
}

export function createAuthRepository(api: AxiosInstance = defaultApi): AuthRepository {
    return {
        login: async (username, password) =>
            (await api.post<{ token: string; user: User }>("/auth/login", { username, password })).data,
        me: async () => (await api.get<User>("/auth/me")).data,
    }
}

export const authRepo: AuthRepository = createAuthRepository()
