import { useEffect, useState } from "react"
import { Captions, Film, Star, Tv } from "lucide-react"
import type { VideoLibraryItem } from "@/api/videos"
import { cn } from "@/lib/utils"
import {
    artworkUrlFromItem,
    itemSubtitle,
    ratingText,
    type ShowGroup,
    videoTitle,
    videoYear,
} from "./video-page-model"

export function MovieCard({
    item,
    selected,
    onClick,
}: {
    item: VideoLibraryItem
    selected: boolean
    onClick: () => void
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "group min-w-0 rounded-[1.5rem] p-1 text-left transition-colors hover:bg-secondary/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selected && "bg-primary/10",
            )}
        >
            <Poster artworkUrl={artworkUrlFromItem(item)} fallback="movie" />
            <div className="mt-2 min-w-0 px-1">
                <h3 className="truncate text-sm font-bold">{videoTitle(item)}</h3>
                <div className="mt-0.5 flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
                    {videoYear(item) && <span className="shrink-0 tabular-nums">{videoYear(item)}</span>}
                    {ratingText(item) && <Badge icon={Star} label={ratingText(item)} />}
                    {item.subtitles && <Badge icon={Captions} label="Sub" />}
                </div>
            </div>
        </button>
    )
}

export function ShowCard({
    show,
    selected,
    onClick,
}: {
    show: ShowGroup
    selected: boolean
    onClick: () => void
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "group min-w-0 rounded-[1.5rem] p-1 text-left transition-colors hover:bg-secondary/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selected && "bg-primary/10",
            )}
        >
            <Poster artworkUrl={artworkUrlFromItem(show.representative)} fallback="tv" />
            <div className="mt-2 min-w-0 px-1">
                <h3 className="truncate text-sm font-bold">{show.title}</h3>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {[show.year, `${show.episodes.length} episodes`].filter(Boolean).join(" · ")}
                </p>
            </div>
        </button>
    )
}

export function MetadataBadges({ item }: { item: VideoLibraryItem }) {
    const rating = ratingText(item)
    return (
        <div className="flex flex-wrap gap-2">
            {itemSubtitle(item) && <span className="rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-muted-foreground">{itemSubtitle(item)}</span>}
            {rating && <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-muted-foreground"><Star className="h-3.5 w-3.5 text-amber-500" /> {rating}</span>}
            {item.subtitles && <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-muted-foreground"><Captions className="h-3.5 w-3.5" /> Subtitles</span>}
        </div>
    )
}

function Poster({ artworkUrl, fallback }: { artworkUrl?: string, fallback: "movie" | "tv" }) {
    const Icon = fallback === "movie" ? Film : Tv
    const [usableArtwork, setUsableArtwork] = useState(Boolean(artworkUrl))
    useEffect(() => {
        setUsableArtwork(Boolean(artworkUrl))
    }, [artworkUrl])
    return (
        <div className="relative aspect-[2/3] overflow-hidden rounded-[1.25rem] bg-secondary shadow-lg shadow-black/10">
            <div className="absolute inset-0 flex h-full w-full items-center justify-center bg-gradient-to-br from-secondary to-muted">
                <Icon className="h-10 w-10 text-muted-foreground/35" />
            </div>
            {artworkUrl && usableArtwork && (
                <img
                    src={artworkUrl}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    draggable={false}
                    onError={() => setUsableArtwork(false)}
                    className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                />
            )}
        </div>
    )
}

function Badge({ icon: Icon, label }: { icon: typeof Star, label: string }) {
    return (
        <span className="inline-flex min-w-0 items-center gap-1 rounded-full bg-secondary/70 px-1.5 py-0.5">
            <Icon className="h-3 w-3 shrink-0" />
            <span className="truncate">{label}</span>
        </span>
    )
}
