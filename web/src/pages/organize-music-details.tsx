import { useEffect, useState } from "react"
import { Captions, FolderOpen, Music } from "lucide-react"
import { organizerRepo, type OrganizerItem } from "@/api/organizer"
import { Card } from "@/components/ui/card"
import { cn, isLocalMachine } from "@/lib/utils"
import { toast } from "@/stores/toast"
import { type MediaRow, cleanTrackTitle, basename, commonFolder, rowFromFiles } from "./organize-model"
import {
    artworkImageSrc,
    formatBytes,
    musicArtists,
    musicDiscText,
    rowArtworkAssets,
    rowMetadata,
    rowRelatedFiles,
} from "./organize-detail-model"
import { FileIcon, ArtworkRail, DetailBlock, DetailField, IdList } from "./organize-shared-detail"
import { LyricsSearchDialog } from "./organize-lyrics-dialog"

export function MusicDetailsTab({ row, meta }: { row: MediaRow, meta: ReturnType<typeof rowMetadata> }) {
    const artist = musicArtists(row).join(", ")
    const album = row.files[0]?.album || row.title
    const lyricsCount = row.files.filter((file) => file.lyrics).length

    return (
        <div className="grid gap-6 lg:grid-cols-[17rem_1fr]">
            <ArtworkRail row={row} />

            <div className="space-y-5">
                <section className="border-b border-border pb-4">
                    <h2 className="text-3xl font-bold tracking-tight">{album}</h2>
                    {artist && <p className="mt-1 text-lg font-semibold text-muted-foreground">{artist}</p>}
                </section>

                <section className="grid gap-3 border-b border-border pb-5 sm:grid-cols-2 lg:grid-cols-4">
                    <MusicStat label="Year" value={meta.year ?? "-"} />
                    <MusicStat label="Tracks" value={row.files.length} />
                    <MusicStat label="Lyrics" value={`${lyricsCount}/${row.files.length}`} />
                    <MusicStat label="Files" value={row.files.length} />
                </section>

                <section className="grid gap-x-8 gap-y-2 border-b border-border pb-5 md:grid-cols-[9rem_1fr]">
                    <DetailField label="Artist" value={artist} wide />
                    <DetailField label="Album" value={album} wide />
                    <DetailField label="Release date" value={meta.premiered} wide />
                    <DetailField label="Genres" value={meta.genres.join(", ")} wide />
                    <DetailField label="Style" value={meta.styles.join(", ")} wide />
                    <DetailField label="Composer" value={meta.composers.join(", ")} wide />
                    <DetailField label="Tags" value={meta.tags.join(", ")} wide />
                    <IdList ids={meta.ids} />
                </section>

                <section className="space-y-4 border-b border-border py-4">
                    <DetailBlock label="Review" value={meta.plot} />
                </section>

                <MusicLyricsBlock row={row} />

                <section className="space-y-3">
                    <h3 className="text-[15px] font-semibold">Tracks</h3>
                    <div className="overflow-hidden rounded-2xl border border-border">
                        {row.files
                            .slice()
                            .sort((a, b) => (a.track ?? 9999) - (b.track ?? 9999) || a.title.localeCompare(b.title))
                            .map((file) => (
                                <div key={file.path} className="grid grid-cols-[3rem_1fr_5rem] items-center gap-3 border-b border-border/50 px-3 py-2.5 last:border-b-0">
                                    <div className="text-sm tabular-nums text-muted-foreground">{file.track ?? "-"}</div>
                                    <div className="min-w-0">
                                        <div className="truncate text-sm font-semibold">{cleanTrackTitle(file)}</div>
                                        <div className="truncate font-mono text-[11px] text-muted-foreground">{basename(file.path)}</div>
                                    </div>
                                    <div className="text-right text-xs font-semibold text-muted-foreground">
                                        {file.lyrics ? "Lyrics" : ""}
                                    </div>
                                </div>
                            ))}
                    </div>
                </section>
            </div>
        </div>
    )
}

