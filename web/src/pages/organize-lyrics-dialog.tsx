import { createPortal } from "react-dom"
import { useEffect, useRef, useState } from "react"
import { Captions, FileSearch, X } from "lucide-react"
import { organizerRepo, type OrganizerItem, type OrganizerLyricsCandidate } from "@/api/organizer"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { notify } from "@/stores/notifications"
import { cn } from "@/lib/utils"
import { LabeledSearchInput } from "./organize-form-controls"
import { basename, cleanTrackTitle, errorMessage } from "./organize-model"

interface LyricsSearchDialogProps {
    file: OrganizerItem | null
    sourcePaths: string[]
    defaultSource: string
    onClose: () => void
    onApplied: () => Promise<void>
}

export function LyricsSearchDialog(props: LyricsSearchDialogProps) {
    if (!props.file) return null
    return (
        <LyricsDialogContent
            key={`${props.file.item_uid ?? props.file.path}:${props.defaultSource}`}
            {...props}
            file={props.file}
        />
    )
}

function LyricsDialogContent({
    file,
    sourcePaths,
    defaultSource,
    onClose,
    onApplied,
}: Omit<LyricsSearchDialogProps, "file"> & { file: OrganizerItem }) {
    const [title, setTitle] = useState(() => cleanTrackTitle(file))
    const [artist, setArtist] = useState(() => file.artist ?? "")
    const [album, setAlbum] = useState(() => file.album ?? "")
    const [lyricsSource, setLyricsSource] = useState(defaultSource)
    const [candidates, setCandidates] = useState<OrganizerLyricsCandidate[]>([])
    const [activeKey, setActiveKey] = useState("")
    const [loading, setLoading] = useState(false)
    const [applying, setApplying] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const requestRef = useRef<{ generation: number, controller?: AbortController }>({ generation: 0 })
    const active = candidates.find((candidate) => candidate.source_id === activeKey) ?? candidates[0] ?? null
    const close = () => {
        requestRef.current.controller?.abort()
        requestRef.current.generation += 1
        onClose()
    }

    useEffect(() => () => {
        requestRef.current.controller?.abort()
        requestRef.current.generation += 1
    }, [])

    const runSearch = async () => {
        requestRef.current.controller?.abort()
        requestRef.current.generation += 1
        const generation = requestRef.current.generation
        const controller = new AbortController()
        requestRef.current.controller = controller
        setLoading(true)
        setError(null)
        try {
            const results = await organizerRepo.lyricsSearch({
                path: file.path,
                title,
                artist,
                album,
                source: lyricsSource,
                limit: 8,
            }, { signal: controller.signal })
            if (generation !== requestRef.current.generation) return
            setCandidates(results)
            setActiveKey(results[0]?.source_id ?? "")
        } catch (error) {
            if (!controller.signal.aborted && generation === requestRef.current.generation) {
                setError(errorMessage(error))
            }
        } finally {
            if (generation === requestRef.current.generation) setLoading(false)
        }
    }

    const applyLyrics = async () => {
        if (!active) return
        const exists = Boolean(
            file.lyrics
            || file.metadata_lyrics?.trim()
            || file.metadata_synced_lyrics?.trim(),
        )
        if (exists && !window.confirm("This track already has lyrics. Overwrite them?")) return
        setApplying(true)
        setError(null)
        try {
            const result = await organizerRepo.lyricsApply({
                path: file.path,
                lyrics: active.lyrics,
                synced_lyrics: active.synced_lyrics,
                overwrite: exists,
            })
            notify.success("Lyrics saved", result.message)
            await onApplied()
        } catch (error) {
            setError(errorMessage(error))
        } finally {
            setApplying(false)
        }
    }

    return createPortal(
        <div className="fixed inset-0 z-[10020] flex items-center justify-center bg-black/40 p-4" onClick={close}>
            <section
                role="dialog"
                aria-modal="true"
                aria-label="Search lyrics"
                onClick={(event) => event.stopPropagation()}
                className="flex max-h-[82vh] w-full max-w-4xl flex-col overflow-hidden rounded-[1.25rem] bg-background shadow-2xl"
            >
                <div className="flex items-center justify-between border-b border-border px-5 py-3">
                    <div>
                        <h2 className="text-lg font-bold">Search lyrics</h2>
                        <p className="truncate font-mono text-xs text-muted-foreground">
                            {relativeToSource(file.path, sourcePaths)}
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={close}
                        className="flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                        aria-label="Close lyrics dialog"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <div className="border-b border-border px-4 py-3">
                    <div className="grid w-full items-end gap-3 md:grid-cols-[9rem_minmax(0,1fr)_minmax(10rem,0.55fr)_minmax(10rem,0.75fr)_6.25rem]">
                        <label className="space-y-1">
                            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                Source
                            </span>
                            <select
                                value={lyricsSource}
                                onChange={(event) => setLyricsSource(event.target.value)}
                                className="h-10 w-full rounded-xl bg-secondary/60 px-3 text-sm outline-none"
                            >
                                <option value="lrclib">LRCLIB</option>
                                <option value="netease">网易云</option>
                                <option value="qq">QQ Music</option>
                                <option value="all">All</option>
                            </select>
                        </label>
                        <LabeledSearchInput label="Track" value={title} onChange={setTitle} />
                        <LabeledSearchInput label="Artist" value={artist} onChange={setArtist} />
                        <LabeledSearchInput label="Album" value={album} onChange={setAlbum} />
                        <Button
                            size="sm"
                            variant="tinted"
                            disabled={loading}
                            onClick={() => void runSearch()}
                            className="h-10 w-full"
                        >
                            <FileSearch className="h-4 w-4" />
                            Search
                        </Button>
                    </div>
                    {loading && (
                        <div className="mt-2 h-0.5 w-full overflow-hidden rounded-full bg-secondary">
                            <div className="h-full w-1/3 animate-[shimmer_1s_infinite] bg-primary" />
                        </div>
                    )}
                    {error && <p role="alert" className="mt-2 text-sm text-destructive">{error}</p>}
                </div>
                <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_minmax(18rem,0.8fr)]">
                    <div className="min-h-0 overflow-y-auto border-r border-border p-3">
                        {candidates.length === 0 ? (
                            <EmptyState
                                icon={Captions}
                                title={loading ? "Searching lyrics" : "No lyrics selected"}
                                description="Search LRCLIB to find synced or plain lyrics for this track."
                                className="min-h-[20rem]"
                            />
                        ) : candidates.map((candidate) => (
                            <button
                                key={candidate.source_id}
                                type="button"
                                onClick={() => setActiveKey(candidate.source_id)}
                                className={cn(
                                    "flex w-full items-start justify-between gap-3 rounded-2xl px-3 py-2 text-left hover:bg-secondary/45",
                                    active?.source_id === candidate.source_id && "bg-primary/10 text-primary hover:bg-primary/10",
                                )}
                            >
                                <span className="min-w-0">
                                    <span className="block truncate font-semibold">{candidate.title}</span>
                                    <span className="block truncate text-sm text-muted-foreground">
                                        {[candidate.artist, candidate.album].filter(Boolean).join(" - ")}
                                    </span>
                                </span>
                                <span className="shrink-0 rounded-full bg-secondary px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
                                    {lyricsSourceLabel(candidate.source)} · {candidate.synced_lyrics ? "LRC" : "Text"}
                                </span>
                            </button>
                        ))}
                    </div>
                    <aside className="min-h-0 overflow-y-auto p-4">
                        {active ? (
                            <pre className="whitespace-pre-wrap text-sm leading-6 text-foreground/80">
                                {active.synced_lyrics || active.lyrics || "No lyrics text."}
                            </pre>
                        ) : (
                            <p className="text-sm text-muted-foreground">Select a lyrics result to preview it.</p>
                        )}
                    </aside>
                </div>
                <div className="flex justify-end gap-2 border-t border-border px-5 py-3">
                    <Button size="sm" variant="plain" onClick={close}>Cancel</Button>
                    <Button size="sm" loading={applying} disabled={!active} onClick={() => void applyLyrics()}>
                        Save
                    </Button>
                </div>
            </section>
        </div>,
        document.body,
    )
}

function relativeToSource(path: string, sourcePaths: string[]) {
    const normalized = path.replace(/\\/g, "/")
    const roots = sourcePaths
        .map((source) => source.replace(/\\/g, "/").replace(/\/+$/, ""))
        .sort((a, b) => b.length - a.length)
    for (const root of roots) {
        if (normalized === root) return basename(normalized)
        if (normalized.startsWith(`${root}/`)) return normalized.slice(root.length + 1)
    }
    return normalized
}

function lyricsSourceLabel(source: string) {
    if (source === "netease") return "网易云"
    if (source === "qq") return "QQ"
    return "LRCLIB"
}
