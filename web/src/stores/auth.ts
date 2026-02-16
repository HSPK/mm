import { create } from "zustand"
import { api } from "@/api/client"
import type { User } from "@/api/types"

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

// Sync token to cookie on initial load
const initialToken = localStorage.getItem("uom_token")
if (initialToken) {
    document.cookie = `uom_token=${initialToken}; path=/; SameSite=Strict`
}

export const useAuthStore = create<AuthState>((set, get) => ({
    token: initialToken,
    user: null,
    loading: false,
    error: null,
    get isAuthenticated() {
        return !!get().token
    },

    login: async (username, password) => {
        set({ loading: true, error: null })
        try {
            const res = await api.post<{ token: string; user: User }>("/auth/login", { username, password })
            const token = res.data.token
            localStorage.setItem("uom_token", token)
            document.cookie = `uom_token=${token}; path=/; SameSite=Strict`
            set({ token, loading: false })
            await get().fetchUser()
            return true
        } catch (err: any) {
            const msg = err.response?.data?.detail || "Login failed"
            set({ error: msg, loading: false })
            return false
        }
    },

    fetchUser: async () => {
        try {
            const res = await api.get<User>("/auth/me")
            set({ user: res.data })
        } catch {
            get().logout()
        }
    },

    logout: () => {
        localStorage.removeItem("uom_token")
        document.cookie = "uom_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
        set({ token: null, user: null })
    },
}))
