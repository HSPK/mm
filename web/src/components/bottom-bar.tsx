import { useState, useEffect, useRef, useCallback, type MutableRefObject, type RefObject } from "react"
import { NavLink } from "react-router-dom"
import {
    Trash2,
    FolderPlus,
    CheckCheck,
    X,
    RotateCcw,
    Loader2,
    AlertTriangle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useMediaStore } from "@/stores/media"
import { api } from "@/api/client"
import { Button } from "@/components/ui/button"
import { navItems } from "@/components/navigation/nav-items"
import type { Media } from "@/api/types"

function fulfilledIds<T>(ids: number[], results: PromiseSettledResult<T>[]) {
    return ids.filter((_, index) => results[index].status === "fulfilled")
}

// ─── Bottom Bar: morphs between nav tabs and selection action bar ──

export function BottomBar({
    isTabRoute,
    navVisible,
    navRef,
    itemRefs,
    indicator,
}: {
    isTabRoute: boolean
    navVisible: boolean
    navRef: RefObject<HTMLElement | null>
    itemRefs: MutableRefObject<(HTMLAnchorElement | null)[]>
    indicator: { left: number; width: number }
}) {
    const {
        selectionMode, selectedIds, items, total,
        exitSelectionMode, selectAll, removeItems,
        filters, resetFilters,
        activeLabel: viewingAlbum,
        fetchMedia,
    } = useMediaStore()

    const isDeletedView = filters.deleted

    const [albumMode, setAlbumMode] = useState<false | "pick" | "create">(false)
    const [albums, setAlbums] = useState<{ id: number; name: string }[]>([])
    const [newAlbumName, setNewAlbumName] = useState("")
    const [busy, setBusy] = useState(false)
    const [albumLoading, setAlbumLoading] = useState(false)
    const [albumLoadError, setAlbumLoadError] = useState<string | null>(null)
    const [notice, setNotice] = useState<string | null>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        if (selectionMode) return
        const t = window.setTimeout(() => setAlbumMode(false), 0)
        return () => window.clearTimeout(t)
    }, [selectionMode])

    useEffect(() => {
        if (albumMode === "create") inputRef.current?.focus()
    }, [albumMode])

    useEffect(() => {
        if (!notice) return
        const t = window.setTimeout(() => setNotice(null), 2600)
        return () => window.clearTimeout(t)
    }, [notice])

    const loadAlbums = useCallback(async () => {
        setNotice(null)
        setAlbumLoadError(null)
        setAlbumLoading(true)
        try {
            const res = await api.get<{ id: number; name: string }[]>("/albums")
            setAlbums(res.data)
        } catch {
            setAlbums([])
            setAlbumLoadError("Could not load albums")
            setNotice("Could not load albums")
        } finally {
            setAlbumLoading(false)
        }
    }, [])

    const addToAlbum = async (albumId: number) => {
        setBusy(true)
        setNotice(null)
        try {
            await api.post(`/albums/${albumId}/media`, { media_ids: [...selectedIds] })
            setAlbumMode(false)
        } catch {
            setNotice("Could not add to album")
        } finally {
            setBusy(false)
        }
    }

    const createAndAdd = async () => {
        const name = newAlbumName.trim()
        if (!name) return
        setBusy(true)
        setNotice(null)
        try {
            const res = await api.post<{ id: number }>("/albums", { name })
            await api.post(`/albums/${res.data.id}/media`, { media_ids: [...selectedIds] })
            setNewAlbumName("")
            setAlbumMode(false)
        } catch {
            setNotice("Could not create album")
        } finally {
            setBusy(false)
        }
    }

    const handleDelete = async () => {
        const ids = [...selectedIds]
        if (ids.length === 0) return
        if (isDeletedView) {
            if (!window.confirm(`Permanently delete ${ids.length} item(s)?`)) return
            const results = await Promise.allSettled(ids.map((id) => api.delete(`/media/${id}`, { params: { permanent: true } })))
            const deletedIds = fulfilledIds(ids, results)
            if (deletedIds.length === 0) {
                setNotice("Could not delete items")
                return
            }
            if (deletedIds.length < ids.length) {
                setNotice(`Deleted ${deletedIds.length} of ${ids.length} items`)
            }
            removeItems(deletedIds)
            exitSelectionMode()
            setAlbumMode(false)
            if (total - deletedIds.length <= 0) {
                resetFilters()
            } else if (items.length - deletedIds.length <= 0) {
                await fetchMedia(true)
            }
        } else {
            let deletedIds = ids
            try {
                const res = await api.post<{ affected: number }>("/batch/delete", { media_ids: ids })
                if (res.data.affected < ids.length) {
                    setNotice(`Deleted ${res.data.affected} of ${ids.length} items`)
                    exitSelectionMode()
                    setAlbumMode(false)
                    await fetchMedia(true)
                    return
                }
            } catch {
                const results = await Promise.allSettled(ids.map((id) => api.delete(`/media/${id}`)))
                deletedIds = fulfilledIds(ids, results)
                if (deletedIds.length === 0) {
                    setNotice("Could not delete items")
                    return
                }
                if (deletedIds.length < ids.length) {
                    setNotice(`Deleted ${deletedIds.length} of ${ids.length} items`)
                }
            }
            removeItems(deletedIds)
            exitSelectionMode()
            setAlbumMode(false)
        }
    }

    const handleRestore = async () => {
        let ids: number[]
        try {
            if (selectionMode) {
                ids = [...selectedIds]
            } else {
                const res = await api.get<Media[]>("/media/trash")
                ids = res.data.map((item) => item.id)
            }
        } catch {
            setNotice("Could not load trash")
            return
        }
        if (ids.length === 0) return
        if (!window.confirm(`Restore ${ids.length} item(s)?`)) return
        const results = await Promise.allSettled(ids.map((id) => api.post(`/media/${id}/restore`)))
        const restoredIds = ids.filter((_, index) => results[index].status === "fulfilled")
        if (restoredIds.length === 0) {
            setNotice("Could not restore items")
            return
        }
        if (restoredIds.length < ids.length) {
            setNotice(`Restored ${restoredIds.length} of ${ids.length} items`)
        }
        removeItems(restoredIds)
        exitSelectionMode()
        setAlbumMode(false)
        const remainingTrashCount = selectionMode
            ? total - restoredIds.length
            : ids.length - restoredIds.length
        if (remainingTrashCount <= 0) {
            resetFilters()
        } else if (items.length - restoredIds.length <= 0) {
            await fetchMedia(true)
        }
    }

    const handleEmptyTrash = async () => {
        let trashCount: number
        try {
            const res = await api.get<Media[]>("/media/trash")
            trashCount = res.data.length
        } catch {
            setNotice("Could not load trash")
            return
        }
        if (trashCount === 0) {
            resetFilters()
            return
        }
        if (!window.confirm(`Permanently delete all ${trashCount} item(s) in Recently Deleted? This cannot be undone.`)) return
        try {
            await api.delete("/media/trash")
            resetFilters()
        } catch {
            setNotice("Could not empty trash")
        }
    }

    const show = isTabRoute && (selectionMode || isDeletedView || (navVisible && !viewingAlbum))

    return (
        <div
            className={cn(
                "fixed bottom-0 left-0 right-0 z-30 transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                show ? "translate-y-0" : "translate-y-full",
            )}
            aria-hidden={!show}
            inert={show ? undefined : true}
            style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
        >
            {/* Album picker dropdown — sits above the bar */}
            {notice && (
                <div className="flex justify-center px-4 pb-2">
                    <div className="rounded-full bg-destructive/12 px-4 py-2 text-xs font-medium text-destructive shadow-lg backdrop-blur-xl">
                        {notice}
                    </div>
                </div>
            )}

            {selectionMode && albumMode && (
                <div className="flex justify-center px-4 pb-2">
                    <div className="w-full max-w-xs bg-popover border border-border rounded-2xl shadow-xl overflow-hidden">
                        {albumMode === "pick" ? (
                            <div className="max-h-48 overflow-y-auto p-1.5">
                                {albumLoading ? (
                                    <div className="flex items-center justify-center gap-2 py-4 text-xs text-muted-foreground/60">
                                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                        <span>Loading albums…</span>
                                    </div>
                                ) : albumLoadError ? (
                                    <div className="flex flex-col items-center gap-2 py-4 text-center text-xs text-muted-foreground/60">
                                        <AlertTriangle className="h-4 w-4 text-destructive/70" />
                                        <span>{albumLoadError}</span>
                                        <button
                                            type="button"
                                            onClick={loadAlbums}
                                            className="rounded-full bg-secondary px-3 py-1 font-medium text-foreground/75 hover:bg-secondary/80"
                                        >
                                            Retry
                                        </button>
                                    </div>
                                ) : albums.length === 0 ? (
                                    <p className="text-xs text-muted-foreground/50 text-center py-4">No albums yet</p>
                                ) : null}
                                {!albumLoading && !albumLoadError && albums.map((a) => (
                                    <button
                                        key={a.id}
                                        onClick={() => addToAlbum(a.id)}
                                        disabled={busy}
                                        className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-sm text-foreground/80 hover:bg-secondary transition-colors text-left disabled:opacity-50"
                                    >
                                        <FolderPlus className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
                                        <span className="truncate">{a.name}</span>
                                    </button>
                                ))}
                                <button
                                    onClick={() => setAlbumMode("create")}
                                    disabled={albumLoading || busy}
                                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-sm text-primary/80 hover:bg-primary/5 transition-colors text-left"
                                >
                                    <span className="h-3.5 w-3.5 flex items-center justify-center text-primary/60 shrink-0 text-base leading-none">+</span>
                                    <span>New album…</span>
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 p-2.5">
                                <input
                                    ref={inputRef}
                                    type="text"
                                    value={newAlbumName}
                                    onChange={(e) => setNewAlbumName(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") createAndAdd()
                                        if (e.key === "Escape") setAlbumMode("pick")
                                    }}
                                    placeholder="Album name"
                                    className="flex-1 h-9 rounded-lg bg-secondary px-3 text-sm outline-none focus:ring-1 focus:ring-ring/40 text-foreground placeholder:text-muted-foreground/40"
                                />
                                <Button
                                    size="sm"
                                    className="rounded-lg h-9 px-4 text-xs"
                                    onClick={createAndAdd}
                                    disabled={!newAlbumName.trim() || busy}
                                >
                                    {busy ? "…" : "Create"}
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* The bar itself */}
            <div className="flex justify-center px-4 pb-4">
                {selectionMode ? (
                    /* ── Selection action bar ── */
                    <div className="relative flex items-center gap-1 px-2 py-1.5 bg-background border border-border shadow-2xl shadow-black/10 rounded-full">
                        <button
                            onClick={() => { setAlbumMode(false); exitSelectionMode() }}
                            className="relative z-10 flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                        >
                            <X className="h-[1.15rem] w-[1.15rem]" />
                            <span>Cancel</span>
                        </button>

                        <span className="text-[10px] font-semibold text-foreground/80 px-2 tabular-nums">
                            {selectedIds.size}
                        </span>

                        <button
                            onClick={selectAll}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                            title="Select all"
                        >
                            <CheckCheck className="h-[1.15rem] w-[1.15rem]" />
                            <span>All</span>
                        </button>

                        {isDeletedView ? (
                            <>
                                <button
                                    onClick={handleRestore}
                                    className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                                    title="Restore"
                                >
                                    <RotateCcw className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Restore</span>
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-destructive/70 hover:text-destructive transition-colors"
                                    title="Delete permanently"
                                >
                                    <Trash2 className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Delete</span>
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    onClick={() => {
                                        if (albumMode) {
                                            setAlbumMode(false)
                                        } else {
                                            setAlbumMode("pick")
                                            void loadAlbums()
                                        }
                                    }}
                                    className={cn(
                                        "relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium transition-colors",
                                        albumMode ? "text-primary" : "text-muted-foreground/70 hover:text-foreground"
                                    )}
                                    title="Add to album"
                                >
                                    <FolderPlus className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Album</span>
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-destructive/70 hover:text-destructive transition-colors"
                                    title="Delete"
                                >
                                    <Trash2 className="h-[1.15rem] w-[1.15rem]" />
                                    <span>Delete</span>
                                </button>
                            </>
                        )}
                    </div>
                ) : isDeletedView ? (
                    /* ── Trash default bar ── */
                    <div className="relative flex items-center gap-1 px-2 py-1.5 bg-background border border-border shadow-2xl shadow-black/10 rounded-full">
                        <button
                            onClick={resetFilters}
                            className="relative z-10 flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                        >
                            <X className="h-[1.15rem] w-[1.15rem]" />
                            <span>Back</span>
                        </button>

                        <span className="text-[10px] font-semibold text-foreground/80 px-2 tabular-nums">
                            {total}
                        </span>

                        <button
                            onClick={selectAll}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                            title="Select all"
                        >
                            <CheckCheck className="h-[1.15rem] w-[1.15rem]" />
                            <span>All</span>
                        </button>
                        <button
                            onClick={handleRestore}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-muted-foreground/70 hover:text-foreground transition-colors"
                            title="Restore all"
                        >
                            <RotateCcw className="h-[1.15rem] w-[1.15rem]" />
                            <span>Restore</span>
                        </button>
                        <button
                            onClick={handleEmptyTrash}
                            className="relative z-10 flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-full text-[10px] font-medium text-destructive/70 hover:text-destructive transition-colors"
                            title="Empty trash"
                        >
                            <Trash2 className="h-[1.15rem] w-[1.15rem]" />
                            <span>Empty</span>
                        </button>
                    </div>
                ) : (
                    /* ── Normal tab navigation ── */
                    <nav
                        ref={navRef}
                        className="relative flex items-center gap-1 px-2 py-2 bg-background/80 backdrop-blur-xl border border-border/60 shadow-2xl shadow-black/10 rounded-full"
                    >
                        <div
                            className="absolute top-2 h-[calc(100%-1rem)] rounded-full bg-primary/12 transition-all duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]"
                            style={{ left: indicator.left, width: indicator.width }}
                        />
                        {navItems.map((item, i) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                end={item.to === "/"}
                                ref={(el) => { itemRefs.current[i] = el }}
                                className={({ isActive }) =>
                                    cn(
                                        "relative z-10 flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-full text-[10px] font-medium transition-colors duration-200",
                                        isActive
                                            ? "text-primary"
                                            : "text-muted-foreground/50 hover:text-foreground/70",
                                    )
                                }
                            >
                                <item.icon className="h-[1.15rem] w-[1.15rem]" />
                                <span>{item.label}</span>
                            </NavLink>
                        ))}
                    </nav>
                )}
            </div>
        </div>
    )
}
