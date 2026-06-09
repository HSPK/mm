import { useCallback, useState } from "react"
import { albumRepo, type AlbumSummary } from "@/api/albums"
import { mediaRepo } from "@/api/media"
import { fulfilledIds } from "@/lib/promise-results"
import { useMediaQueryStore } from "@/stores/media-query"
import { useSelectionStore } from "@/stores/media-selection"

export type AlbumPickerMode = false | "pick" | "create"

export interface UseAlbumActionsResult {
    mode: AlbumPickerMode
    openPicker: () => void
    openCreate: () => void
    close: () => void
    retryLoad: () => Promise<void>
    albums: AlbumSummary[]
    albumLoading: boolean
    albumLoadError: string | null
    busy: boolean
    newAlbumName: string
    setNewAlbumName: (value: string) => void
    addToAlbum: (albumId: number) => Promise<void>
    createAndAdd: () => Promise<void>
    handleDeleteSelected: () => Promise<void>
}

interface UseAlbumActionsOpts {
    notify: (message: string) => void
}

/**
 * State + handlers for the selection-bar album picker, plus the
 * batch-or-fallback delete used in the non-trash flow. Owns its own picker
 * mode so the bottom-bar component can stay presentational.
 */
export function useAlbumActions({ notify }: UseAlbumActionsOpts): UseAlbumActionsResult {
    const [mode, setMode] = useState<AlbumPickerMode>(false)
    const [albums, setAlbums] = useState<AlbumSummary[]>([])
    const [albumLoading, setAlbumLoading] = useState(false)
    const [albumLoadError, setAlbumLoadError] = useState<string | null>(null)
    const [busy, setBusy] = useState(false)
    const [newAlbumName, setNewAlbumName] = useState("")

    const removeItems = useMediaQueryStore((s) => s.removeItems)
    const fetchMedia = useMediaQueryStore((s) => s.fetchMedia)
    const { selectedIds, exitSelectionMode } = useSelectionStore()

    const close = useCallback(() => setMode(false), [])

    const loadAlbums = useCallback(async () => {
        setAlbumLoadError(null)
        setAlbumLoading(true)
        try {
            setAlbums(await albumRepo.list())
        } catch {
            setAlbums([])
            setAlbumLoadError("Could not load albums")
            notify("Could not load albums")
        } finally {
            setAlbumLoading(false)
        }
    }, [notify])

    const openPicker = useCallback(() => {
        setMode("pick")
        void loadAlbums()
    }, [loadAlbums])

    const openCreate = useCallback(() => setMode("create"), [])

    const addToAlbum = useCallback(async (albumId: number) => {
        setBusy(true)
        try {
            await albumRepo.addMedia(albumId, [...selectedIds])
            setMode(false)
        } catch {
            notify("Could not add to album")
        } finally {
            setBusy(false)
        }
    }, [notify, selectedIds])

    const createAndAdd = useCallback(async () => {
        const name = newAlbumName.trim()
        if (!name) return
        setBusy(true)
        try {
            const created = await albumRepo.create(name)
            await albumRepo.addMedia(created.id, [...selectedIds])
            setNewAlbumName("")
            setMode(false)
        } catch {
            notify("Could not create album")
        } finally {
            setBusy(false)
        }
    }, [newAlbumName, notify, selectedIds])

    const handleDeleteSelected = useCallback(async () => {
        const ids = [...selectedIds]
        if (ids.length === 0) return
        let deletedIds = ids
        try {
            const res = await mediaRepo.batchDelete(ids)
            if (res.affected < ids.length) {
                notify(`Deleted ${res.affected} of ${ids.length} items`)
                exitSelectionMode()
                setMode(false)
                await fetchMedia(true)
                return
            }
        } catch {
            const results = await Promise.allSettled(ids.map((id) => mediaRepo.deleteOne(id)))
            deletedIds = fulfilledIds(ids, results)
            if (deletedIds.length === 0) {
                notify("Could not delete items")
                return
            }
            if (deletedIds.length < ids.length) {
                notify(`Deleted ${deletedIds.length} of ${ids.length} items`)
            }
        }
        removeItems(deletedIds)
        exitSelectionMode()
        setMode(false)
    }, [exitSelectionMode, fetchMedia, notify, removeItems, selectedIds])

    return {
        mode,
        openPicker,
        openCreate,
        close,
        retryLoad: loadAlbums,
        albums,
        albumLoading,
        albumLoadError,
        busy,
        newAlbumName,
        setNewAlbumName,
        addToAlbum,
        createAndAdd,
        handleDeleteSelected,
    }
}
