import type { LucideIcon } from "lucide-react"
import { Music, Plus } from "lucide-react"
import { formatTime } from "@/components/player/music-player-utils"
import { type PlayerTrack, usePlayerStore } from "@/stores/player"
import { cn } from "@/lib/utils"
import { AuthImage } from "@/components/auth-image"

export function TrackTable({
    tracks,
    onPlay,
    onPlayNext,
    showAlbum = true,
    startIndex = 0,
}: {
    tracks: PlayerTrack[]
    onPlay: (track: PlayerTrack) => void
    onPlayNext: (track: PlayerTrack) => void
    showAlbum?: boolean
    startIndex?: number
}) {
    const activeTrackId = usePlayerStore((state) => (
        state.index >= 0 ? state.queue[state.index]?.id ?? null : null
    ))
    return (
        <div className="overflow-hidden rounded-3xl border border-border/45 bg-card">
            {tracks.map((track, index) => (
                <div
                    key={track.id}
                    className={cn(
                        "grid items-center gap-3 border-b border-border/45 px-4 py-2.5 last:border-b-0 hover:bg-secondary/25 sm:gap-4 sm:px-5",
                        showAlbum
                            ? "grid-cols-[2.5rem_2.75rem_minmax(0,1fr)_auto] md:grid-cols-[3rem_2.75rem_minmax(0,1fr)_16rem_4rem_auto]"
                            : "grid-cols-[2.5rem_minmax(0,1fr)_auto] md:grid-cols-[3rem_minmax(0,1fr)_4rem_auto]",
                        activeTrackId === track.id && "bg-primary/10",
                    )}
                >
                    <span className="text-right text-sm tabular-nums text-muted-foreground">
                        {trackNumberLabel(track, startIndex + index)}
                    </span>
                    {showAlbum && <TrackCover track={track} />}
                    <button type="button" onClick={() => onPlay(track)} className="min-w-0 overflow-hidden text-left">
                        <span className="block truncate font-medium">{track.title}</span>
                        <span className="block truncate text-sm text-muted-foreground">{track.artist}</span>
                    </button>
                    {showAlbum && <span className="hidden truncate text-sm text-muted-foreground md:block">{track.album}</span>}
                    <span className="hidden text-right text-xs tabular-nums text-muted-foreground md:block">
                        {track.duration ? formatTime(track.duration) : ""}
                    </span>
                    <TrackIconButton onClick={() => onPlayNext(track)} label="Play next" icon={Plus} />
                </div>
            ))}
        </div>
    )
}

function TrackCover({ track }: { track: PlayerTrack }) {
    return (
        <div className="relative h-11 w-11 overflow-hidden rounded-xl bg-secondary">
            {track.artworkUrl ? (
                <AuthImage
                    apiSrc={track.artworkUrl}
                    alt=""
                    className="h-full w-full object-cover"
                    fallback={<MusicFallback />}
                />
            ) : (
                <MusicFallback />
            )}
        </div>
    )
}

function MusicFallback() {
    return (
        <div className="flex h-full w-full items-center justify-center bg-primary/10 text-primary">
            <Music className="h-5 w-5" />
        </div>
    )
}

function TrackIconButton({
    onClick,
    label,
    icon: Icon,
}: {
    onClick: () => void
    label: string
    icon: LucideIcon
}) {
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

function trackNumberLabel(track: PlayerTrack, index: number) {
    if (!track.trackNumber) return String(index + 1)
    if (track.discNumber && track.discNumber > 1) return `${track.discNumber}-${track.trackNumber}`
    return String(track.trackNumber)
}
