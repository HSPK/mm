import type { LucideIcon } from "lucide-react"
import {
    ArrowLeft,
    Disc3,
    Grid2X2,
    List,
    ListMusic,
    Play,
    Plus,
    Search,
    Shuffle,
    Sparkles,
    UserRound,
    X,
} from "lucide-react"
import { type PlayerTrack } from "@/stores/player"
import { AuthImage } from "@/components/auth-image"
import { cn } from "@/lib/utils"
import { InfiniteScrollSentinel } from "./music-infinite-scroll"
import { type AlbumGroup } from "./music-library-model"
import { TrackTable } from "./music-track-table"

export type MusicView = "home" | "albums" | "artists" | "songs" | "album" | "artist"
export type AlbumDisplay = "grid" | "list"

export function ViewTabs({
    view,
    onChange,
}: {
    view: MusicView
    onChange: (view: MusicView) => void
}) {
    const activeView = view === "album" ? "albums" : view === "artist" ? "artists" : view
    const tabs: { value: MusicView, label: string, icon: LucideIcon }[] = [
        { value: "home", label: "Home", icon: Sparkles },
        { value: "albums", label: "Albums", icon: Disc3 },
        { value: "artists", label: "Artists", icon: UserRound },
        { value: "songs", label: "Songs", icon: ListMusic },
    ]
    return (
        <div className="flex gap-1 overflow-x-auto rounded-2xl bg-secondary/55 p-1">
            {tabs.map(({ value, label, icon: Icon }) => (
                <button
                    key={value}
                    type="button"
                    onClick={() => onChange(value)}
                    className={cn(
                        "flex h-10 shrink-0 items-center gap-2 rounded-xl px-3 text-sm font-semibold transition-colors",
                        activeView === value ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
                    )}
                >
                    <Icon className="h-4 w-4" />
                    {label}
                </button>
            ))}
        </div>
    )
}

