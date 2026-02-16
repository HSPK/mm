import { create } from "zustand"
import { api } from "@/api/client"
import type { Media, PaginatedMedia } from "@/api/types"

interface Filters {
    type: string | null
    tag: string | null
    camera: string | null
    date_from: string | null
    date_to: string | null
    sort: string
    order: string
    search: string | null
    min_rating: number | null
    favorites_only: boolean
    lat: number | null
    lon: number | null
    radius: number | null
}

export type ViewMode = "justified" | "grid"
export type DateGroupMode = "day" | "month"

interface MediaState {
    items: Media[]
    page: number
    perPage: number
    total: number
    hasMore: boolean
    loading: boolean
    error: string | null
    filters: Filters
    viewMode: ViewMode
    dateGroupMode: DateGroupMode
    thumbSize: number
    setViewMode: (mode: ViewMode) => void
    setDateGroupMode: (mode: DateGroupMode) => void
    setThumbSize: (size: number) => void
    fetchMedia: (reset?: boolean) => Promise<void>
    setFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void
    setFilters: (updates: Partial<Filters>) => void
    resetFilters: () => void
}

const defaultFilters: Filters = {
    type: null,
    tag: null,
    camera: null,
    date_from: null,
    date_to: null,
    sort: "date_taken",
    order: "desc",
    search: null,
    min_rating: null,
    favorites_only: false,
    lat: null,
    lon: null,
    radius: null,
}

export const useMediaStore = create<MediaState>((set, get) => ({
    items: [],
    page: 1,
    perPage: 60,
    total: 0,
    hasMore: true,
    loading: false,
    error: null,
    filters: { ...defaultFilters },
    viewMode: (localStorage.getItem("uom-view-mode") === "grid" ? "grid" : "justified") as ViewMode,
    dateGroupMode: (localStorage.getItem("uom-date-group-mode") === "day" ? "day" : "month") as DateGroupMode,
    thumbSize: Math.min(400, Math.max(80, Number(localStorage.getItem("uom-thumb-size")) || 220)),

    setViewMode: (mode) => {
        localStorage.setItem("uom-view-mode", mode)
        set({ viewMode: mode })
    },
    setDateGroupMode: (mode) => {
        localStorage.setItem("uom-date-group-mode", mode)
        set({ dateGroupMode: mode })
    },
    setThumbSize: (size) => {
        const clamped = Math.min(400, Math.max(80, size))
        localStorage.setItem("uom-thumb-size", String(clamped))
        set({ thumbSize: clamped })
    },

    fetchMedia: async (reset = false) => {
        const state = get()
        if (state.loading && !reset) return

        if (reset) {
            set({ items: [], page: 1, hasMore: true })
        }

        const currentState = get()
        if (!currentState.hasMore && !reset) return

        set({ loading: true, error: null })

        try {
            const params: Record<string, unknown> = {
                page: reset ? 1 : currentState.page,
                per_page: currentState.perPage,
            }

            // Add non-null filters
            for (const [k, v] of Object.entries(currentState.filters)) {
                if (v !== null && v !== false && v !== "") {
                    params[k] = v
                }
            }

            const res = await api.get<PaginatedMedia>("/media", { params })
            const { items, total, pages } = res.data
            const nextPage = reset ? 2 : currentState.page + 1

            set((s) => ({
                items: reset ? items : [...s.items, ...items],
                total,
                hasMore: (reset ? 1 : currentState.page) < pages,
                page: nextPage,
                loading: false,
            }))
        } catch (err: any) {
            set({ error: err.message || "Failed to fetch media", loading: false })
        }
    },

    setFilter: (key, value) => {
        set((s) => ({
            filters: { ...s.filters, [key]: value },
        }))
        get().fetchMedia(true)
    },

    setFilters: (updates) => {
        set((s) => ({
            filters: { ...s.filters, ...updates },
        }))
        get().fetchMedia(true)
    },

    resetFilters: () => {
        set({ filters: { ...defaultFilters } })
        get().fetchMedia(true)
    },
}))
