import { useCallback, useEffect, useState } from "react"
import { ChevronRight, File, Folder, HardDrive, X } from "lucide-react"
import { filesRepo, type FileBrowserEntry, type FileBrowserResponse, type FileSelectMode } from "@/api/files"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { formatBytes } from "@/lib/format"
import { cn } from "@/lib/utils"

interface ServerFilePickerProps {
    open: boolean
    title?: string
    select?: FileSelectMode
    initialPath?: string
    onSelect: (path: string) => void
    onClose: () => void
}

export function ServerFilePicker({
    open,
    title = "Choose server path",
    select = "any",
    initialPath,
    onSelect,
    onClose,
}: ServerFilePickerProps) {
    const [path, setPath] = useState(initialPath ?? "")
    const [data, setData] = useState<FileBrowserResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const browse = useCallback(async (nextPath?: string) => {
        setLoading(true)
        setError(null)
        try {
            const result = await filesRepo.browse(nextPath, select)
            setData(result)
            setPath(result.path)
        } catch (err) {
            setError(err instanceof Error ? err.message : "Could not browse server path")
        } finally {
            setLoading(false)
        }
    }, [select])

    useEffect(() => {
        if (!open) return
        const id = window.setTimeout(() => { void browse(initialPath) }, 0)
        return () => window.clearTimeout(id)
    }, [browse, initialPath, open])

    if (!open) return null

    return (
        <div className="fixed inset-0 z-[10020] flex items-center justify-center bg-black/45 p-4">
            <div className="flex max-h-[82vh] w-full max-w-3xl flex-col overflow-hidden rounded-[2rem] bg-popover text-popover-foreground shadow-2xl">
                <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
                    <div>
                        <h2 className="text-[17px] font-semibold">{title}</h2>
                        <p className="mt-0.5 text-[12px] text-muted-foreground">Server filesystem path</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                        aria-label="Close"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                <div className="space-y-3 border-b border-border px-5 py-4">
                    <div className="rounded-2xl bg-secondary/55 px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                            Current path
                        </p>
                        <p className="mt-1 truncate font-mono text-[13px] text-foreground/85">
                            {path || "..."}
                        </p>
                    </div>
                    {data && (
                        <div className="flex flex-wrap gap-1.5">
                            {data.roots.map((root) => (
                                <button
                                    key={root}
                                    type="button"
                                    onClick={() => void browse(root)}
                                    className="inline-flex items-center gap-1 rounded-full bg-secondary/60 px-2.5 py-1 text-[12px] text-muted-foreground hover:text-foreground"
                                >
                                    <HardDrive className="h-3 w-3" />
                                    {root}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-2">
                    {loading && !data && (
                        <div className="flex justify-center py-12"><Spinner /></div>
                    )}
                    {error && (
                        <p className="m-3 rounded-2xl bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
                    )}
                    {data?.parent && (
                        <EntryRow
                            entry={{
                                name: "..",
                                path: data.parent,
                                is_dir: true,
                                is_file: false,
                                extension: "",
                                selectable: false,
                            }}
                            onOpen={() => void browse(data.parent ?? undefined)}
                            onChoose={onSelect}
                        />
                    )}
                    {data?.entries.map((entry) => (
                        <EntryRow
                            key={entry.path}
                            entry={entry}
                            onOpen={() => entry.is_dir ? void browse(entry.path) : undefined}
                            onChoose={onSelect}
                        />
                    ))}
                </div>

                <div className="flex justify-end gap-2 border-t border-border px-5 py-4">
                    <Button variant="plain" onClick={onClose}>Cancel</Button>
                    <Button
                        onClick={() => onSelect(path)}
                        disabled={!path.trim()}
                    >
                        Use path
                    </Button>
                </div>
            </div>
        </div>
    )
}

function EntryRow({
    entry,
    onOpen,
    onChoose,
}: {
    entry: FileBrowserEntry
    onOpen: () => void
    onChoose: (path: string) => void
}) {
    const Icon = entry.is_dir ? Folder : File
    return (
        <div className="group flex items-center gap-3 rounded-2xl px-3 py-2 hover:bg-secondary/50">
            <button
                type="button"
                onClick={onOpen}
                className="flex min-w-0 flex-1 items-center gap-3 text-left"
            >
                <div className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl",
                    entry.is_dir ? "bg-primary/12 text-primary" : "bg-secondary text-muted-foreground",
                )}>
                    <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{entry.name}</p>
                    <p className="truncate text-[12px] text-muted-foreground">
                        {entry.is_dir ? "Folder" : [entry.extension || "file", entry.size != null ? formatBytes(entry.size) : null].filter(Boolean).join(" · ")}
                    </p>
                </div>
                {entry.is_dir && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            </button>
            <Button
                size="sm"
                variant="plain"
                disabled={!entry.selectable}
                onClick={() => onChoose(entry.path)}
                className="opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
            >
                Choose
            </Button>
        </div>
    )
}