export function MusicToolbar({
    tracks,
    query,
    onQueryChange,
    onPlayAll,
    onShuffle,
}: {
    tracks: PlayerTrack[]
    query: string
    onQueryChange: (query: string) => void
    onPlayAll: () => void
    onShuffle: () => void
}) {
    return (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            {tracks.length > 0 && (
                <div className="flex gap-2">
                    <PillButton onClick={onPlayAll} primary icon={Play}>Play all</PillButton>
                    <PillButton onClick={onShuffle} icon={Shuffle}>Shuffle</PillButton>
                </div>
            )}
            <div className="min-w-0">
                <div className="relative w-full sm:w-96">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                        type="search"
                        value={query}
                        onChange={(event) => onQueryChange(event.target.value)}
                        placeholder="Search songs, albums, artists"
                        className="h-10 w-full rounded-2xl border border-border bg-card pl-10 pr-10 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/55"
                        aria-label="Search music"
                    />
                    {query && (
                        <button
                            type="button"
                            onClick={() => onQueryChange("")}
                            className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                            aria-label="Clear search"
                        >
                            <X className="h-3.5 w-3.5" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export function HomeView({
    albums,
    tracks,
    albumTotal,
    trackTotal,
    onViewAlbums,
    onViewSongs,
    onOpenAlbum,
    onPlayAlbum,
    onPlayTrack,
    onPlayNextAlbum,
    onPlayNextTrack,
}: {
    albums: AlbumGroup[]
    tracks: PlayerTrack[]
    albumTotal: number
    trackTotal: number
    onViewAlbums: () => void
    onViewSongs: () => void
    onOpenAlbum: (album: AlbumGroup) => void
    onPlayAlbum: (album: AlbumGroup) => void
    onPlayTrack: (track: PlayerTrack) => void
    onPlayNextAlbum: (album: AlbumGroup) => void
    onPlayNextTrack: (track: PlayerTrack) => void
}) {
    return (
        <div className="space-y-7">
            <MusicSectionHeader
                title="Albums"
                count={albumTotal}
                actionLabel={albumTotal > 12 ? "View all" : undefined}
                onAction={onViewAlbums}
            />
            <AlbumGrid
                albums={albums.slice(0, 12)}
                onOpenAlbum={onOpenAlbum}
                onPlayAlbum={onPlayAlbum}
                onPlayNextAlbum={onPlayNextAlbum}
            />
            <MusicSectionHeader
                title="Songs"
                count={trackTotal}
                actionLabel={trackTotal > 12 ? "View all" : undefined}
                onAction={onViewSongs}
            />
            <TrackTable
                tracks={tracks.slice(0, 12)}
                onPlay={onPlayTrack}
                onPlayNext={onPlayNextTrack}
            />
        </div>
    )
}

export function AlbumsView({
    albums,
    total,
    display,
    onDisplayChange,
    onOpenAlbum,
    onPlayAlbum,
    onPlayNextAlbum,
    hasMore,
    onLoadMore,
}: {
    albums: AlbumGroup[]
    total: number
    display: AlbumDisplay
    onDisplayChange: (display: AlbumDisplay) => void
    onOpenAlbum: (album: AlbumGroup) => void
    onPlayAlbum: (album: AlbumGroup) => void
    onPlayNextAlbum: (album: AlbumGroup) => void
    hasMore: boolean
    onLoadMore: () => void
}) {
    return (
        <div className="space-y-4">
            <div className="flex flex-col gap-3 px-1 sm:flex-row sm:items-center sm:justify-between">
                <MusicSectionHeader title="Albums" count={total} />
                <SegmentedControl
                    value={display}
                    options={[
                        { value: "grid", label: "Grid", icon: Grid2X2 },
                        { value: "list", label: "List", icon: List },
                    ]}
                    onChange={onDisplayChange}
                />
            </div>
            {display === "grid" ? (
                <AlbumGrid albums={albums} onOpenAlbum={onOpenAlbum} onPlayAlbum={onPlayAlbum} onPlayNextAlbum={onPlayNextAlbum} />
            ) : (
                <AlbumList albums={albums} onOpenAlbum={onOpenAlbum} onPlayAlbum={onPlayAlbum} onPlayNextAlbum={onPlayNextAlbum} />
            )}
            <InfiniteScrollSentinel key={albums.length} hasMore={hasMore} onLoadMore={onLoadMore} />
        </div>
    )
}

export function AlbumDetail({
    album,
    tracks,
    matchedCount,
    query,
    onBack,
    onPlay,
    onShuffle,
    onPlayNext,
    onPlayTrack,
    onPlayNextTrack,
    hasMore,
    onLoadMore,
}: {
    album: AlbumGroup
    tracks: PlayerTrack[]
    matchedCount: number
    query: string
    onBack: () => void
    onPlay: () => void
    onShuffle: () => void
    onPlayNext: () => void
    onPlayTrack: (track: PlayerTrack) => void
    onPlayNextTrack: (track: PlayerTrack) => void
    hasMore: boolean
    onLoadMore: () => void
}) {
    return (
        <div className="space-y-5">
            <button
                type="button"
                onClick={onBack}
                className="inline-flex h-9 items-center gap-2 rounded-full bg-secondary px-3 text-sm font-semibold text-muted-foreground hover:text-foreground"
            >
                <ArrowLeft className="h-4 w-4" />
                Back to albums
            </button>
            <section className="grid gap-5 rounded-[2rem] bg-card p-5 shadow-sm md:grid-cols-[12rem_minmax(0,1fr)]">
                <AlbumCover album={album} className="aspect-square w-full rounded-[1.5rem] md:w-48" />
                <div className="flex min-w-0 flex-col justify-between gap-5">
                    <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Album</p>
                        <h2 className="mt-2 truncate text-3xl font-black tracking-tight md:text-5xl">{album.title}</h2>
                        <p className="mt-2 truncate text-lg text-muted-foreground">{album.artist}</p>
                        <AlbumMeta year={album.year} matched={query && matchedCount !== album.count ? matchedCount : null} />
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <PillButton onClick={onPlay} primary icon={Play}>Play</PillButton>
                        <PillButton onClick={onShuffle} icon={Shuffle}>Shuffle</PillButton>
                        <PillButton onClick={onPlayNext} icon={Plus}>Play next</PillButton>
                    </div>
                </div>
            </section>
            <TrackTable tracks={tracks} showAlbum={false} onPlay={onPlayTrack} onPlayNext={onPlayNextTrack} />
            <InfiniteScrollSentinel key={tracks.length} hasMore={hasMore} onLoadMore={onLoadMore} />
        </div>
    )
}

function MusicSectionHeader({
    title,
    subtitle,
    count,
    actionLabel,
    onAction,
}: {
    title: string
    subtitle?: string
    count: number
    actionLabel?: string
    onAction?: () => void
}) {
    return (
        <div className="flex flex-1 flex-col gap-2 px-1 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0">
                <div className="flex items-center gap-2">
                    <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
                    <span className="rounded-full bg-secondary/70 px-2 py-0.5 text-xs font-semibold text-muted-foreground">{count.toLocaleString()}</span>
                </div>
                {subtitle && <p className="mt-1 max-w-2xl text-sm leading-5 text-muted-foreground">{subtitle}</p>}
            </div>
            {actionLabel && onAction && (
                <button type="button" onClick={onAction} className="self-start rounded-full bg-secondary px-3 py-1.5 text-sm font-semibold hover:bg-secondary/80 sm:self-auto">
                    {actionLabel}
                </button>
            )}
        </div>
    )
}

function AlbumGrid({
    albums,
    onOpenAlbum,
    onPlayAlbum,
    onPlayNextAlbum,
}: {
    albums: AlbumGroup[]
    onOpenAlbum: (album: AlbumGroup) => void
    onPlayAlbum: (album: AlbumGroup) => void
    onPlayNextAlbum: (album: AlbumGroup) => void
}) {
    return (
        <section className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
            {albums.map((album) => (
                <article key={album.key} className="group min-w-0">
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => onOpenAlbum(album)}
                            className="relative block aspect-square w-full overflow-hidden rounded-[1.35rem] bg-secondary text-left shadow-sm ring-1 ring-border/50 transition duration-300 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-black/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            <AlbumCover album={album} className="h-full w-full" />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
                            <span className="absolute inset-x-0 bottom-0 truncate p-3 text-xs font-semibold text-white/90 opacity-0 transition-opacity group-hover:opacity-100">
                                Open
                            </span>
                        </button>
                        <button
                            type="button"
                            onClick={() => onPlayAlbum(album)}
                            className="absolute bottom-3 right-3 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white text-black opacity-0 shadow-lg transition-opacity hover:scale-105 group-hover:opacity-100"
                            title="Play album"
                        >
                            <Play className="ml-0.5 h-5 w-5" />
                        </button>
                    </div>
                    <div className="mt-3 grid min-w-0 grid-cols-[minmax(0,1fr)_2rem] items-start gap-2 px-1.5">
                        <AlbumCaption album={album} onOpenAlbum={onOpenAlbum} />
                        <IconButton onClick={() => onPlayNextAlbum(album)} label="Play next" icon={Plus} />
                    </div>
                </article>
            ))}
        </section>
    )
}

function AlbumList({
    albums,
    onOpenAlbum,
    onPlayAlbum,
    onPlayNextAlbum,
}: {
    albums: AlbumGroup[]
    onOpenAlbum: (album: AlbumGroup) => void
    onPlayAlbum: (album: AlbumGroup) => void
    onPlayNextAlbum: (album: AlbumGroup) => void
}) {
    return (
        <div className="overflow-hidden rounded-3xl border border-border/45 bg-card">
            {albums.map((album) => (
                <div key={album.key} className="grid grid-cols-[3.5rem_minmax(0,1fr)_auto] items-center gap-3 border-b border-border/45 px-4 py-3 last:border-b-0 hover:bg-secondary/25 md:grid-cols-[3.5rem_minmax(0,1fr)_6rem_auto]">
                    <button type="button" onClick={() => onOpenAlbum(album)} className="overflow-hidden rounded-xl bg-secondary">
                        <AlbumCover album={album} className="h-14 w-14" />
                    </button>
                    <button type="button" onClick={() => onOpenAlbum(album)} className="min-w-0 overflow-hidden text-left">
                        <span className="block truncate font-semibold">{album.title}</span>
                        <span className="block truncate text-sm text-muted-foreground">{album.artist}</span>
                    </button>
                    <span className="hidden md:block">{album.year ? <YearBadge year={album.year} /> : null}</span>
                    <div className="flex items-center gap-1">
                        <IconButton onClick={() => onPlayAlbum(album)} label="Play album" icon={Play} />
                        <IconButton onClick={() => onPlayNextAlbum(album)} label="Play next" icon={Plus} />
                    </div>
                </div>
            ))}
        </div>
    )
}

function AlbumCover({ album, className }: { album: AlbumGroup, className?: string }) {
    if (album.artworkUrl) {
        return (
            <AuthImage
                apiSrc={album.artworkUrl}
                alt=""
                className={cn("object-cover", className)}
                fallback={<AlbumFallback className={className} />}
            />
        )
    }
    return <AlbumFallback className={className} />
}

function AlbumFallback({ className }: { className?: string }) {
    return (
        <div className={cn("flex items-center justify-center bg-gradient-to-br from-secondary to-muted", className)}>
            <Disc3 className="h-12 w-12 text-muted-foreground/35" />
        </div>
    )
}

function AlbumCaption({
    album,
    onOpenAlbum,
}: {
    album: AlbumGroup
    onOpenAlbum: (album: AlbumGroup) => void
}) {
    return (
        <button
            type="button"
            onClick={() => onOpenAlbum(album)}
            className="min-w-0 overflow-hidden rounded-2xl px-1.5 py-0.5 text-left transition-colors hover:bg-secondary/35"
        >
            <h2 className="truncate text-[15px] font-bold leading-5">{album.title}</h2>
            <span className="mt-0.5 grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
                <span className="truncate text-sm leading-5 text-muted-foreground">{album.artist}</span>
                {album.year && <YearBadge year={album.year} />}
            </span>
        </button>
    )
}

function AlbumMeta({ year, matched }: { year?: number | null, matched?: number | null }) {
    const parts = [year ? String(year) : "", matched != null ? `${matched.toLocaleString()} matched` : ""].filter(Boolean)
    if (parts.length === 0) return null
    return <p className="mt-1 text-sm text-muted-foreground">{parts.join(" · ")}</p>
}

function YearBadge({ year, className }: { year: number, className?: string }) {
    return (
        <span className={cn(
            "inline-flex max-w-full shrink-0 rounded-full bg-secondary/70 px-2 py-0.5 text-[11px] font-semibold leading-4 text-muted-foreground tabular-nums",
            className,
        )}>
            {year}
        </span>
    )
}

function IconButton({ onClick, label, icon: Icon }: { onClick: () => void, label: string, icon: LucideIcon }) {
    return (
        <button type="button" onClick={onClick} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground" title={label} aria-label={label}>
            <Icon className="h-3.5 w-3.5" />
        </button>
    )
}

function PillButton({ onClick, icon: Icon, primary, children }: { onClick: () => void, icon: LucideIcon, primary?: boolean, children: string }) {
    return (
        <button type="button" onClick={onClick} className={cn("inline-flex h-10 items-center gap-2 rounded-full px-4 text-sm font-semibold", primary ? "bg-primary text-primary-foreground" : "bg-secondary")}>
            <Icon className="h-4 w-4" />
            {children}
        </button>
    )
}

function SegmentedControl<T extends string>({
    value,
    options,
    onChange,
}: {
    value: T
    options: { value: T, label: string, icon: LucideIcon }[]
    onChange: (value: T) => void
}) {
    return (
        <div className="flex w-max gap-1 rounded-2xl bg-secondary/55 p-1">
            {options.map(({ value: optionValue, label, icon: Icon }) => (
                <button
                    key={optionValue}
                    type="button"
                    onClick={() => onChange(optionValue)}
                    className={cn(
                        "flex h-9 items-center gap-2 rounded-xl px-3 text-sm font-semibold transition-colors",
                        value === optionValue ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
                    )}
                >
                    <Icon className="h-4 w-4" />
                    {label}
                </button>
            ))}
        </div>
    )
}