export function MusicDetailsSidebar({
    row,
    sourcePaths,
    defaultLyricsSource,
    onLyricsApplied,
}: {
    row: MediaRow | null
    sourcePaths: string[]
    defaultLyricsSource: string
    onLyricsApplied: () => Promise<void>
}) {
    const [lyricsTarget, setLyricsTarget] = useState<OrganizerItem | null>(null)
    const [tab, setTab] = useState<"details" | "files">("details")
    const [detailResult, setDetailResult] = useState<{
        key: string
        files: OrganizerItem[]
    } | null>(null)
    useEffect(() => {
        let cancelled = false
        if (!row) return undefined
        void organizerRepo.details(row.files)
            .then((items) => {
                if (!cancelled) setDetailResult({ key: row.key, files: items })
            })
            .catch(() => undefined)
        return () => {
            cancelled = true
        }
    }, [row])
    const detailFiles = detailResult && detailResult.key === row?.key
        ? detailResult.files
        : null
    const detailRow = row && detailFiles
        ? rowFromFiles(row.key, row.kind, detailFiles, new Map(), {}, {
            expandable: row.expandable,
            expanded: row.expanded,
        })
        : row
    if (!detailRow) {
        return (
            <Card className="flex h-full min-h-[28rem] items-center justify-center rounded-[1.25rem] p-6 text-center text-sm text-muted-foreground xl:min-h-0">
                Select an album or track to view details.
            </Card>
        )
    }
    const meta = rowMetadata(detailRow)
    const artist = musicArtists(detailRow).join(", ")
    const album = detailRow.files[0]?.album || detailRow.title
    const cover = rowArtworkAssets(detailRow).find((asset) => asset.kind === "poster") ?? rowArtworkAssets(detailRow)[0]
    const itemUids = detailRow.files
        .map((file) => file.item_uid)
        .filter((itemUid): itemUid is string => Boolean(itemUid))
    const revealDirectory = () => {
        void organizerRepo.revealDirectory(itemUids)
            .catch(() => toast.error("Couldn’t open the album folder"))
    }
    return (
        <>
            <Card className="h-full min-h-[28rem] max-h-[calc(100vh-7rem)] overflow-y-auto rounded-[1.25rem] p-4 xl:min-h-0 xl:max-h-none">
                <div className="space-y-5">
                <div className="flex items-center gap-2">
                <div className="flex flex-1 rounded-full bg-secondary/45 p-1">
                    {(["details", "files"] as const).map((item) => (
                        <button
                            key={item}
                            type="button"
                            onClick={() => setTab(item)}
                            className={cn(
                                "h-8 flex-1 rounded-full px-3 text-sm font-semibold capitalize transition-colors",
                                tab === item ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
                            )}
                        >
                            {item}
                        </button>
                    ))}
                </div>
                {isLocalMachine() && itemUids.length > 0 && (
                    <button
                        type="button"
                        onClick={revealDirectory}
                        title="Open album folder"
                        aria-label="Open album folder"
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary/45 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                    >
                        <FolderOpen className="h-4 w-4" />
                    </button>
                )}
                </div>

                {tab === "details" ? (
                    <>
                <div className="mx-auto w-48 overflow-hidden rounded-2xl bg-secondary/60">
                    {cover ? (
                        <img
                            src={artworkImageSrc(cover)}
                            alt=""
                            className="aspect-square w-full object-cover"
                            loading="lazy"
                            decoding="async"
                        />
                    ) : (
                        <div className="flex aspect-square items-center justify-center">
                            <Music className="h-10 w-10 text-muted-foreground/45" />
                        </div>
                    )}
                </div>

                <section className="space-y-1">
                    <h2 className="text-xl font-bold leading-tight">{album}</h2>
                    {artist && <p className="text-sm font-semibold text-muted-foreground">{artist}</p>}
                </section>

                <section className="grid grid-cols-3 gap-2">
                    <MusicStat label="Year" value={meta.year ?? "-"} />
                    <MusicStat label="Tracks" value={detailRow.files.length} />
                </section>

                <section className="space-y-2 text-sm">
                    <CompactDetailField label="Disc" value={musicDiscText(detailRow)} />
                    <CompactDetailField label="Genre" value={meta.genres.join(", ")} />
                    <CompactDetailField label="Style" value={meta.styles.join(", ")} />
                    <CompactDetailField label="Release" value={meta.premiered} />
                </section>

                <section className="space-y-2">
                    <h3 className="text-sm font-bold">Tracks</h3>
                    <div className="divide-y divide-border/50 overflow-hidden rounded-2xl bg-secondary/20">
                        {detailRow.files
                            .slice()
                            .sort((a, b) => (a.track ?? 9999) - (b.track ?? 9999) || a.title.localeCompare(b.title))
                            .map((file) => (
                                <div key={file.path} className="grid grid-cols-[2rem_1fr_auto] items-center gap-2 px-3 py-2">
                                    <span className="text-right text-xs tabular-nums text-muted-foreground">{file.track ?? "-"}</span>
                                    <span className="min-w-0 truncate text-sm font-semibold">{cleanTrackTitle(file)}</span>
                                    <button
                                        type="button"
                                        onClick={() => setLyricsTarget(file)}
                                        className={cn(
                                            "flex h-7 w-7 items-center justify-center rounded-full transition-colors",
                                            file.lyrics
                                                ? "bg-primary/10 text-primary hover:bg-primary/15"
                                                : "bg-secondary text-muted-foreground hover:text-foreground",
                                        )}
                                        title={file.lyrics ? "Update lyrics" : "Get lyrics"}
                                        aria-label={file.lyrics ? `Update lyrics for ${cleanTrackTitle(file)}` : `Get lyrics for ${cleanTrackTitle(file)}`}
                                    >
                                        <Captions className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            ))}
                    </div>
                </section>
                    </>
                ) : (
                    <MusicFilesPanel row={detailRow} />
                )}
            </div>
            </Card>
            <LyricsSearchDialog
                file={lyricsTarget}
                sourcePaths={sourcePaths}
                defaultSource={defaultLyricsSource}
                onClose={() => setLyricsTarget(null)}
                onApplied={async () => {
                    setLyricsTarget(null)
                    await onLyricsApplied()
                }}
            />
        </>
    )
}

