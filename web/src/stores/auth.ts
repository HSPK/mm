import axios from "axios"
import { create } from "zustand"
import { authRepo, type AuthRepository } from "@/api/auth"
import type { User } from "@/api/types"
import { browserTokenStorage, type TokenStorage } from "@/lib/token-storage"

interface AuthState {
    token: string | null
    user: User | null
    loading: boolean
    error: string | null
    isAuthenticated: boolean
    login: (username: string, password: string) => Promise<boolean>
    fetchUser: () => Promise<void>
    logout: () => void
}

export interface AuthStoreDeps {
    repo?: AuthRepository
    tokenStorage?: TokenStorage
}

function extractLoginError(err: unknown): string {
    if (axios.isAxiosError<{ detail?: string }>(err)) {
        return err.response?.data?.detail || "Login failed"
    }
    return "Login failed"
}

export function createAuthStore(deps: AuthStoreDeps = {}) {
    const repo = deps.repo ?? authRepo
    const storage = deps.tokenStorage ?? browserTokenStorage

    const initialToken = storage.get()
    return create<AuthState>((set, get) => ({
        token: initialToken,
        user: null,
        loading: Boolean(initialToken),
        error: null,
        get isAuthenticated() {
            return !!get().token
        },

        login: async (username, password) => {
            set({ loading: true, error: null })
            try {
                const { token } = await repo.login(username, password)
                storage.set(token)
                set({ token, loading: false })
                await get().fetchUser()
                return true
            } catch (err: unknown) {
                set({ error: extractLoginError(err), loading: false })
                return false
            }
        },

        fetchUser: async () => {
            set({ loading: true })
            try {
                const user = await repo.me()
                set({ user, loading: false })
            } catch {
                get().logout()
            }
        },

        logout: () => {
            void repo.logout().catch(() => undefined)
            storage.clear()
            set({ token: null, user: null, loading: false })
        },
    }))
}

export const useAuthStore = createAuthStore()
