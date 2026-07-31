import { useEffect, useState, type ReactNode } from "react"
import { ArrowLeft, ChevronDown, FolderOpen, Heart, ImageOff, Star } from "lucide-react"
import { videoRepo, type VideoLibraryItem } from "@/api/videos"
import { playerRepo, type VideoMediaInfo } from "@/api/player"
import { cn, isLocalMachine } from "@/lib/utils"
import { toast } from "@/stores/toast"
import {
    artworkUrlFromItem,
    backdropUrlFromItem,
    logoUrlFromItem,
    ratingText,
    runtimeText,
    type ShowGroup,
    videoTitle,
    videoYear,
} from "./video-page-model"
import { MediaInfoChips } from "./media-info"
import { useVideoUserState } from "./video-user-state"

export function MovieDetail({
    item,
    onBack,
    onUserStateChange,
}: {
    item: VideoLibraryItem
    onBack: () => void
    onUserStateChange: () => void
}) {
    if (!item.playback_id) return <MissingPlaybackId onBack={onBack} />
    return (
        <MovieDetailReady
            item={item}
            playbackId={item.playback_id}
            onBack={onBack}
            onUserStateChange={onUserStateChange}
        />
    )
}

function MovieDetailReady({
    item,
    playbackId,
    onBack,
    onUserStateChange,
}: {
    item: VideoLibraryItem
    playbackId: string
    onBack: () => void
    onUserStateChange: () => void
}) {
    const { state, setFavorite } = useVideoUserState(playbackId)
    return (
        <CinemaDetail
            heroItem={item}
            playbackId={playbackId}
            title={videoTitle(item)}
            poster={artworkUrlFromItem(item, 720)}
            favorite={state.favorite}
            onFavoriteChange={(value) => {
                setFavorite(value)
                onUserStateChange()
            }}
            onBack={onBack}
        />
    )
}

export function ShowDetail({
    show,
    onBack,
    onUserStateChange,
}: {
    show: ShowGroup
    onBack: () => void
    onUserStateChange: () => void
}) {
    const bookmarkId = show.representative.playback_id
    if (!bookmarkId) return <MissingPlaybackId onBack={onBack} />
    return (
        <ShowDetailReady
            show={show}
            playbackId={bookmarkId}
            onBack={onBack}
            onUserStateChange={onUserStateChange}
        />
    )
}

function ShowDetailReady({
    show,
    playbackId,
    onBack,
    onUserStateChange,
}: {
    show: ShowGroup
    playbackId: string
    onBack: () => void
    onUserStateChange: () => void
}) {
    const { state, setFavorite } = useVideoUserState(playbackId)
    return (
        <CinemaDetail
            heroItem={show.representative}
            playbackId={playbackId}
            title={show.title}
            poster={artworkUrlFromItem(show.representative, 720)}
            favorite={state.favorite}
            onFavoriteChange={(value) => {
                setFavorite(value)
                onUserStateChange()
            }}
            onBack={onBack}
            episodes={<EpisodeList show={show} />}
        />
    )
}

interface CinemaDetailProps {
    heroItem: VideoLibraryItem
    playbackId: string
    title: string
    poster?: string
    favorite: boolean
    onFavoriteChange: (favorite: boolean) => void
    onBack: () => void
    episodes?: ReactNode
}

function CinemaDetail({
    heroItem,
    playbackId,
    title,
    poster,
    favorite,
    onFavoriteChange,
    onBack,
    episodes,
}: CinemaDetailProps) {
    const [mediaInfo, setMediaInfo] = useState<VideoMediaInfo | null>(null)
    const canReveal = isLocalMachine()

    useEffect(() => {
        let cancelled = false
        setMediaInfo(null)
        void playerRepo.videoSource(playbackId)
            .then((source) => {
                if (!cancelled) setMediaInfo(source.media_info ?? null)
            })
            .catch(() => undefined)
        return () => {
            cancelled = true
        }
    }, [playbackId])

    const revealInFileManager = () => {
        void videoRepo.reveal(playbackId).catch(() => toast.error("Couldn’t open the file manager"))
    }

    return (
        <div className="pb-16">
            <div className="relative bg-black">
                <div className="relative aspect-video max-h-[74vh] w-full overflow-hidden">
                    <HeroPromo
                        heroItem={heroItem}
                        title={title}
                        poster={poster}
                        mediaInfo={mediaInfo}
                        favorite={favorite}
                        onFavoriteChange={onFavoriteChange}
                        onReveal={canReveal ? revealInFileManager : undefined}
                    />
                </div>
                <button
                    type="button"
                    onClick={onBack}
                    aria-label="Back"
                    className="absolute left-3 top-3 z-40 flex h-10 w-10 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-md transition hover:bg-black/60 sm:left-5 sm:top-5"
                >
                    <ArrowLeft className="h-5 w-5" />
                </button>
            </div>
            <DetailBody heroItem={heroItem} mediaInfo={mediaInfo} episodes={episodes} />
        </div>
    )
}

