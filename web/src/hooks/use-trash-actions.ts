import { useCallback } from "react"
import { mediaRepo } from "@/api/media"
import { fulfilledIds } from "@/lib/promise-results"
import { useMediaQueryStore } from "@/stores/media-query"
import { useSelectionStore } from "@/stores/media-selection"

export interface UseTrashActionsResult {
    handleRestore: () => Promise<void>
    handleEmptyTrash: () => Promise<void>
    handleDeletePermanently: (ids: number[]) => Promise<void>
}

interface UseTrashActionsOpts {
    notify: (message: string) => void
    onCleanup?: () => void
}

/**
 * Encapsulates trash-only actions: bulk restore, empty trash, and permanent
 * delete. Each handler reconciles the query store on success so the UI updates
 * without a refetch when possible.
 */
export function useTrashActions({ notify, onCleanup }: UseTrashActionsOpts): UseTrashActionsResult {
    const { items, total, removeItems, resetFilters, fetchMedia } = useMediaQueryStore()
    const { selectionMode, selectedIds, exitSelectionMode } = useSelectionStore()

    const handleRestore = useCallback(async () => {
        let ids: number[]
        try {
            ids = selectionMode
                ? [...selectedIds]
                : (await mediaRepo.listTrash()).map((item) => item.id)
        } catch {
            notify("Could not load trash")
            return
        }
        if (ids.length === 0) return
        if (!window.confirm(`Restore ${ids.length} item(s)?`)) return

        const results = await Promise.allSettled(ids.map((id) => mediaRepo.restoreOne(id)))
        const restoredIds = fulfilledIds(ids, results)
        if (restoredIds.length === 0) {
            notify("Could not restore items")
            return
        }
        if (restoredIds.length < ids.length) {
            notify(`Restored ${restoredIds.length} of ${ids.length} items`)
        }
        removeItems(restoredIds)
        exitSelectionMode()
        onCleanup?.()

        const remainingTrashCount = selectionMode
            ? total - restoredIds.length
            : ids.length - restoredIds.length
        if (remainingTrashCount <= 0) {
            resetFilters()
        } else if (items.length - restoredIds.length <= 0) {
            await fetchMedia(true)
        }
    }, [items.length, notify, onCleanup, removeItems, resetFilters, selectedIds, selectionMode, exitSelectionMode, total, fetchMedia])

    const handleEmptyTrash = useCallback(async () => {
        let trashCount: number
        try {
            trashCount = (await mediaRepo.listTrash()).length
        } catch {
            notify("Could not load trash")
            return
        }
        if (trashCount === 0) {
            resetFilters()
            return
        }
        if (!window.confirm(`Permanently delete all ${trashCount} item(s) in Recently Deleted? This cannot be undone.`)) return
        try {
            await mediaRepo.emptyTrash()
            resetFilters()
        } catch {
            notify("Could not empty trash")
        }
    }, [notify, resetFilters])

    const handleDeletePermanently = useCallback(async (ids: number[]) => {
        if (ids.length === 0) return
        if (!window.confirm(`Permanently delete ${ids.length} item(s)?`)) return

        const results = await Promise.allSettled(ids.map((id) => mediaRepo.deleteOne(id, { permanent: true })))
        const deletedIds = fulfilledIds(ids, results)
        if (deletedIds.length === 0) {
            notify("Could not delete items")
            return
        }
        if (deletedIds.length < ids.length) {
            notify(`Deleted ${deletedIds.length} of ${ids.length} items`)
        }
        removeItems(deletedIds)
        exitSelectionMode()
        onCleanup?.()

        if (total - deletedIds.length <= 0) {
            resetFilters()
        } else if (items.length - deletedIds.length <= 0) {
            await fetchMedia(true)
        }
    }, [items.length, notify, onCleanup, removeItems, resetFilters, exitSelectionMode, total, fetchMedia])

    return { handleRestore, handleEmptyTrash, handleDeletePermanently }
}
