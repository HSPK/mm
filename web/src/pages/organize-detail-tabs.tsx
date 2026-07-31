import { useEffect, useState } from "react"
import type { OrganizerItem } from "@/api/organizer"
import { organizerRepo } from "@/api/organizer"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { RatingSourceBadge } from "./organize-badges"
import {
    artworkAspectRatio,
    artworkImageSrc,
    bitrateText,
    formatBytes,
    formatDuration,
    resolutionText,
    rowArtworkAssets,
    rowMetadata,
    rowRelatedFiles,
} from "./organize-detail-model"
import {
    type MediaRow,
    type MetadataEditValues,
    basename,
    commonFolder,
    parseRating,
    parseRuntime,
    parseYear,
    ratingText,
} from "./organize-model"
import { MusicDetailsTab } from "./organize-music-details"
import { ArtworkRail, DetailBlock, DetailField, FileIcon, IdList } from "./organize-shared-detail"

export function DetailsTab({
    row,
    editing,
    onSaveEdit,
    onCancelEdit,
}: {
    row: MediaRow
    editing: boolean
    onSaveEdit: (row: MediaRow, values: MetadataEditValues) => void
    onCancelEdit: () => void
}) {
    const meta = rowMetadata(row)

    if (editing) return <EditPanel row={row} onSave={onSaveEdit} onCancel={onCancelEdit} />
    if (row.kind === "music") return <MusicDetailsTab row={row} meta={meta} />

    return (
        <div className="grid gap-6 lg:grid-cols-[17rem_1fr]">
            <ArtworkRail row={row} />

            <div className="space-y-5">
                <section className="border-b border-border pb-4">
                    <h2 className="text-3xl font-bold tracking-tight">{meta.title}</h2>
                    {meta.originalTitle && meta.originalTitle !== meta.title && (
                        <p className="mt-1 text-lg font-semibold text-muted-foreground">{meta.originalTitle}</p>
                    )}
                </section>

                <section className="grid gap-x-10 gap-y-2 border-b border-border pb-5 md:grid-cols-2">
                    <DetailField label="Year" value={meta.year} />
                    <IdList ids={meta.ids} />
                    <DetailField label="Premiered" value={meta.premiered} />
                    <DetailField label="Certification" value={meta.certification} />
                    <DetailField label="Runtime" value={meta.runtime ? `${meta.runtime} min` : ""} />
                    <DetailField label="Genres" value={meta.genres.join(", ")} />
                    <DetailField label="Status" value={meta.status} />
                    <DetailField label="Studio" value={meta.studios.join(" / ")} wide />
                    <DetailField label="Country" value={meta.countries.join(", ")} />
                </section>

                <section className="border-b border-border py-4">
                    <div className="flex items-center gap-4">
                        <div className="inline-flex items-center gap-3 rounded-2xl bg-secondary/45 px-4 py-3">
                            <div>
                                <RatingSourceBadge source={meta.ratingSource} />
                            </div>
                            <div className="text-3xl font-bold tabular-nums">{ratingText(meta.rating)}</div>
                        </div>
                    </div>
                </section>

                <section className="space-y-4 border-b border-border py-4">
                    <DetailBlock label="Tagline" value={meta.tagline} />
                    <DetailBlock label="Plot" value={meta.plot} />
                </section>

                <section className="grid gap-x-8 gap-y-2 pt-3 md:grid-cols-[10rem_1fr]">
                    <DetailField label="Cast" value={meta.cast.join(", ")} wide />
                    <DetailField label="Tags" value={meta.tags.join(", ")} wide />
                    <DetailField label="Path" value={commonFolder(row.files.map((file) => file.path))} wide mono />
                    <DetailField label="Note" value="" wide />
                </section>

            </div>
        </div>
    )
}

