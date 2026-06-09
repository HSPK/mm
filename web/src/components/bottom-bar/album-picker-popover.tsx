import { useEffect, useRef } from "react"
import { AlertTriangle, FolderPlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { UseAlbumActionsResult } from "@/hooks/use-album-actions"

interface AlbumPickerPopoverProps {
    actions: UseAlbumActionsResult
}

export function AlbumPickerPopover({ actions }: AlbumPickerPopoverProps) {
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        if (actions.mode === "create") inputRef.current?.focus()
    }, [actions.mode])

    if (!actions.mode) return null

    return (
        <div className="flex justify-center px-4 pb-2">
            <div className="w-full max-w-xs bg-popover border border-border rounded-2xl shadow-xl overflow-hidden">
                {actions.mode === "pick"
                    ? <PickList actions={actions} />
                    : <CreateForm actions={actions} inputRef={inputRef} />}
            </div>
        </div>
    )
}

function PickList({ actions }: { actions: UseAlbumActionsResult }) {
    return (
        <div className="max-h-48 overflow-y-auto p-1.5">
            {actions.albumLoading ? (
                <div className="flex items-center justify-center gap-2 py-4 text-xs text-muted-foreground/60">
                    <Spinner size="sm" />
                    <span>Loading albums…</span>
                </div>
            ) : actions.albumLoadError ? (
                <div className="flex flex-col items-center gap-2 py-4 text-center text-xs text-muted-foreground/60">
                    <AlertTriangle className="h-4 w-4 text-destructive/70" />
                    <span>{actions.albumLoadError}</span>
                    <button
                        type="button"
                        onClick={actions.retryLoad}
                        className="rounded-full bg-secondary px-3 py-1 font-medium text-foreground/75 hover:bg-secondary/80"
                    >
                        Retry
                    </button>
                </div>
            ) : actions.albums.length === 0 ? (
                <p className="text-xs text-muted-foreground/50 text-center py-4">No albums yet</p>
            ) : null}
            {!actions.albumLoading && !actions.albumLoadError && actions.albums.map((a) => (
                <button
                    key={a.id}
                    onClick={() => actions.addToAlbum(a.id)}
                    disabled={actions.busy}
                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-sm text-foreground/80 hover:bg-secondary transition-colors text-left disabled:opacity-50"
                >
                    <FolderPlus className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
                    <span className="truncate">{a.name}</span>
                </button>
            ))}
            <button
                onClick={actions.openCreate}
                disabled={actions.albumLoading || actions.busy}
                className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-sm text-primary/80 hover:bg-primary/5 transition-colors text-left"
            >
                <span className="h-3.5 w-3.5 flex items-center justify-center text-primary/60 shrink-0 text-base leading-none">+</span>
                <span>New album…</span>
            </button>
        </div>
    )
}

function CreateForm({
    actions,
    inputRef,
}: {
    actions: UseAlbumActionsResult
    inputRef: React.RefObject<HTMLInputElement | null>
}) {
    return (
        <div className="flex items-center gap-2 p-2.5">
            <input
                ref={inputRef}
                type="text"
                value={actions.newAlbumName}
                onChange={(e) => actions.setNewAlbumName(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === "Enter") actions.createAndAdd()
                    if (e.key === "Escape") actions.openPicker()
                }}
                placeholder="Album name"
                className="flex-1 h-9 rounded-lg bg-secondary px-3 text-sm outline-none focus:ring-1 focus:ring-ring/40 text-foreground placeholder:text-muted-foreground/40"
            />
            <Button
                size="sm"
                className="rounded-lg h-9 px-4 text-xs"
                onClick={actions.createAndAdd}
                disabled={!actions.newAlbumName.trim()}
                loading={actions.busy}
            >
                {actions.busy ? "" : "Create"}
            </Button>
        </div>
    )
}
