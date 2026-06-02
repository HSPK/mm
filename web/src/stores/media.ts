import { create } from "zustand"
import axios from "axios"
import { api } from "@/api/client"
import type { Media, PaginatedMedia } from "@/api/types"
import {
    mediaMatchesFilters,
    needsServerFilterRecheck,
    sortMediaItems,
    type Filters,
} from "@/lib/media-filter"

export type { Filters } from "@/lib/media-filter"

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
    activeLabel: string | null
    albumFilterKeys: Set<string>
    // Selection mode
    selectionMode: boolean
    selectedIds: Set<number>
    setViewMode: (mode: ViewMode) => void
    setDateGroupMode: (mode: DateGroupMode) => void
    setThumbSize: (size: number) => void
    fetchMedia: (reset?: boolean) => Promise<void>
    setFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void
    setFilters: (updates: Partial<Filters>, options?: { replace?: boolean }) => void
    resetFilters: () => void
    removeItem: (id: number) => void
    updateItem: (id: number, patch: Partial<Media>) => void
    setActiveLabel: (label: string | null, lockedKeys?: string[]) => void
    enterSelectionMode: (initialId?: number) => void
    exitSelectionMode: () => void
    toggleSelected: (id: number) => void
    selectAll: () => void
    removeItems: (ids: number[]) => void
}

const defaultFilters: Filters = {
    type: null,
    tag: null,
    camera: null,
    date_from: null,
    date_to: null,
    date_ranges: null,
    sort: "date_taken",
    order: "desc",
    search: null,
    min_rating: null,
    favorites_only: false,
    lat: null,
    lon: null,
    radius: null,
    no_date: false,
    deleted: false,
}

let mediaFetchSeq = 0
let mediaFetchController: AbortController | null = null

export const useMediaStore = create<MediaState>((set, get) => ({
    items: [],
    page: 1,
    perPage: 60,
    total: 0,
    hasMore: true,
    loading: false,
    error: null,
    filters: { ...defaultFilters },
    activeLabel: null,
    albumFilterKeys: new Set<string>(),
    selectionMode: false,
    selectedIds: new Set<number>(),
    viewMode: (localStorage.getItem("mm-view-mode") === "grid" ? "grid" : "justified") as ViewMode,
    dateGroupMode: (localStorage.getItem("mm-date-group-mode") === "day" ? "day" : "month") as DateGroupMode,
    thumbSize: Math.min(400, Math.max(80, Number(localStorage.getItem("mm-thumb-size")) || 220)),

    setViewMode: (mode) => {
        localStorage.setItem("mm-view-mode", mode)
        set({ viewMode: mode })
    },
    setDateGroupMode: (mode) => {
        localStorage.setItem("mm-date-group-mode", mode)
        set({ dateGroupMode: mode })
    },
    setThumbSize: (size) => {
        const clamped = Math.min(400, Math.max(80, size))
        localStorage.setItem("mm-thumb-size", String(clamped))
        set({ thumbSize: clamped })
    },

    fetchMedia: async (reset = false) => {
        const state = get()
        if (state.loading && !reset) return

        if (reset) {
            mediaFetchController?.abort()
            set({ items: [], page: 1, hasMore: true })
        }

        const currentState = get()
        if (!currentState.hasMore && !reset) return

        const requestSeq = ++mediaFetchSeq
        const controller = new AbortController()
        mediaFetchController = controller
        set({ loading: true, error: null })

        try {
            const params: Record<string, unknown> = {
                page: reset ? 1 : currentState.page,
                per_page: currentState.perPage,
            }

            // Add non-null filters
            for (const [k, v] of Object.entries(currentState.filters)) {
                if (v !== null && v !== false && v !== "") {
                    // date_ranges must be JSON-encoded for the API
                    params[k] = k === "date_ranges" && Array.isArray(v) ? JSON.stringify(v) : v
                }
            }

            const res = await api.get<PaginatedMedia>("/media", { params, signal: controller.signal })
            if (requestSeq !== mediaFetchSeq) return
            const { items, total, pages } = res.data
            const nextPage = reset ? 2 : currentState.page + 1

            set((s) => ({
                items: reset ? items : [...s.items, ...items],
                total,
                hasMore: (reset ? 1 : currentState.page) < pages,
                page: nextPage,
                loading: false,
            }))
        } catch (err: unknown) {
            if (axios.isCancel(err) || requestSeq !== mediaFetchSeq) return
            const message = err instanceof Error ? err.message : "Failed to fetch media"
            set({ error: message, loading: false })
        } finally {
            if (mediaFetchController === controller) {
                mediaFetchController = null
            }
        }
    },

    setFilter: (key, value) => {
        set((s) => ({
            filters: { ...s.filters, [key]: value },
        }))
        get().fetchMedia(true)
    },

    setFilters: (updates, options) => {
        set((s) => ({
            filters: { ...(options?.replace ? defaultFilters : s.filters), ...updates },
            activeLabel: options?.replace ? null : s.activeLabel,
            albumFilterKeys: options?.replace ? new Set<string>() : s.albumFilterKeys,
        }))
        get().fetchMedia(true)
    },

    resetFilters: () => {
        set({ filters: { ...defaultFilters }, activeLabel: null, albumFilterKeys: new Set<string>() })
        get().fetchMedia(true)
    },

    removeItem: (id) => {
        set((s) => ({
            items: s.items.filter((i) => i.id !== id),
            total: Math.max(0, s.total - 1),
        }))
    },

    updateItem: (id, patch) => {
        const shouldRefetch = needsServerFilterRecheck(get().filters)
        set((s) => {
            const wasPresent = s.items.some((item) => item.id === id)
            const nextItems = s.items
                .map((item) => (item.id === id ? { ...item, ...patch } : item))
                .filter((item) => mediaMatchesFilters(item, s.filters))
            const stillPresent = nextItems.some((item) => item.id === id)
            return {
                items: sortMediaItems(nextItems, s.filters),
                total: wasPresent && !stillPresent ? Math.max(0, s.total - 1) : s.total,
            }
        })
        if (shouldRefetch) void get().fetchMedia(true)
    },

    setActiveLabel: (label, lockedKeys) => {
        set({ activeLabel: label, albumFilterKeys: new Set(lockedKeys ?? []) })
    },

    enterSelectionMode: (initialId) => {
        const ids = new Set<number>()
        if (initialId != null) ids.add(initialId)
        set({ selectionMode: true, selectedIds: ids })
    },

    exitSelectionMode: () => {
        set({ selectionMode: false, selectedIds: new Set<number>() })
    },

    toggleSelected: (id) => {
        set((s) => {
            const next = new Set(s.selectedIds)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            // Auto-exit if nothing selected
            if (next.size === 0) return { selectionMode: false, selectedIds: next }
            return { selectedIds: next }
        })
    },

    selectAll: () => {
        set((s) => ({
            selectionMode: true,
            selectedIds: new Set(s.items.map((i) => i.id)),
        }))
    },

    removeItems: (ids) => {
        const idSet = new Set(ids)
        set((s) => ({
            items: s.items.filter((i) => !idSet.has(i.id)),
            total: Math.max(0, s.total - ids.length),
            selectedIds: new Set([...s.selectedIds].filter((id) => !idSet.has(id))),
        }))
    },
}))