function EditPanel({
    row,
    onSave,
    onCancel,
}: {
    row: MediaRow
    onSave: (row: MediaRow, values: MetadataEditValues) => void
    onCancel: () => void
}) {
    const meta = rowMetadata(row)
    const [values, setValues] = useState({
        title: meta.title,
        originalTitle: meta.originalTitle,
        year: meta.year ? String(meta.year) : "",
        rating: meta.rating ? String(meta.rating) : "",
        premiered: meta.premiered,
        certification: meta.certification,
        runtime: meta.runtime ? String(meta.runtime) : "",
        genres: meta.genres.join(", "),
        status: meta.status,
        studios: meta.studios.join(", "),
        countries: meta.countries.join(", "),
        tagline: meta.tagline,
        plot: meta.plot,
        tags: meta.tags.join(", "),
        cast: meta.cast.join(", "),
        writeNfo: false,
    })
    const setValue = (key: keyof typeof values, value: string) => {
        setValues((prev) => ({ ...prev, [key]: value }))
    }

    return (
        <div className="space-y-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Edit organizer projection</p>
            <p className="text-sm text-muted-foreground">Changes stay in the organizer projection unless you explicitly write an NFO.</p>
            <div className="grid gap-3 md:grid-cols-2">
                <Input value={values.title} onChange={(event) => setValue("title", event.target.value)} placeholder="Title" />
                <Input value={values.originalTitle} onChange={(event) => setValue("originalTitle", event.target.value)} placeholder="Original title" />
                <Input value={values.year} onChange={(event) => setValue("year", event.target.value)} placeholder="Year" inputMode="numeric" />
                <Input value={values.rating} onChange={(event) => setValue("rating", event.target.value)} placeholder="Rating" inputMode="decimal" />
                <Input value={values.premiered} onChange={(event) => setValue("premiered", event.target.value)} placeholder="Premiered" />
                <Input value={values.certification} onChange={(event) => setValue("certification", event.target.value)} placeholder="Certification" />
                <Input value={values.runtime} onChange={(event) => setValue("runtime", event.target.value)} placeholder="Runtime" inputMode="numeric" />
                <Input value={values.status} onChange={(event) => setValue("status", event.target.value)} placeholder="Status" />
                <Input value={values.genres} onChange={(event) => setValue("genres", event.target.value)} placeholder="Genres" />
                <Input value={values.studios} onChange={(event) => setValue("studios", event.target.value)} placeholder="Studios" />
                <Input value={values.countries} onChange={(event) => setValue("countries", event.target.value)} placeholder="Countries" />
                <Input value={values.cast} onChange={(event) => setValue("cast", event.target.value)} placeholder="Cast" />
                <Input value={values.tags} onChange={(event) => setValue("tags", event.target.value)} placeholder="Tags" wrapperClassName="md:col-span-2" />
                <Input value={values.tagline} onChange={(event) => setValue("tagline", event.target.value)} placeholder="Tagline" wrapperClassName="md:col-span-2" />
                <textarea
                    value={values.plot}
                    onChange={(event) => setValue("plot", event.target.value)}
                    placeholder="Plot"
                    className="min-h-32 rounded-2xl bg-secondary/60 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring md:col-span-2"
                />
            </div>
            <div className="flex gap-2">
                <Button
                    size="sm"
                    onClick={() => onSave(row, {
                        title: values.title.trim() || row.title,
                        originalTitle: values.originalTitle.trim(),
                        year: parseYear(values.year),
                        rating: parseRating(values.rating),
                        premiered: values.premiered.trim(),
                        certification: values.certification.trim(),
                        runtime: parseRuntime(values.runtime),
                        genres: values.genres,
                        status: values.status.trim(),
                        studios: values.studios,
                        countries: values.countries,
                        tagline: values.tagline.trim(),
                        plot: values.plot.trim(),
                        tags: values.tags,
                        cast: values.cast,
                        writeNfo: values.writeNfo,
                    })}
                >
                    Save projection
                </Button>
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                    <input type="checkbox" checked={values.writeNfo} onChange={(event) => setValues((prev) => ({ ...prev, writeNfo: event.target.checked }))} />
                    Write NFO
                </label>
                <Button size="sm" variant="plain" onClick={onCancel}>Cancel</Button>
            </div>
        </div>
    )
}

