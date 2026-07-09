import { Captions, FileText, Image, Music } from "lucide-react"
import type { OrganizerItem } from "@/api/organizer"
import { cn } from "@/lib/utils"
import type { MediaRow } from "./organize-model"
import { artworkImageSrc, dimensionsText, rowArtworkAssets } from "./organize-detail-model"

export function ArtworkRail({ row }: { row: MediaRow }) {
    const assets = rowArtworkAssets(row)
    const poster = assets.find((asset) => asset.kind === "poster") ?? assets[0]
    const fanart = assets.find((asset) => asset.kind === "fanart" || asset.kind === "landscape")
    const banner = assets.find((asset) => asset.kind === "banner")
    if (row.kind === "music") {
        return (
            <aside className="space-y-5">
                <ArtworkSlot title="Cover" asset={poster} candidateUrl={row.candidate?.poster_url} ratio="aspect-square" />
            </aside>
        )
    }
    return (
        <aside className="space-y-5">
            <ArtworkSlot title="Poster" asset={poster} candidateUrl={row.candidate?.poster_url} ratio="aspect-[2/3]" />
            <ArtworkSlot title="Fanart" asset={fanart} ratio="aspect-video" />
            <ArtworkSlot title="Banner" asset={banner} ratio="aspect-[5/1]" />
        </aside>
    )
}

export function DetailField({
    label,
    value,
    wide,
    mono,
}: {
    label: string
    value?: string | number | null
    wide?: boolean
    mono?: boolean
}) {
    if (!value) return null
    return (
        <div className={cn("grid grid-cols-[8rem_1fr] gap-3", wide && "md:col-span-2")}>
            <dt className="font-bold text-muted-foreground">{label}</dt>
            <dd className={cn("min-w-0 text-foreground/80", mono && "font-mono text-primary")}>{value}</dd>
        </div>
    )
}

export function DetailBlock({ label, value }: { label: string, value?: string | null }) {
    if (!value) return null
    return (
        <div>
            <h3 className="font-bold text-muted-foreground">{label}</h3>
            <p className="mt-2 max-w-3xl whitespace-pre-wrap leading-6 text-foreground/80">{value}</p>
        </div>
    )
}

export function IdList({ ids }: { ids: Record<string, string> }) {
    const entries = Object.entries(ids)
    if (entries.length === 0) return null
    return (
        <div className="grid grid-cols-[8rem_1fr] gap-3 md:col-span-1">
            <dt className="font-bold text-muted-foreground">IDs</dt>
            <dd className="min-w-0 space-y-1">
                {entries.map(([key, value]) => (
                    <div key={key} className="grid min-w-0 grid-cols-[5.5rem_minmax(0,1fr)] gap-2 text-sm">
                        <span className="font-bold text-foreground/80">{key.toUpperCase()}</span>
                        <span title={value} className="min-w-0 truncate whitespace-nowrap font-mono text-primary">
                            {value}
                        </span>
                    </div>
                ))}
            </dd>
        </div>
    )
}

export function FileIcon({ kind }: { kind: string }) {
    if (kind === "image" || kind === "poster" || kind === "fanart" || kind === "banner") {
        return <Image className="h-4 w-4" />
    }
    if (kind === "subtitle") return <Captions className="h-4 w-4" />
    if (kind === "lyrics") return <Music className="h-4 w-4" />
    return <FileText className="h-4 w-4" />
}

function ArtworkSlot({
    title,
    asset,
    candidateUrl,
    ratio,
}: {
    title: string
    asset?: NonNullable<OrganizerItem["artwork"]>[number]
    candidateUrl?: string
    ratio: string
}) {
    return (
        <div>
            <div className={cn("relative overflow-hidden rounded-sm bg-secondary/60 shadow-lg", ratio)}>
                {asset ? (
                    <img
                        src={artworkImageSrc(asset)}
                        alt=""
                        className="h-full w-full object-cover"
                        loading="lazy"
                        decoding="async"
                    />
                ) : candidateUrl ? (
                    <img src={candidateUrl} alt="" className="h-full w-full object-cover" loading="lazy" />
                ) : (
                    <div className="flex h-full w-full items-center justify-center">
                        <Image className="h-8 w-8 text-muted-foreground/50" />
                    </div>
                )}
            </div>
            <p className="mt-2 text-sm font-semibold text-muted-foreground">
                {asset ? `${title} - ${dimensionsText(asset)}` : title}
            </p>
        </div>
    )
}
