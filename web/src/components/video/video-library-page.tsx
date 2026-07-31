import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react"
import { Film, RefreshCw, Search, Tv } from "lucide-react"
import { useLocation } from "react-router-dom"
import { videoRepo, type VideoLibraryItem } from "@/api/videos"
import { useHeaderRegistration } from "@/components/navigation/header-context"
import { EmptyState } from "@/components/ui/empty-state"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"
import { MovieDetail, ShowDetail } from "./video-detail"
import { VideoHome } from "./video-home"
import { useVideoSelection } from "./use-video-selection"
import {
    collectionNames,
    filterCollectionMovies,
    filterCollectionShows,
    recentItems,
    recentShowsList,
} from "./video-home-model"
import {
    filterShows,
    filterVideoItems,
    groupShows,
    type VideoPageKind,
} from "./video-page-model"
import { loadVideoStates } from "./video-user-state"

const PAGE_SIZE = 96

export function VideoLibraryPage({ kind }: { kind: VideoPageKind }) {
    const [items, setItems] = useState<VideoLibraryItem[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [query, setQuery] = useState("")
    const [limit, setLimit] = useState(PAGE_SIZE)
    const { selectedKey, select, clear } = useVideoSelection()
    const [activeCollection, setActiveCollection] = useState("All")
    const [userStateVersion, setUserStateVersion] = useState(0)
    const location = useLocation()
    const registerHeader = useHeaderRegistration()
    const rootRef = useRef<HTMLDivElement>(null)
    const deferredQuery = useDeferredValue(query)
    const isTv = kind === "tv"
    const title = isTv ? "TV Shows" : "Movies"
    const Icon = isTv ? Tv : Film

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const [videoItems] = await Promise.all([
                videoRepo.items(kind),
                loadVideoStates(),
            ])
            setItems(videoItems)
            setUserStateVersion((value) => value + 1)
        } catch (err) {
            setError(err instanceof Error ? err.message : `Could not load ${title.toLowerCase()}`)
        } finally {
            setLoading(false)
        }
    }, [kind, title])

    useEffect(() => {
        const id = window.setTimeout(() => { void load() }, 0)
        return () => window.clearTimeout(id)
    }, [load])

    useEffect(() => {
        setLimit(PAGE_SIZE)
    }, [activeCollection, deferredQuery, kind])

    useEffect(() => {
        const ids = items.map((item) => item.playback_id).filter((id): id is string => Boolean(id)).slice(0, 120)
        if (ids.length > 0) void videoRepo.artworkBatch(ids, 420).catch(() => undefined)
    }, [items])

    const playableItems = useMemo(
        () => items.filter((item) => item.playback_id),
        [items],
    )
    const searchedMovies = useMemo(
        () => filterVideoItems(playableItems, deferredQuery),
        [deferredQuery, playableItems],
    )
    const searchedShows = useMemo(
        () => filterShows(groupShows(playableItems), deferredQuery),
        [deferredQuery, playableItems],
    )
    const collectionLabels = useMemo(
        () => collectionNames(isTv ? searchedShows.flatMap((show) => show.episodes) : searchedMovies),
        [isTv, searchedMovies, searchedShows],
    )
    const collectionOptions = useMemo(
        () => ["All", "Favorites", ...collectionLabels],
        [collectionLabels],
    )
    const selectedCollection = collectionOptions.includes(activeCollection) ? activeCollection : "All"
    const movies = useMemo(
        () => filterCollectionMovies(searchedMovies, selectedCollection),
        [searchedMovies, selectedCollection, userStateVersion],
    )
    const shows = useMemo(
        () => filterCollectionShows(searchedShows, selectedCollection),
        [searchedShows, selectedCollection, userStateVersion],
    )
    const visibleMovies = useMemo(() => movies.slice(0, limit), [limit, movies])
    const visibleShows = useMemo(() => shows.slice(0, limit), [limit, shows])
    const recentMovies = useMemo(() => recentItems(searchedMovies), [searchedMovies])
    const recentShows = useMemo(() => recentShowsList(searchedShows), [searchedShows])
    const selectedMovie = useMemo(
        () => searchedMovies.find((item) => item.playback_id === selectedKey) ?? null,
        [searchedMovies, selectedKey],
    )
    const selectedShow = useMemo(
        () => searchedShows.find((show) => show.id === selectedKey) ?? null,
        [selectedKey, searchedShows],
    )
    const hasItems = items.length > 0
    const noMatches = hasItems && (isTv ? searchedShows.length === 0 : searchedMovies.length === 0)

    const headerSearch = useMemo(
        () => (
            <SearchBox
                value={query}
                onChange={setQuery}
                placeholder={isTv ? "Search shows, seasons, episodes" : "Search movies, genres, cast"}
            />
        ),
        [isTv, query],
    )
    const headerActions = useMemo(
        () => (
            <button
                type="button"
                onClick={() => void load()}
                disabled={loading}
                aria-label="Refresh"
                title="Refresh"
                className="flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-50"
            >
                <RefreshCw className={cn("h-[18px] w-[18px]", loading && "animate-spin")} />
            </button>
        ),
        [load, loading],
    )
    useEffect(() => registerHeader({
        locationKey: `${location.pathname}?${location.search}`,
        title,
        immersive: Boolean(selectedKey),
        back: selectedKey ? clear : false,
        backLabel: selectedKey ? "Back to list" : "Back",
        search: selectedKey ? undefined : headerSearch,
        actions: selectedKey ? undefined : headerActions,
    }), [clear, headerActions, headerSearch, location.pathname, location.search, registerHeader, selectedKey, title])

    useEffect(() => {
        if (!selectedKey) return
        let node = rootRef.current?.parentElement
        while (node) {
            if (node.scrollHeight > node.clientHeight && getComputedStyle(node).overflowY !== "visible") {
                node.scrollTop = 0
                break
            }
            node = node.parentElement
        }
    }, [selectedKey])

    const detailReady = Boolean(selectedKey) && hasItems && !noMatches
    const activeDetail = detailReady ? (isTv ? selectedShow : selectedMovie) : null

    return (
        <div ref={rootRef} className="min-h-screen pb-24">
            {activeDetail && isTv && selectedShow ? (
                <ShowDetail
                    key={selectedShow.id}
                    show={selectedShow}
                    onBack={clear}
                    onUserStateChange={() => setUserStateVersion((value) => value + 1)}
                />
            ) : activeDetail && !isTv && selectedMovie ? (
                <MovieDetail
                    key={selectedMovie.playback_id}
                    item={selectedMovie}
                    onBack={clear}
                    onUserStateChange={() => setUserStateVersion((value) => value + 1)}
                />
            ) : (
                <div className="space-y-5 px-4 pt-5 sm:px-6 sm:pt-7">
                    {loading && !hasItems && <div className="flex justify-center py-16"><Spinner /></div>}
                    {error && !hasItems && (
                        <EmptyState
                            icon={Icon}
                            title={`Couldn’t load ${title.toLowerCase()}`}
                            description={error}
                            action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                        />
                    )}
                    {!loading && !error && !hasItems && (
                        <EmptyState icon={Icon} title={`No ${title.toLowerCase()} yet`} description="Sync this media source in Organize first." />
                    )}
                    {noMatches && (
                        <EmptyState icon={Search} title="No matches" description="Try a shorter title, year, genre, or cast search." />
                    )}
                    {selectedKey && hasItems && !noMatches && !activeDetail && (
                        <EmptyState
                            icon={Icon}
                            title="Title not found"
                            description="This item is no longer in your library."
                            action={{ label: "Back to list", onClick: clear, variant: "primary" }}
                        />
                    )}
                    {!selectedKey && hasItems && !noMatches && (
                        isTv ? (
                            <VideoHome
                                kind="tv"
                                recentShows={recentShows}
                                shows={visibleShows}
                                selectedKey=""
                                collectionLabels={collectionLabels}
                                activeCollection={selectedCollection}
                                hasMore={visibleShows.length < shows.length}
                                onSelectShow={(show) => select(show.id)}
                                onLoadMore={() => setLimit((value) => value + PAGE_SIZE)}
                                onCollection={setActiveCollection}
                            />
                        ) : (
                            <VideoHome
                                kind="movies"
                                recentMovies={recentMovies}
                                movies={visibleMovies}
                                selectedPath=""
                                collectionLabels={collectionLabels}
                                activeCollection={selectedCollection}
                                hasMore={visibleMovies.length < movies.length}
                                onSelectMovie={(item) => select(item.playback_id ?? "")}
                                onLoadMore={() => setLimit((value) => value + PAGE_SIZE)}
                                onCollection={setActiveCollection}
                            />
                        )
                    )}
                </div>
            )}
        </div>
    )
}

function SearchBox({
    value,
    placeholder,
    onChange,
}: {
    value: string
    placeholder: string
    onChange: (value: string) => void
}) {
    return (
        <label className="relative w-full max-w-xl">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
                type="search"
                value={value}
                onChange={(event) => onChange(event.target.value)}
                placeholder={placeholder}
                className="h-11 w-full rounded-full border border-border/70 bg-card pl-11 pr-4 text-[15px] shadow-sm outline-none transition-colors placeholder:text-muted-foreground/45 hover:bg-card/90 focus:border-ring/45 focus:ring-2 focus:ring-ring/15"
            />
        </label>
    )
}