function MusicFilesPanel({ row }: { row: MediaRow }) {
    const files = rowRelatedFiles(row)
    return (
        <section className="flex min-h-[calc(100vh-12rem)] flex-col space-y-3">
            <div className="space-y-2 text-sm">
                <CompactDetailField label="Path" value={commonFolder(row.files.map((file) => file.path))} mono />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto rounded-2xl bg-secondary/20">
                {files.map((file) => (
                    <div key={file.path} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-2 border-b border-border/45 px-3 py-2.5 last:border-b-0">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-secondary/60 text-muted-foreground">
                            <FileIcon kind={file.kind} />
                        </div>
                        <div className="min-w-0 break-all text-sm font-semibold leading-5">{file.name}</div>
                        <div className="shrink-0 text-right text-[11px] text-muted-foreground">
                            <div className="capitalize">{file.kind}</div>
                            {file.size != null && <div>{formatBytes(file.size)}</div>}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    )
}

function MusicStat({ label, value }: { label: string, value: string | number }) {
    return (
        <div className="rounded-2xl bg-secondary/35 px-4 py-3">
            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
            <div className="mt-1 text-xl font-bold tabular-nums">{value}</div>
        </div>
    )
}

function CompactDetailField({
    label,
    value,
    mono,
}: {
    label: string
    value?: string | number | null
    mono?: boolean
}) {
    if (!value) return null
    return (
        <div className="grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2">
            <dt className="font-bold text-muted-foreground">{label}</dt>
            <dd className={cn(
                "min-w-0 break-words text-foreground/80",
                mono && "font-mono text-[12px] leading-5 text-primary",
            )}>
                {value}
            </dd>
        </div>
    )
}

function MusicLyricsBlock({ row }: { row: MediaRow }) {
    const lyrics = row.files
        .map((file) => ({
            title: cleanTrackTitle(file),
            text: file.metadata_synced_lyrics || file.metadata_lyrics || "",
        }))
        .filter((item) => item.text.trim())

    if (lyrics.length === 0) return null

    return (
        <section className="space-y-3 border-b border-border py-4">
            <h3 className="font-bold text-muted-foreground">Lyrics</h3>
            <div className="space-y-3">
                {lyrics.map((item) => (
                    <details key={item.title} className="rounded-2xl bg-secondary/30 px-4 py-3" open={lyrics.length === 1}>
                        <summary className="cursor-pointer select-none text-sm font-semibold">{item.title}</summary>
                        <pre className="mt-3 max-h-72 overflow-y-auto whitespace-pre-wrap text-sm leading-6 text-foreground/80">
                            {item.text}
                        </pre>
                    </details>
                ))}
            </div>
        </section>
    )
}
