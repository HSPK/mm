import { useEffect, useMemo, useState, type ReactNode } from "react"
import { Check, ChevronDown, Heart, Play } from "lucide-react"
import type { VideoLibraryItem } from "@/api/videos"
import { cn } from "@/lib/utils"
import {
    artworkUrlFromItem,
    ratingText,
    runtimeText,
    type ShowGroup,
    videoTitle,
    videoYear,
} from "./video-page-model"
import { VideoNotes } from "./video-notes"
import { VideoPlayer } from "./video-player"
import { readVideoState, useVideoUserState } from "./video-user-state"

export function MovieDetail({
    item,
    onUserStateChange,
}: {
    item: VideoLibraryItem
    onUserStateChange: () => void
}) {
    const playbackId = item.playback_id
    if (!playbackId) return <MissingPlaybackId />
    const { state, setFavorite, setWatched, setNotes, setProgress } = useVideoUserState(playbackId)
    return (
        <DetailShell
            title={videoTitle(item)}
            item={item}
            playbackId={playbackId}
            poster={artworkUrlFromItem(item, 720)}
            favorite={state.favorite}
            watched={state.watched}
            onFavoriteChange={(value) => {
                setFavorite(value)
                onUserStateChange()
            }}
            onWatchedChange={(value) => {
                setWatched(value)
                onUserStateChange()
            }}
            initialTime={state.progress}
            onProgress={setProgress}
        >
            <IntroPanel item={item} />
            <VideoNotes value={state.notes} onChange={setNotes} />
        </DetailShell>
    )
}

export function ShowDetail({
    show,
    onUserStateChange,
}: {
    show: ShowGroup
    onUserStateChange: () => void
}) {
    const initialEpisode = useMemo(() => preferredEpisode(show), [show])
    const [activePath, setActivePath] = useState(initialEpisode?.path ?? "")
    useEffect(() => {
        setActivePath(initialEpisode?.path ?? "")
    }, [initialEpisode?.path, show.key])
    const activeEpisode = show.episodes.find((episode) => episode.path === activePath) ?? initialEpisode
    const nextEpisode = nextEpisodeAfter(show, activeEpisode?.path)
    const playbackId = activeEpisode?.playback_id
    if (!playbackId) return <MissingPlaybackId />
    const { state, setFavorite, setWatched, setNotes, setProgress } = useVideoUserState(playbackId)
    if (!activeEpisode) return null
    return (
        <DetailShell
            title={show.title}
            item={activeEpisode}
            playbackId={playbackId}
            poster={artworkUrlFromItem(show.representative, 720)}
            favorite={state.favorite}
            watched={state.watched}
            onFavoriteChange={(value) => {
                setFavorite(value)
                onUserStateChange()
            }}
            onWatchedChange={(value) => {
                setWatched(value)
                onUserStateChange()
            }}
            initialTime={state.progress}
            onProgress={setProgress}
            onNext={nextEpisode ? () => setActivePath(nextEpisode.path) : undefined}
            side={<EpisodeList show={show} activePath={activeEpisode.path} onSelect={setActivePath} />}
        >
            <IntroPanel item={show.representative} />
            <VideoNotes value={state.notes} onChange={setNotes} />
        </DetailShell>
    )
}

function DetailShell({
    title,
    item,
    playbackId,
    poster,
    favorite,
    watched,
    side,
    onFavoriteChange,
    onWatchedChange,
    initialTime,
    onProgress,
    onNext,
    children,
}: {
    title: string
    item: VideoLibraryItem
    playbackId: string
    poster?: string
    favorite: boolean
    watched: boolean
    side?: ReactNode
    onFavoriteChange: (favorite: boolean) => void
    onWatchedChange: (watched: boolean) => void
    initialTime: number
    onProgress: (time: number, duration: number) => void
    onNext?: () => void
    children: ReactNode
}) {
    return (
        <section className="pt-1">
            <div className="mb-4 min-w-0">
                <h2 className="truncate pl-1 text-2xl font-black tracking-tight sm:pl-2">{title}</h2>
                <DetailMeta item={item} />
            </div>
            <div className={cn("grid gap-6", side && "xl:grid-cols-[minmax(0,1fr)_19rem] xl:items-stretch xl:gap-14")}>
                <div className="min-w-0 xl:aspect-video xl:max-h-[62vh]">
                    <VideoPlayer
                        playbackId={playbackId}
                        poster={poster}
                        initialTime={initialTime}
                        onNext={onNext}
                        onProgress={onProgress}
                    />
                </div>
                {side && (
                    <aside className="min-h-0 overflow-hidden xl:h-full xl:max-h-[62vh] xl:pl-4">
                        {side}
                    </aside>
                )}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
                <StateButton active={favorite} icon={Heart} label="Favorite" onClick={() => onFavoriteChange(!favorite)} />
                <StateButton active={watched} icon={Check} label="Watched" onClick={() => onWatchedChange(!watched)} />
            </div>
            <div className="mt-4">
                {children}
            </div>
        </section>
    )
}

function DetailMeta({ item }: { item: VideoLibraryItem }) {
    const parts = [
        videoYear(item) ? String(videoYear(item)) : "",
        runtimeText(item),
        ratingText(item) ? `★ ${ratingText(item)}` : "",
        item.subtitles ? "Subtitles" : "",
    ].filter(Boolean)
    if (parts.length === 0) return null
    return <p className="mt-1 truncate pl-1 text-sm text-muted-foreground sm:pl-2">{parts.join(" · ")}</p>
}

