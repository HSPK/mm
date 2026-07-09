import type { LucideIcon } from "lucide-react"
import { ArrowLeft, Disc3, Play, Plus, Shuffle, UserRound } from "lucide-react"
import { type PlayerTrack } from "@/stores/player"
import { cn } from "@/lib/utils"
import { InfiniteScrollSentinel } from "./music-infinite-scroll"
import { type AlbumGroup, type ArtistGroup } from "./music-library-model"
import { TrackTable } from "./music-track-table"

export function ArtistGrid({
    artists,
    onOpenArtist,
    onPlay,
    onPlayNext,
}: {
    artists: ArtistGroup[]
    onOpenArtist: (artist: ArtistGroup) => void
    onPlay: (artist: ArtistGroup) => void
    onPlayNext: (artist: ArtistGroup) => void
}) {
    return (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {artists.map((artist) => (
                <div key={artist.name} className="flex items-center gap-3 rounded-3xl bg-card p-4">
                    <button
                        type="button"
                        onClick={() => onOpenArtist(artist)}
                        className="relative h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-secondary"
                    >
                        <ArtistCover artist={artist} />
                    </button>
                    <button type="button" onClick={() => onOpenArtist(artist)} className="min-w-0 flex-1 text-left">
                        <div className="truncate font-bold">{artist.name}</div>
                        <div className="text-sm text-muted-foreground">{artist.albums} album(s) · {artist.tracks.length} song(s)</div>
                    </button>
                    <div className="flex shrink-0 gap-1">
                        <IconButton onClick={() => onPlay(artist)} label="Play artist" icon={Play} />
                        <IconButton onClick={() => onPlayNext(artist)} label="Play next" icon={Plus} />
                    </div>
                </div>
            ))}
        </div>
    )
}

export function ArtistDetail({
    artist,
    albums,
    tracks,
    matchedTrackCount,
    query,
    hasMoreAlbums,
    hasMoreTracks,
    onBack,
    onOpenAlbum,
    onLoadMoreAlbums,
    onLoadMoreTracks,
    onPlay,
    onShuffle,
    onPlayNext,
    onPlayAlbum,
    onPlayNextAlbum,
    onPlayTrack,
    onPlayNextTrack,
}: {
    artist: ArtistGroup
    albums: AlbumGroup[]
    tracks: PlayerTrack[]
    matchedTrackCount: number
    query: string
    hasMoreAlbums: boolean
    hasMoreTracks: boolean
    onBack: () => void
    onOpenAlbum: (album: AlbumGroup) => void
    onLoadMoreAlbums: () => void
    onLoadMoreTracks: () => void
    onPlay: () => void
    onShuffle: () => void
    onPlayNext: () => void
    onPlayAlbum: (album: AlbumGroup) => void
    onPlayNextAlbum: (album: AlbumGroup) => void
    onPlayTrack: (track: PlayerTrack) => void
    onPlayNextTrack: (track: PlayerTrack) => void
}) {
    return (
        <div className="space-y-5">
            <button
                type="button"
                onClick={onBack}
                className="inline-flex h-9 items-center gap-2 rounded-full bg-secondary px-3 text-sm font-semibold text-muted-foreground hover:text-foreground"
            >
                <ArrowLeft className="h-4 w-4" />
                Back to artists
            </button>
            <section className="grid gap-5 rounded-[2rem] bg-card p-5 shadow-sm md:grid-cols-[12rem_minmax(0,1fr)]">
                <div className="aspect-square w-full overflow-hidden rounded-[1.5rem] bg-secondary md:w-48">
                    <ArtistCover artist={artist} large />
                </div>
                <div className="flex min-w-0 flex-col justify-between gap-5">
                    <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Artist</p>
                        <h2 className="mt-2 truncate text-3xl font-black tracking-tight md:text-5xl">{artist.name}</h2>
                        <p className="mt-2 text-sm text-muted-foreground">
                            {artist.albums.toLocaleString()} album(s) · {artist.tracks.length.toLocaleString()} song(s)
                            {query && matchedTrackCount !== artist.tracks.length ? ` · ${matchedTrackCount.toLocaleString()} matched` : ""}
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <PillButton onClick={onPlay} primary icon={Play}>Play</PillButton>
                        <PillButton onClick={onShuffle} icon={Shuffle}>Shuffle</PillButton>
                        <PillButton onClick={onPlayNext} icon={Plus}>Play next</PillButton>
                    </div>
                </div>
            </section>

            {albums.length > 0 && (
                <section className="space-y-3">
                    <SectionTitle title="Albums" />
                    <ArtistAlbumGrid
                        albums={albums}
                        onOpenAlbum={onOpenAlbum}
                        onPlayAlbum={onPlayAlbum}
                        onPlayNextAlbum={onPlayNextAlbum}
                    />
                    <InfiniteScrollSentinel key={albums.length} hasMore={hasMoreAlbums} onLoadMore={onLoadMoreAlbums} />
                </section>
            )}

            <section className="space-y-3">
                <SectionTitle title="Songs" />
                <TrackTable tracks={tracks} onPlay={onPlayTrack} onPlayNext={onPlayNextTrack} />
                <InfiniteScrollSentinel key={tracks.length} hasMore={hasMoreTracks} onLoadMore={onLoadMoreTracks} />
            </section>
        </div>
    )
}