export function FilesTab({
    row,
}: {
    row: MediaRow
}) {
    const root = commonFolder(row.files.map((file) => file.path))
    const files = rowRelatedFiles(row)
    const primary = row.files[0]
    const [mediaInfo, setMediaInfo] = useState(primary?.media_info ?? null)

    useEffect(() => {
        if (!primary?.playback_id || mediaInfo) return
        let cancelled = false
        void organizerRepo.mediaInfo(primary.playback_id)
            .then((info) => {
                if (!cancelled) setMediaInfo(info)
            })
            .catch(() => undefined)
        return () => {
            cancelled = true
        }
    }, [mediaInfo, primary?.playback_id])

    return (
        <div className="space-y-6">
            <section className="space-y-3">
                <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Root</p>
                    <p className="mt-1 truncate font-mono text-sm text-primary">{root}</p>
                </div>
                <div className="grid gap-x-8 gap-y-3 border-b border-border pb-5 lg:grid-cols-3">
                    <FileFact label="Original file" value={basename(primary?.path ?? "")} mono wide />
                    <FileFact label="Runtime" value={formatDuration(mediaInfo?.duration)} />
                    <FileFact label="Resolution" value={resolutionText(mediaInfo)} />
                    <FileFact label="Video codec" value={mediaInfo?.video_codec} />
                    <FileFact label="Frame rate" value={mediaInfo?.frame_rate ? `${mediaInfo.frame_rate} fps` : ""} />
                    <FileFact label="Video bitrate" value={bitrateText(mediaInfo?.video_bit_rate)} />
                    <FileFact label="HDR format" value={mediaInfo?.hdr_format} />
                    <FileFact label="Video bit depth" value={mediaInfo?.video_bit_depth ? `${mediaInfo.video_bit_depth} bit` : ""} />
                </div>
            </section>

            <StreamTable title="Audio" streams={mediaInfo?.audio_streams ?? []} type="audio" />
            <StreamTable title="Subtitles" streams={mediaInfo?.subtitle_streams ?? []} type="subtitle" />

            <section className="space-y-3">
                <h3 className="text-[15px] font-semibold">Media files</h3>
                <div className="divide-y divide-border/55">
                    {files.map((file) => (
                        <div key={file.path} className="flex items-center gap-3 px-1 py-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary/60 text-muted-foreground">
                                <FileIcon kind={file.kind} />
                            </div>
                            <div className="min-w-0 flex-1">
                                <div className="truncate text-sm font-semibold">{file.name}</div>
                                <div className="truncate font-mono text-[11px] text-muted-foreground">{file.path}</div>
                            </div>
                            <div className="shrink-0 text-right text-xs text-muted-foreground">
                                <div className="capitalize">{file.kind}</div>
                                {file.size != null && <div>{formatBytes(file.size)}</div>}
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    )
}

function StreamTable({
    title,
    streams,
    type,
}: {
    title: string
    streams: NonNullable<OrganizerItem["media_info"]>["audio_streams"] | undefined
    type: "audio" | "subtitle"
}) {
    return (
        <section className="space-y-2">
            <h3 className="text-[15px] font-semibold">{title}</h3>
            {!streams || streams.length === 0 ? (
                <p className="rounded-2xl bg-secondary/35 px-3 py-3 text-sm text-muted-foreground">
                    No {title.toLowerCase()} tracks detected.
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full min-w-[760px] text-left text-sm">
                        <thead className="border-b border-border text-xs text-muted-foreground">
                            <tr>
                                <th className="whitespace-nowrap py-2 pr-3 font-semibold">Source</th>
                                <th className="whitespace-nowrap px-3 py-2 font-semibold">Codec</th>
                                {type === "audio" && <th className="whitespace-nowrap px-3 py-2 font-semibold">Channels</th>}
                                {type === "audio" && <th className="whitespace-nowrap px-3 py-2 font-semibold">Bit rate</th>}
                                {type === "audio" && <th className="whitespace-nowrap px-3 py-2 font-semibold">Bit depth</th>}
                                <th className="whitespace-nowrap px-3 py-2 font-semibold">Language</th>
                                <th className="whitespace-nowrap px-3 py-2 font-semibold">Default</th>
                                <th className="whitespace-nowrap px-3 py-2 font-semibold">Forced</th>
                                {type === "subtitle" && <th className="whitespace-nowrap px-3 py-2 font-semibold">Format</th>}
                                <th className="whitespace-nowrap px-3 py-2 font-semibold">Title</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/50">
                            {streams.map((stream, index) => (
                                <tr key={`${stream.codec}:${stream.language}:${index}`}>
                                    <td className="whitespace-nowrap py-2 pr-3 text-muted-foreground capitalize">{stream.source}</td>
                                    <td className="whitespace-nowrap px-3 py-2">{stream.codec || "-"}</td>
                                    {type === "audio" && <td className="whitespace-nowrap px-3 py-2">{stream.channels || "-"}</td>}
                                    {type === "audio" && <td className="whitespace-nowrap px-3 py-2">{bitrateText(stream.bit_rate)}</td>}
                                    {type === "audio" && <td className="whitespace-nowrap px-3 py-2">{stream.bit_depth ? `${stream.bit_depth} bit` : "-"}</td>}
                                    <td className="whitespace-nowrap px-3 py-2">{stream.language || "-"}</td>
                                    <td className="whitespace-nowrap px-3 py-2">{stream.default ? "✓" : ""}</td>
                                    <td className="whitespace-nowrap px-3 py-2">{stream.forced ? "✓" : ""}</td>
                                    {type === "subtitle" && <td className="whitespace-nowrap px-3 py-2">{stream.format || "-"}</td>}
                                    <td className="whitespace-nowrap px-3 py-2">{stream.title || "-"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    )
}

function FileFact({
    label,
    value,
    mono,
    wide,
}: {
    label: string
    value?: string | number | null
    mono?: boolean
    wide?: boolean
}) {
    if (!value) return null
    return (
        <div className={cn("flex min-w-0 gap-3", wide && "lg:col-span-2")}>
            <dt className="shrink-0 font-bold text-muted-foreground">{label}</dt>
            <dd className={cn("min-w-0 truncate whitespace-nowrap text-foreground/85", mono && "font-mono text-primary")}>
                {value}
            </dd>
        </div>
    )
}

export function ArtworkCanvasTab({ row }: { row: MediaRow }) {
    const assets = row.kind === "music"
        ? rowArtworkAssets(row).filter((asset) => ["poster", "cover", "folder", "image"].includes(asset.kind))
        : rowArtworkAssets(row)
    const canvasItems = assets.length > 0
        ? assets
        : row.candidate?.poster_url
            ? [{ kind: "poster", path: row.candidate.poster_url, label: "poster", width: 2, height: 3 }]
            : []

    return (
        <div className="grid grid-cols-1 items-start gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {canvasItems.length === 0 && (
                <div className="rounded-2xl bg-secondary/35 p-10 text-center text-sm text-muted-foreground">
                    No artwork files detected near this media.
                </div>
            )}
            {canvasItems.map((asset) => (
                <PureArtworkImage key={asset.path} asset={asset} />
            ))}
        </div>
    )
}

function PureArtworkImage({ asset }: { asset: { path: string, playback_id?: string | null, label: string, width?: number | null, height?: number | null } }) {
    const local = !/^https?:\/\//i.test(asset.path)
    return (
        <div className="overflow-hidden" style={{ aspectRatio: artworkAspectRatio(asset) }}>
            <img
                src={local ? artworkImageSrc(asset) : asset.path}
                alt=""
                className="h-full w-full object-cover"
                loading="lazy"
                decoding="async"
            />
        </div>
    )
}
