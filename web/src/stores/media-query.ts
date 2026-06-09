import axios from "axios"
import { create } from "zustand"
import type { Media } from "@/api/types"
import { mediaRepo, type MediaRepository } from "@/api/media"
import { defaultFilters, type Filters } from "@/lib/filter-types"
import { mediaMatchesFilters, needsServerFilterRecheck } from "@/lib/media-predicate"
import { sortMediaItems } from "@/lib/media-sorters"

interface MediaQueryState {
    items: Media[]
    page: number
    perPage: number
    total: number
    hasMore: boolean
    loading: boolean
    error: string | null
    filters: Filters
    activeLabel: string | null
    albumFilterKeys: Set<string>
    fetchMedia: (reset?: boolean) => Promise<void>
    setFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void
    setFilters: (updates: Partial<Filters>, options?: { replace?: boolean }) => void
    resetFilters: () => void
    removeItem: (id: number) => void
    updateItem: (id: number, patch: Partial<Media>) => void
    removeItems: (ids: number[]) => void
    setActiveLabel: (label: string | null, lockedKeys?: string[]) => void
}

interface FetchControl {
    seq: number
    controller: AbortController | null
}

// Module-scoped to avoid re-creating per store call and to support cancellation
// of in-flight fetches when a new one starts.
const fetchControl: FetchControl = { seq: 0, controller: null }

export function createMediaQueryStore(repo: MediaRepository = mediaRepo) {
    return create<MediaQueryState>((set, get) => ({
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

        fetchMedia: async (reset = false) => {
            const state = get()
            if (state.loading && !reset) return

            if (reset) {
                fetchControl.controller?.abort()
                set({ items: [], page: 1, hasMore: true })
            }

            const currentState = get()
            if (!currentState.hasMore && !reset) return

            const requestSeq = ++fetchControl.seq
            const controller = new AbortController()
            fetchControl.controller = controller
            set({ loading: true, error: null })

            try {
                const data = await repo.list({
                    page: reset ? 1 : currentState.page,
                    perPage: currentState.perPage,
                    filters: currentState.filters,
                    signal: controller.signal,
                })
                if (requestSeq !== fetchControl.seq) return
                const { items, total, pages } = data
                const nextPage = reset ? 2 : currentState.page + 1

                set((s) => ({
                    items: reset ? items : [...s.items, ...items],
                    total,
                    hasMore: (reset ? 1 : currentState.page) < pages,
                    page: nextPage,
                    loading: false,
                }))
            } catch (err: unknown) {
                if (axios.isCancel(err) || requestSeq !== fetchControl.seq) return
                const message = err instanceof Error ? err.message : "Failed to fetch media"
                set({ error: message, loading: false })
            } finally {
                if (fetchControl.controller === controller) {
                    fetchControl.controller = null
                }
            }
        },

        setFilter: (key, value) => {
            set((s) => ({ filters: { ...s.filters, [key]: value } }))
            void get().fetchMedia(true)
        },

        setFilters: (updates, options) => {
            set((s) => ({
                filters: { ...(options?.replace ? defaultFilters : s.filters), ...updates },
                activeLabel: options?.replace ? null : s.activeLabel,
                albumFilterKeys: options?.replace ? new Set<string>() : s.albumFilterKeys,
            }))
            void get().fetchMedia(true)
        },

        resetFilters: () => {
            set({
                filters: { ...defaultFilters },
                activeLabel: null,
                albumFilterKeys: new Set<string>(),
            })
            void get().fetchMedia(true)
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

        removeItems: (ids) => {
            const idSet = new Set(ids)
            set((s) => ({
                items: s.items.filter((i) => !idSet.has(i.id)),
                total: Math.max(0, s.total - ids.length),
            }))
        },

        setActiveLabel: (label, lockedKeys) => {
            set({ activeLabel: label, albumFilterKeys: new Set(lockedKeys ?? []) })
        },
    }))
}

export const useMediaQueryStore = createMediaQueryStore()
