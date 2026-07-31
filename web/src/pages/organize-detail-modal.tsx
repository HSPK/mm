import { createPortal } from "react-dom"
import { useEffect, useState } from "react"
import { Pencil, X } from "lucide-react"
import { organizerRepo, type OrganizerItem } from "@/api/organizer"
import { cn } from "@/lib/utils"
import { ArtworkCanvasTab, DetailsTab, FilesTab } from "./organize-detail-tabs"
import { type MediaRow, type MetadataEditValues, rowFromFiles } from "./organize-model"

type DetailTab = "details" | "files" | "artwork"

export function MediaDetailModal({
    open,
    row,
    editing,
    onEdit,
    onClose,
    onSaveEdit,
    onCancelEdit,
}: {
    open: boolean
    row: MediaRow | null
    editing: boolean
    onEdit: () => void
    onClose: () => void
    onSaveEdit: (row: MediaRow, values: MetadataEditValues) => void
    onCancelEdit: () => void
}) {
    if (!open || !row) return null
    return createPortal(
        <MediaDetailModalContent
            key={row.key}
            row={row}
            editing={editing}
            onEdit={onEdit}
            onClose={onClose}
            onSaveEdit={onSaveEdit}
            onCancelEdit={onCancelEdit}
        />,
        document.body,
    )
}

function MediaDetailModalContent({
    row,
    editing,
    onEdit,
    onClose,
    onSaveEdit,
    onCancelEdit,
}: {
    row: MediaRow
    editing: boolean
    onEdit: () => void
    onClose: () => void
    onSaveEdit: (row: MediaRow, values: MetadataEditValues) => void
    onCancelEdit: () => void
}) {
    const [tab, setTab] = useState<DetailTab>("details")
    const [detailFiles, setDetailFiles] = useState<OrganizerItem[] | null>(null)
    const [detailError, setDetailError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        setDetailFiles(null)
        setDetailError(null)
        void organizerRepo.details(row.files)
            .then((items) => {
                if (!cancelled) setDetailFiles(items)
            })
            .catch((error) => {
                if (!cancelled) setDetailError(error instanceof Error ? error.message : "Could not load read-only details.")
            })
        return () => {
            cancelled = true
        }
    }, [row.key, row.files])

    const detailRow = detailFiles
        ? rowFromFiles(row.key, row.kind, detailFiles, new Map(), {}, {
            expandable: row.expandable,
            expanded: row.expanded,
            season: row.season,
            track: row.track,
        })
        : row

    useEffect(() => {
        const handler = (event: KeyboardEvent) => {
            if (event.key === "Escape") onClose()
        }
        window.addEventListener("keydown", handler)
        return () => window.removeEventListener("keydown", handler)
    }, [onClose])

    useEffect(() => {
        const previous = document.body.style.overflow
        document.body.style.overflow = "hidden"
        return () => {
            document.body.style.overflow = previous
        }
    }, [])

    return (
        <div
            className="fixed inset-0 z-[10010] flex items-center justify-center bg-black/40 p-4"
            onClick={onClose}
            onWheel={(event) => event.stopPropagation()}
            onTouchMove={(event) => event.stopPropagation()}
        >
            <section
                role="dialog"
                aria-modal="true"
                aria-label={`${detailRow.title} details`}
                onClick={(event) => event.stopPropagation()}
                className="flex h-[86vh] w-full max-w-6xl flex-col overflow-hidden rounded-[1.5rem] bg-background shadow-2xl"
            >
                <div className="grid grid-cols-[1fr_auto_1fr] items-center border-b border-border/70 px-5 py-4">
                    <div className="min-w-0 pr-4">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                            Media details
                        </p>
                        <h2 className="mt-1 truncate text-xl font-bold tracking-tight">{detailRow.title}</h2>
                    </div>
                    <div className="flex rounded-full bg-secondary/45 p-1">
                        {(["details", "files", "artwork"] as const).map((item) => (
                            <button
                                key={item}
                                type="button"
                                onClick={() => setTab(item)}
                                className={cn(
                                    "h-8 rounded-full px-3 text-sm font-semibold capitalize transition-colors",
                                    tab === item ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
                                )}
                            >
                                {item}
                            </button>
                        ))}
                    </div>
                    <div className="flex justify-end gap-2">
                        <button
                            type="button"
                            onClick={onEdit}
                            aria-label={editing ? "Stop editing" : "Edit details"}
                            disabled={!detailRow.files[0]?.item_uid || detailRow.files[0]?.revision == null}
                            title={!detailRow.files[0]?.item_uid ? "Legacy items cannot be saved until they are synced." : undefined}
                            className={cn(
                                "flex h-9 items-center gap-1.5 rounded-full px-3 text-sm font-semibold transition-colors",
                                editing ? "bg-primary/10 text-primary" : "bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground",
                            )}
                        >
                            <Pencil className="h-4 w-4" />
                            {editing ? "Done" : "Edit"}
                        </button>
                        <button
                            type="button"
                            onClick={onClose}
                            aria-label="Close details"
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-5">
                    {detailError && <p role="alert" className="mb-4 rounded-xl bg-destructive/10 px-3 py-2 text-sm text-destructive">{detailError}</p>}
                    <p className="mb-3 text-xs text-muted-foreground">Details are a read-only projection. Saving edits updates the projection only unless Write NFO is selected.</p>
                    {tab === "details" && (
                        <DetailsTab
                            row={detailRow}
                            editing={editing}
                            onSaveEdit={onSaveEdit}
                            onCancelEdit={onCancelEdit}
                        />
                    )}
                    {tab === "files" && <FilesTab row={detailRow} />}
                    {tab === "artwork" && <ArtworkCanvasTab row={detailRow} />}
                </div>
            </section>
        </div>
    )
}