function EpisodeList({
    show,
    activePath,
    onSelect,
}: {
    show: ShowGroup
    activePath: string
    onSelect: (path: string) => void
}) {
    const [season, setSeason] = useState(show.seasons[0]?.season ?? 0)
    const [menuOpen, setMenuOpen] = useState(false)
    useEffect(() => {
        const activeSeason = show.episodes.find((episode) => episode.path === activePath)?.season ?? show.seasons[0]?.season ?? 0
        setSeason(activeSeason)
    }, [activePath, show])
    const activeSeason = show.seasons.find((item) => item.season === season) ?? show.seasons[0]
    return (
        <div className="flex h-full min-h-0 flex-col rounded-xl border border-border/70 bg-card/45">
            {show.seasons.length > 1 && (
                <div className="relative border-b border-border/70 p-2">
                    <button
                        type="button"
                        onClick={() => setMenuOpen((value) => !value)}
                        className="flex h-9 w-full items-center justify-between rounded-lg bg-secondary/45 px-3 text-sm font-semibold hover:bg-secondary/65"
                        aria-expanded={menuOpen}
                    >
                        <span>{season > 0 ? `Season ${season}` : "Episodes"}</span>
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    </button>
                    {menuOpen && (
                        <div className="absolute inset-x-2 top-12 z-20 overflow-hidden rounded-lg border border-border bg-popover shadow-xl shadow-black/15">
                            {show.seasons.map((item) => (
                                <button
                                    key={item.season}
                                    type="button"
                                    onClick={() => {
                                        setSeason(item.season)
                                        setMenuOpen(false)
                                    }}
                                    className={cn(
                                        "flex h-9 w-full items-center justify-between px-3 text-left text-sm font-semibold hover:bg-secondary/50",
                                        season === item.season && "text-primary",
                                    )}
                                >
                                    <span>{item.season > 0 ? `Season ${item.season}` : "Episodes"}</span>
                                    <span className="text-xs text-muted-foreground">{item.episodes.length}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}
            <div className="video-scrollbar min-h-0 flex-1 overflow-y-auto">
                {activeSeason?.episodes.map((episode) => (
                    <button
                        key={episode.path}
                        type="button"
                        onClick={() => onSelect(episode.path)}
                        className={cn(
                            "flex w-full items-center gap-3 border-b border-border/50 px-3 py-3 text-left text-sm last:border-b-0",
                            episode.path === activePath
                                ? "bg-primary/10 text-primary hover:bg-primary/10"
                                : "hover:bg-secondary/30",
                        )}
                    >
                        <Play className="h-3.5 w-3.5 shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{videoTitle(episode)}</span>
                        {runtimeText(episode) && <span className="shrink-0 text-xs text-muted-foreground">{runtimeText(episode)}</span>}
                    </button>
                ))}
            </div>
        </div>
    )
}

function preferredEpisode(show: ShowGroup) {
    const withProgress = show.episodes
        .map((episode) => ({ episode, state: readVideoState(episode.playback_id) }))
        .filter(({ state }) => state.progress > 30 && (!state.duration || state.progress < state.duration - 60))
        .sort((a, b) => b.state.updatedAt - a.state.updatedAt)
    return withProgress[0]?.episode ?? show.episodes[0]
}

function nextEpisodeAfter(show: ShowGroup, path?: string) {
    if (!path) return null
    const index = show.episodes.findIndex((episode) => episode.path === path)
    return index >= 0 ? show.episodes[index + 1] ?? null : null
}

function MissingPlaybackId() {
    return (
        <section className="rounded-xl bg-destructive/10 px-4 py-3 text-sm font-semibold text-destructive">
            This media item needs to be synced before playback.
        </section>
    )
}

function IntroPanel({ item }: { item: VideoLibraryItem }) {
    return (
        <section className="space-y-3 border-t border-border/70 pt-4">
            <h3 className="text-lg font-bold">Overview</h3>
            {item.metadata_plot ? (
                <p className="text-sm leading-6 text-muted-foreground">{item.metadata_plot}</p>
            ) : (
                <p className="text-sm text-muted-foreground">No introduction yet.</p>
            )}
            {item.metadata_genres && item.metadata_genres.length > 0 && (
                <PillList values={item.metadata_genres.slice(0, 8)} />
            )}
            {item.metadata_cast && item.metadata_cast.length > 0 && (
                <div>
                    <h4 className="mb-2 text-sm font-semibold">Cast</h4>
                    <PillList values={item.metadata_cast.slice(0, 12)} />
                </div>
            )}
        </section>
    )
}

function PillList({ values }: { values: string[] }) {
    return (
        <div className="flex flex-wrap gap-2">
            {values.map((value) => (
                <span key={value} className="rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-muted-foreground">
                    {value}
                </span>
            ))}
        </div>
    )
}

function StateButton({
    active,
    icon: Icon,
    label,
    onClick,
}: {
    active: boolean
    icon: typeof Heart
    label: string
    onClick: () => void
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs font-semibold",
                "h-9 w-9 justify-center p-0",
                active ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground",
            )}
            aria-label={label}
            title={label}
        >
            <Icon className="h-3.5 w-3.5" />
        </button>
    )
}
