import type { VideoLibraryItem } from "@/api/videos"
import { InfiniteScrollSentinel } from "@/components/ui/infinite-scroll-sentinel"
import { cn } from "@/lib/utils"
import { MovieCard, ShowCard } from "./video-card"
import type { ShowGroup, VideoPageKind } from "./video-page-model"

const VIDEO_GRID_CLASS = "grid grid-cols-4 gap-x-2.5 gap-y-4 sm:grid-cols-5 md:grid-cols-7 xl:grid-cols-9 2xl:grid-cols-10"

export function VideoHome({
    kind,
    movies = [],
    shows = [],
    recentMovies = [],
    recentShows = [],
    selectedPath = "",
    selectedKey = "",
    collectionLabels,
    activeCollection = "All",
    hasMore,
    onSelectMovie,
    onSelectShow,
    onLoadMore,
    onCollection,
}: {
    kind: VideoPageKind
    movies?: VideoLibraryItem[]
    shows?: ShowGroup[]
    recentMovies?: VideoLibraryItem[]
    recentShows?: ShowGroup[]
    selectedPath?: string
    selectedKey?: string
    collectionLabels: string[]
    activeCollection?: string
    hasMore: boolean
    onSelectMovie?: (item: VideoLibraryItem) => void
    onSelectShow?: (show: ShowGroup) => void
    onLoadMore: () => void
    onCollection: (name: string) => void
}) {
    const isTv = kind === "tv"
    return (
        <div className="space-y-8">
            {isTv ? (
                <>
                    <ShowSection title="Recently Added" shows={recentShows} selectedKey={selectedKey} onSelect={onSelectShow} />
                    <CollectionsSection labels={collectionLabels} active={activeCollection} onSelect={onCollection} />
                    <ShowGrid shows={shows} selectedKey={selectedKey} onSelect={onSelectShow!} hasMore={hasMore} onLoadMore={onLoadMore} />
                </>
            ) : (
                <>
                    <MovieSection title="Recently Added" movies={recentMovies} selectedPath={selectedPath} onSelect={onSelectMovie} />
                    <CollectionsSection labels={collectionLabels} active={activeCollection} onSelect={onCollection} />
                    <MovieGrid movies={movies} selectedPath={selectedPath} onSelect={onSelectMovie!} hasMore={hasMore} onLoadMore={onLoadMore} />
                </>
            )}
        </div>
    )
}

function MovieSection({
    title,
    movies,
    selectedPath,
    onSelect,
}: {
    title: string
    movies: VideoLibraryItem[]
    selectedPath: string
    onSelect?: (item: VideoLibraryItem) => void
}) {
    if (movies.length === 0 || !onSelect) return null
    return (
        <section className="space-y-3">
            <SectionTitle title={title} count={movies.length} />
            <div className={VIDEO_GRID_CLASS}>
                {movies.map((item) => (
                    <MovieCard key={item.path} item={item} selected={item.path === selectedPath} onClick={() => onSelect(item)} />
                ))}
            </div>
        </section>
    )
}

function ShowSection({
    title,
    shows,
    selectedKey,
    onSelect,
}: {
    title: string
    shows: ShowGroup[]
    selectedKey: string
    onSelect?: (show: ShowGroup) => void
}) {
    if (shows.length === 0 || !onSelect) return null
    return (
        <section className="space-y-3">
            <SectionTitle title={title} count={shows.length} />
            <div className={VIDEO_GRID_CLASS}>
                {shows.map((show) => (
                    <ShowCard key={show.key} show={show} selected={show.key === selectedKey} onClick={() => onSelect(show)} />
                ))}
            </div>
        </section>
    )
}

function MovieGrid({
    movies,
    selectedPath,
    hasMore,
    onSelect,
    onLoadMore,
}: {
    movies: VideoLibraryItem[]
    selectedPath: string
    hasMore: boolean
    onSelect: (item: VideoLibraryItem) => void
    onLoadMore: () => void
}) {
    return (
        <section className="space-y-5">
            <div className={VIDEO_GRID_CLASS}>
                {movies.map((item) => (
                    <MovieCard key={item.path} item={item} selected={item.path === selectedPath} onClick={() => onSelect(item)} />
                ))}
            </div>
            <InfiniteScrollSentinel key={movies.length} hasMore={hasMore} onLoadMore={onLoadMore} />
        </section>
    )
}

function ShowGrid({
    shows,
    selectedKey,
    hasMore,
    onSelect,
    onLoadMore,
}: {
    shows: ShowGroup[]
    selectedKey: string
    hasMore: boolean
    onSelect: (show: ShowGroup) => void
    onLoadMore: () => void
}) {
    return (
        <section className="space-y-5">
            <div className={VIDEO_GRID_CLASS}>
                {shows.map((show) => (
                    <ShowCard key={show.key} show={show} selected={show.key === selectedKey} onClick={() => onSelect(show)} />
                ))}
            </div>
            <InfiniteScrollSentinel key={shows.length} hasMore={hasMore} onLoadMore={onLoadMore} />
        </section>
    )
}

function CollectionsSection({
    labels,
    active,
    onSelect,
}: {
    labels: string[]
    active: string
    onSelect: (name: string) => void
}) {
    return (
        <section className="space-y-3">
            <SectionTitle title="Collections" />
            <div className="flex flex-wrap gap-2">
                {["All", "Favorites", ...labels].map((label) => (
                    <button
                        key={label}
                        type="button"
                        onClick={() => onSelect(label)}
                        className={cn(
                            "rounded-full px-3 py-2 text-sm font-semibold transition-colors",
                            active === label
                                ? "bg-primary text-primary-foreground"
                                : "bg-secondary text-muted-foreground hover:text-foreground",
                        )}
                    >
                        {label}
                    </button>
                ))}
            </div>
        </section>
    )
}

function SectionTitle({ title, count }: { title: string; count?: number }) {
    return (
        <div className="flex items-baseline gap-2 px-1">
            <h2 className="text-xl font-black tracking-tight">{title}</h2>
            {count != null && <span className="text-xs font-semibold text-muted-foreground">{count}</span>}
        </div>
    )
}