function HeroPromo({
    heroItem,
    title,
    poster,
    mediaInfo,
    favorite,
    onFavoriteChange,
    onReveal,
}: {
    heroItem: VideoLibraryItem
    title: string
    poster?: string
    mediaInfo: VideoMediaInfo | null
    favorite: boolean
    onFavoriteChange: (favorite: boolean) => void
    onReveal?: () => void
}) {
    const [logoOk, setLogoOk] = useState(true)
    const logo = logoUrlFromItem(heroItem)

    return (
        <div className="absolute inset-0">
            <BackdropImage backdrop={backdropUrlFromItem(heroItem)} poster={poster} />
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/45 to-black/5" />
            <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/25 to-transparent" />
            <div className="absolute inset-x-0 bottom-0 flex flex-col gap-4 p-6 sm:p-10 md:max-w-3xl">
                {logo && logoOk ? (
                    <img
                        src={logo}
                        alt={title}
                        onError={() => setLogoOk(false)}
                        className="max-h-24 w-auto max-w-[min(85%,24rem)] object-contain object-left drop-shadow-2xl sm:max-h-28"
                    />
                ) : (
                    <h1 className="text-3xl font-black leading-tight text-white drop-shadow-lg sm:text-5xl">{title}</h1>
                )}
                <HeroMeta item={heroItem} mediaInfo={mediaInfo} />
                {heroItem.metadata_plot && (
                    <p className="line-clamp-3 max-w-2xl text-sm leading-relaxed text-white/85 sm:text-[15px]">
                        {heroItem.metadata_plot}
                    </p>
                )}
                <div className="flex flex-wrap items-center gap-2.5 pt-1">
                    <button
                        type="button"
                        onClick={() => onFavoriteChange(!favorite)}
                        aria-pressed={favorite}
                        className={cn(
                            "inline-flex h-11 items-center gap-2 rounded-full border px-5 text-sm font-bold backdrop-blur-md transition",
                            favorite
                                ? "border-white bg-white/90 text-black"
                                : "border-white/30 bg-white/10 text-white hover:bg-white/20",
                        )}
                    >
                        <Heart className={cn("h-[18px] w-[18px]", favorite && "fill-current")} />
                        {favorite ? "Favorited" : "Favorite"}
                    </button>
                    {onReveal && (
                        <button
                            type="button"
                            onClick={onReveal}
                            aria-label="Show in file manager"
                            title="Show in file manager"
                            className="inline-flex h-11 items-center gap-2 rounded-full border border-white/30 bg-white/10 px-5 text-sm font-bold text-white backdrop-blur-md transition hover:bg-white/20"
                        >
                            <FolderOpen className="h-[18px] w-[18px]" />
                            Open
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

function HeroMeta({ item, mediaInfo }: { item: VideoLibraryItem; mediaInfo: VideoMediaInfo | null }) {
    const year = videoYear(item)
    const rating = ratingText(item)
    const runtime = runtimeText(item)
    return (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm font-medium text-white/90">
            {rating && (
                <span className="inline-flex items-center gap-1 font-bold text-amber-400">
                    <Star className="h-4 w-4 fill-amber-400" />
                    {rating}
                </span>
            )}
            {year ? <span>{year}</span> : null}
            {runtime && <span>{runtime}</span>}
            {item.metadata_certification && (
                <span className="rounded border border-white/40 px-1.5 text-xs font-semibold">{item.metadata_certification}</span>
            )}
            {item.subtitles && <span className="rounded border border-white/40 px-1.5 text-xs font-semibold">CC</span>}
            {mediaInfo && <MediaInfoChips info={mediaInfo} />}
        </div>
    )
}

function BackdropImage({ backdrop, poster }: { backdrop?: string; poster?: string }) {
    const [useBackdrop, setUseBackdrop] = useState(Boolean(backdrop))
    useEffect(() => {
        setUseBackdrop(Boolean(backdrop))
    }, [backdrop])
    const src = useBackdrop ? backdrop : poster
    if (!src) return <div className="absolute inset-0 bg-neutral-900" />
    return (
        <>
            {!useBackdrop && poster && (
                <div
                    className="absolute inset-0 scale-125 bg-cover bg-center blur-2xl"
                    style={{ backgroundImage: `url(${poster})` }}
                />
            )}
            <img
                src={src}
                alt=""
                onError={() => setUseBackdrop(false)}
                className={cn("absolute inset-0 h-full w-full", useBackdrop ? "object-cover" : "object-contain")}
            />
        </>
    )
}

function DetailBody({
    heroItem,
    mediaInfo,
    episodes,
}: {
    heroItem: VideoLibraryItem
    mediaInfo: VideoMediaInfo | null
    episodes?: ReactNode
}) {
    const cast = heroItem.metadata_cast ?? []
    const genres = heroItem.metadata_genres ?? []
    return (
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
            {episodes && <div className="mb-10">{episodes}</div>}
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
                <div className="min-w-0 space-y-7">
                    {heroItem.metadata_tagline && (
                        <p className="text-lg font-medium italic text-muted-foreground">“{heroItem.metadata_tagline}”</p>
                    )}
                    {genres.length > 0 && <PillRow values={genres.slice(0, 10)} />}
                    {heroItem.metadata_plot && (
                        <Section title="Overview">
                            <p className="text-[15px] leading-7 text-foreground/90">{heroItem.metadata_plot}</p>
                        </Section>
                    )}
                    {cast.length > 0 && (
                        <Section title="Cast">
                            <CastGrid names={cast.slice(0, 18)} />
                        </Section>
                    )}
                </div>
                <aside className="lg:sticky lg:top-6 lg:self-start">
                    <InfoTable item={heroItem} mediaInfo={mediaInfo} />
                </aside>
            </div>
        </div>
    )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">{title}</h3>
            {children}
        </section>
    )
}

function CastGrid({ names }: { names: string[] }) {
    return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
            {names.map((name) => (
                <div key={name} className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-bold text-muted-foreground">
                        {initials(name)}
                    </div>
                    <span className="min-w-0 truncate text-sm font-medium">{name}</span>
                </div>
            ))}
        </div>
    )
}

function InfoTable({ item, mediaInfo }: { item: VideoLibraryItem; mediaInfo: VideoMediaInfo | null }) {
    const rows: Array<[string, ReactNode]> = []
    if (mediaInfo?.width && mediaInfo?.height) rows.push(["Resolution", `${mediaInfo.width}×${mediaInfo.height}`])
    if (mediaInfo?.video_codec) rows.push(["Video", mediaInfo.video_codec.toUpperCase()])
    if (mediaInfo?.hdr) rows.push(["Dynamic range", mediaInfo.hdr])
    if (mediaInfo?.audio_codec) rows.push(["Audio", mediaInfo.audio_codec.toUpperCase()])
    if (mediaInfo?.frame_rate) rows.push(["Frame rate", `${Math.round(mediaInfo.frame_rate)} fps`])
    if (item.metadata_status) rows.push(["Status", item.metadata_status])
    if (item.metadata_premiered) rows.push(["Premiered", item.metadata_premiered])
    if (item.metadata_studios?.length) rows.push(["Studio", item.metadata_studios.slice(0, 3).join(", ")])
    if (item.metadata_countries?.length) rows.push(["Country", item.metadata_countries.slice(0, 3).join(", ")])
    if (item.metadata_certification) rows.push(["Rated", item.metadata_certification])
    if (item.metadata_rating != null) {
        rows.push(["Rating", `${ratingText(item)}${item.metadata_rating_source ? ` · ${item.metadata_rating_source}` : ""}`])
    }
    if (rows.length === 0) return null
    return (
        <div className="rounded-2xl border border-border/60 bg-card/40 p-5">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">Details</h3>
            <dl className="space-y-2.5">
                {rows.map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-4 text-sm">
                        <dt className="shrink-0 text-muted-foreground">{key}</dt>
                        <dd className="min-w-0 text-right font-medium">{value}</dd>
                    </div>
                ))}
            </dl>
        </div>
    )
}

