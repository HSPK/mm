import { useMemo } from "react"
import { useMediaQueryStore } from "@/stores/media-query"
import type { SearchBarContext } from "./use-search-bar-context"

export type FilterTagColor = "primary" | "destructive" | "amber" | "emerald"

export interface FilterTag {
    key: string
    label: string
    color?: FilterTagColor
    removable: boolean
    onRemove: () => void
}

interface UseFilterTagListOpts {
    context: SearchBarContext
    onSearchCleared?: () => void
}

function formatDateRangeLabel(from: string | null, to: string | null): string {
    const short = (d: string) => {
        const [y, m, dd] = d.split("-")
        return `${y.slice(2)}/${m}${dd ? `/${dd}` : ""}`
    }
    const f = from ? short(from) : ""
    const t = to ? short(to) : ""
    if (f && t) return `${f} → ${t}`
    return f || `→ ${t}`
}

export function useFilterTagList({ context, onSearchCleared }: UseFilterTagListOpts): FilterTag[] {
    const filters = useMediaQueryStore((s) => s.filters)
    const albumFilterKeys = useMediaQueryStore((s) => s.albumFilterKeys)
    const total = useMediaQueryStore((s) => s.total)
    const setFilter = useMediaQueryStore((s) => s.setFilter)
    const setFilters = useMediaQueryStore((s) => s.setFilters)
    const resetFilters = useMediaQueryStore((s) => s.resetFilters)

    return useMemo(() => {
        if (context.isInAlbumSection) {
            const tags: FilterTag[] = [
                {
                    key: "section",
                    label: context.albumSectionLabel ?? "",
                    removable: true,
                    onRemove: context.exitAlbumSection,
                },
            ]
            if (context.albumSectionSearch) {
                tags.push({
                    key: "search",
                    label: `"${context.albumSectionSearch}"`,
                    removable: true,
                    onRemove: () => context.setAlbumSectionSearch(""),
                })
            }
            return tags
        }

        if (!context.isOnLibrary) return []

        const tags: FilterTag[] = []
        const locked = albumFilterKeys

        if (context.isDeletedView) {
            tags.push({
                key: "trash",
                label: `Recently Deleted · ${total}`,
                color: "destructive",
                removable: true,
                onRemove: resetFilters,
            })
        }
        if (filters.type) {
            tags.push({
                key: "type",
                label: filters.type === "photo" ? "Photos" : "Videos",
                removable: !locked.has("type"),
                onRemove: () => setFilter("type", null),
            })
        }
        if (filters.camera) {
            tags.push({
                key: "camera",
                label: filters.camera,
                removable: !locked.has("camera"),
                onRemove: () => setFilter("camera", null),
            })
        }
        if (filters.date_from || filters.date_to) {
            tags.push({
                key: "date",
                label: formatDateRangeLabel(filters.date_from, filters.date_to),
                removable: !locked.has("date_from") && !locked.has("date_to"),
                onRemove: () => setFilters({ date_from: null, date_to: null }),
            })
        }
        if (filters.min_rating) {
            tags.push({
                key: "rating",
                label: `★ ≥ ${filters.min_rating}`,
                color: "amber",
                removable: !locked.has("min_rating"),
                onRemove: () => setFilter("min_rating", null),
            })
        }
        if (filters.lat != null && filters.lon != null) {
            tags.push({
                key: "location",
                label: `${filters.lat.toFixed(1)}°, ${filters.lon.toFixed(1)}°`,
                color: "emerald",
                removable: !locked.has("lat"),
                onRemove: () => setFilters({ lat: null, lon: null, radius: null }),
            })
        }
        if (filters.search) {
            tags.push({
                key: "search",
                label: `"${filters.search}"`,
                removable: true,
                onRemove: () => {
                    setFilter("search", null)
                    onSearchCleared?.()
                },
            })
        }
        return tags
    }, [
        albumFilterKeys,
        context,
        filters,
        onSearchCleared,
        resetFilters,
        setFilter,
        setFilters,
        total,
    ])
}