function ArtistAlbumGrid({
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
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
            {albums.map((album) => (
                <article key={album.key} className="group min-w-0 rounded-2xl bg-card">
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => onOpenAlbum(album)}
                            className="relative block aspect-square w-full overflow-hidden rounded-2xl bg-secondary text-left"
                        >
                            <AlbumCover album={album} />
                        </button>
                        <button
                            type="button"
                            onClick={() => onPlayAlbum(album)}
                            className="absolute bottom-2 right-2 flex h-9 w-9 items-center justify-center rounded-full bg-white text-black opacity-0 shadow-lg transition-opacity group-hover:opacity-100"
                            title="Play album"
                        >
                            <Play className="ml-0.5 h-4 w-4" />
                        </button>
                    </div>
                    <div className="mt-2 grid min-w-0 grid-cols-[minmax(0,1fr)_2rem] items-start gap-2 px-1">
                        <button
                            type="button"
                            onClick={() => onOpenAlbum(album)}
                            className="min-w-0 overflow-hidden rounded-xl px-1.5 py-0.5 text-left hover:bg-secondary/35"
                        >
                            <span className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
                                <span className="truncate text-sm font-semibold">{album.title}</span>
                                {album.year && <YearBadge year={album.year} />}
                            </span>
                        </button>
                        <IconButton onClick={() => onPlayNextAlbum(album)} label="Play next" icon={Plus} />
                    </div>
                </article>
            ))}
        </div>
    )
}

function ArtistCover({ artist, large }: { artist: ArtistGroup, large?: boolean }) {
    if (artist.artworkUrl) {
        return <img src={artist.artworkUrl} alt="" loading="lazy" decoding="async" className="h-full w-full object-cover" />
    }
    return (
        <div className="flex h-full w-full items-center justify-center bg-primary/10 text-primary">
            <UserRound className={large ? "h-16 w-16" : "h-7 w-7"} />
        </div>
    )
}

function AlbumCover({ album }: { album: AlbumGroup }) {
    if (album.artworkUrl) {
        return <img src={album.artworkUrl} alt="" loading="lazy" decoding="async" className="h-full w-full object-cover" />
    }
    return (
        <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-secondary to-muted">
            <Disc3 className="h-10 w-10 text-muted-foreground/35" />
        </div>
    )
}

function SectionTitle({ title }: { title: string }) {
    return <h3 className="px-1 text-xl font-bold tracking-tight">{title}</h3>
}

function YearBadge({ year, className }: { year: number, className?: string }) {
    return (
        <span className={cn(
            "inline-flex shrink-0 rounded-full bg-secondary/70 px-2 py-0.5 text-[11px] font-semibold leading-4 text-muted-foreground tabular-nums",
            className,
        )}>
            {year}
        </span>
    )
}

function IconButton({ onClick, label, icon: Icon }: { onClick: () => void, label: string, icon: LucideIcon }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground"
            title={label}
            aria-label={label}
        >
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