function PillRow({ values }: { values: string[] }) {
    return (
        <div className="flex flex-wrap gap-2">
            {values.map((value) => (
                <span
                    key={value}
                    className="rounded-full border border-border/70 bg-secondary/60 px-3 py-1 text-xs font-semibold text-foreground/80"
                >
                    {value}
                </span>
            ))}
        </div>
    )
}

function EpisodeList({ show }: { show: ShowGroup }) {
    const [season, setSeason] = useState(show.seasons[0]?.season ?? 0)
    const [menuOpen, setMenuOpen] = useState(false)
    const activeSeason = show.seasons.find((item) => item.season === season) ?? show.seasons[0]
    return (
        <section className="space-y-3">
            <div className="flex items-center justify-between gap-4">
                <h3 className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">Episodes</h3>
                {show.seasons.length > 1 && (
                    <div className="relative">
                        <button
                            type="button"
                            onClick={() => setMenuOpen((value) => !value)}
                            className="flex h-9 items-center gap-1.5 rounded-full bg-secondary px-4 text-sm font-semibold hover:bg-secondary/80"
                            aria-expanded={menuOpen}
                        >
                            {season > 0 ? `Season ${season}` : "Episodes"}
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        </button>
                        {menuOpen && (
                            <div className="absolute right-0 top-11 z-20 min-w-40 overflow-hidden rounded-xl border border-border bg-popover shadow-xl shadow-black/15">
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
            </div>
            <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                {activeSeason?.episodes.map((episode) => (
                    <div
                        key={episode.playback_id ?? episode.path}
                        className="flex items-center gap-3 overflow-hidden rounded-xl border border-border/60 bg-card/40 p-2.5"
                    >
                        <div className="aspect-video w-24 shrink-0 overflow-hidden rounded-lg bg-secondary">
                            <EpisodeThumb episode={episode} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold">{videoTitle(episode)}</p>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                                {[episodeCode(episode), runtimeText(episode)].filter(Boolean).join(" · ")}
                            </p>
                        </div>
                    </div>
                ))}
            </div>
        </section>
    )
}

function EpisodeThumb({ episode }: { episode: VideoLibraryItem }) {
    const [ok, setOk] = useState(true)
    const src = artworkUrlFromItem(episode, 320)
    if (!src || !ok) {
        return <div className="flex h-full w-full items-center justify-center text-muted-foreground"><ImageOff className="h-4 w-4 opacity-40" /></div>
    }
    return <img src={src} alt="" onError={() => setOk(false)} className="h-full w-full object-cover" />
}

function episodeCode(item: VideoLibraryItem) {
    const season = item.season != null ? `S${String(item.season).padStart(2, "0")}` : ""
    const episode = item.episode != null ? `E${String(item.episode).padStart(2, "0")}` : ""
    return `${season}${episode}`
}

function initials(name: string) {
    const parts = name.trim().split(/\s+/).slice(0, 2)
    return parts.map((part) => part[0]?.toUpperCase() ?? "").join("") || "?"
}

function MissingPlaybackId({ onBack }: { onBack: () => void }) {
    return (
        <section className="mx-auto max-w-lg px-4 py-16 text-center">
            <p className="text-sm font-semibold text-destructive">This media item needs to be synced first.</p>
            <button
                type="button"
                onClick={onBack}
                className="mt-4 inline-flex h-9 items-center rounded-full bg-secondary px-4 text-sm font-semibold hover:bg-secondary/80"
            >
                Back to list
            </button>
        </section>
    )
}
