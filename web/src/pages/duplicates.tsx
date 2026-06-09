import { useCallback, useEffect, useState } from "react"
import { Copy, RefreshCw, Trash2 } from "lucide-react"
import { mediaRepo } from "@/api/media"
import { mediaUrl } from "@/lib/media-url"
import { formatBytes } from "@/lib/format"
import type { DuplicateGroup, Media } from "@/api/types"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Spinner } from "@/components/ui/spinner"
import { MediaDetailPanel } from "@/components/media-detail"
import { toast } from "@/stores/toast"
import { cn } from "@/lib/utils"

export default function DuplicatesPage() {
    const [groups, setGroups] = useState<DuplicateGroup[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [openItem, setOpenItem] = useState<{ items: Media[]; index: number } | null>(null)
    const [deleting, setDeleting] = useState<Set<number>>(new Set())

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            setGroups(await mediaRepo.listDuplicates({ minCount: 2, limit: 100 }))
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load duplicates")
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { void load() }, [load])

    const handleDelete = useCallback(async (id: number) => {
        if (!confirm("Move this duplicate to trash?")) return
        setDeleting((prev) => new Set(prev).add(id))
        try {
            await mediaRepo.deleteOne(id)
            setGroups((prev) =>
                prev
                    .map((g) => ({ ...g, items: g.items.filter((m) => m.id !== id), count: g.count - (g.items.some((m) => m.id === id) ? 1 : 0) }))
                    .filter((g) => g.items.length >= 2),
            )
            toast.success("Moved to trash")
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Delete failed")
        } finally {
            setDeleting((prev) => {
                const next = new Set(prev)
                next.delete(id)
                return next
            })
        }
    }, [])

    const totalDupes = groups.reduce((sum, g) => sum + Math.max(0, g.items.length - 1), 0)
    const totalBytes = groups.reduce(
        (sum, g) => sum + (g.items.slice(1).reduce((s, m) => s + m.file_size, 0)),
        0,
    )

    return (
        <div>
            <PageHeader
                title="Duplicates"
                back
                actions={
                    <button
                        type="button"
                        onClick={() => void load()}
                        aria-label="Refresh"
                        disabled={loading}
                        className="flex items-center justify-center h-9 w-9 rounded-full hover:bg-secondary transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                    </button>
                }
            />
            <div className="p-6 max-w-5xl mx-auto space-y-4">
                {groups.length > 0 && (
                    <Card>
                        <CardContent className="pt-5 pb-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
                            <div>
                                <p className="text-xs uppercase tracking-wider text-muted-foreground/70">Groups</p>
                                <p className="text-lg font-semibold tabular-nums">{groups.length}</p>
                            </div>
                            <div>
                                <p className="text-xs uppercase tracking-wider text-muted-foreground/70">Extra copies</p>
                                <p className="text-lg font-semibold tabular-nums">{totalDupes}</p>
                            </div>
                            <div>
                                <p className="text-xs uppercase tracking-wider text-muted-foreground/70">Reclaimable</p>
                                <p className="text-lg font-semibold tabular-nums">{formatBytes(totalBytes)}</p>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {loading && groups.length === 0 && (
                    <div className="py-12 flex justify-center"><Spinner /></div>
                )}

                {!loading && error && groups.length === 0 && (
                    <EmptyState
                        icon={Copy}
                        title="Couldn’t load duplicates"
                        description={error}
                        action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                    />
                )}

                {!loading && !error && groups.length === 0 && (
                    <EmptyState
                        icon={Copy}
                        title="No duplicates found"
                        description="Items with identical file hashes show up here."
                    />
                )}

                {groups.map((group) => (
                    <DuplicateGroupCard
                        key={group.file_hash}
                        group={group}
                        deleting={deleting}
                        onOpen={(idx) => setOpenItem({ items: group.items, index: idx })}
                        onDelete={handleDelete}
                    />
                ))}
            </div>

            {openItem && (
                <MediaDetailPanel
                    items={openItem.items}
                    startIndex={openItem.index}
                    onClose={() => setOpenItem(null)}
                    onDelete={(id) => {
                        setOpenItem(null)
                        void handleDelete(id)
                    }}
                />
            )}
        </div>
    )
}

function DuplicateGroupCard({ group, deleting, onOpen, onDelete }: {
    group: DuplicateGroup
    deleting: Set<number>
    onOpen: (index: number) => void
    onDelete: (id: number) => void
}) {
    return (
        <Card>
            <CardContent className="pt-4 pb-4 space-y-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground/80">
                    <span className="font-mono">{group.file_hash.slice(0, 12)}</span>
                    <span>·</span>
                    <span>{group.count} copies</span>
                    <span>·</span>
                    <span>{formatBytes(group.items[0]?.file_size ?? 0)} each</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                    {group.items.map((item, idx) => (
                        <DuplicateThumb
                            key={item.id}
                            item={item}
                            isOriginal={idx === 0}
                            deleting={deleting.has(item.id)}
                            onOpen={() => onOpen(idx)}
                            onDelete={() => onDelete(item.id)}
                        />
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}

function DuplicateThumb({ item, isOriginal, deleting, onOpen, onDelete }: {
    item: Media
    isOriginal: boolean
    deleting: boolean
    onOpen: () => void
    onDelete: () => void
}) {
    return (
        <div className="group relative rounded-lg overflow-hidden bg-secondary/40">
            <button
                type="button"
                onClick={onOpen}
                className="block w-full aspect-square focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
                <img
                    src={mediaUrl.thumbnail(item.id, "md")}
                    alt={item.filename}
                    loading="lazy"
                    className="h-full w-full object-cover"
                />
            </button>
            {isOriginal && (
                <span className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded-md bg-emerald-500/90 text-[10px] font-semibold uppercase tracking-wide text-white">
                    Keep
                </span>
            )}
            <button
                type="button"
                onClick={onDelete}
                disabled={deleting}
                aria-label="Move to trash"
                className="absolute top-1.5 right-1.5 h-7 w-7 rounded-full bg-black/60 backdrop-blur text-white opacity-0 group-hover:opacity-100 hover:bg-destructive/90 disabled:opacity-50 transition-opacity flex items-center justify-center"
            >
                <Trash2 className="h-3.5 w-3.5" />
            </button>
            <div className="absolute bottom-0 inset-x-0 p-2 bg-gradient-to-t from-black/70 to-transparent">
                <p className="text-[11px] text-white/90 truncate">{item.filename}</p>
            </div>
        </div>
    )
}
