import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react"
import { Film, Search, Tv } from "lucide-react"
import { useLocation } from "react-router-dom"
import { videoRepo, type VideoLibraryItem } from "@/api/videos"
import { useHeaderRegistration } from "@/components/navigation/header-context"
import { EmptyState } from "@/components/ui/empty-state"
import { Spinner } from "@/components/ui/spinner"
import { MovieDetail, ShowDetail } from "./video-detail"
import { VideoHome } from "./video-home"
import {
    collectionNames,
    filterCollectionMovies,
    filterCollectionShows,
    hasProgress,
    recentItems,
    recentShowsList,
    showHasProgress,
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
    const [selectedKey, setSelectedKey] = useState<string | null>(null)
    const [activeCollection, setActiveCollection] = useState("All")
    const [userStateVersion, setUserStateVersion] = useState(0)
    const location = useLocation()
    const registerHeader = useHeaderRegistration()
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
        () => ["All", "Favorites", "Unwatched", ...collectionLabels],
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
    const continueMovies = useMemo(() => searchedMovies.filter(hasProgress).slice(0, 12), [searchedMovies, userStateVersion])
    const continueShows = useMemo(() => searchedShows.filter(showHasProgress).slice(0, 12), [searchedShows, userStateVersion])
    const recentMovies = useMemo(() => recentItems(searchedMovies), [searchedMovies])
    const recentShows = useMemo(() => recentShowsList(searchedShows), [searchedShows])
    const selectedMovie = useMemo(
        () => searchedMovies.find((item) => item.path === selectedKey) ?? null,
        [searchedMovies, selectedKey],
    )
    const selectedShow = useMemo(
        () => searchedShows.find((show) => show.key === selectedKey) ?? null,
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
    useEffect(() => registerHeader({
        locationKey: `${location.pathname}?${location.search}`,
        title,
        back: selectedKey ? () => setSelectedKey(null) : false,
        backLabel: selectedKey ? "Back to list" : "Back",
        search: headerSearch,
    }), [headerSearch, location.pathname, location.search, registerHeader, selectedKey, title])

    return (
        <div className="min-h-screen pb-24">
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

                {!noMatches && hasItems && (
                    <>
                        <div>
                            {isTv && selectedShow ? (
                                <ShowDetail
                                    show={selectedShow}
                                    onUserStateChange={() => setUserStateVersion((value) => value + 1)}
                                />
                            ) : selectedMovie ? (
                                <MovieDetail
                                    item={selectedMovie}
                                    onUserStateChange={() => setUserStateVersion((value) => value + 1)}
                                />
                            ) : null}
                        </div>
                        {selectedKey ? null : isTv ? (
                            <VideoHome
                                kind="tv"
                                continueShows={continueShows}
                                recentShows={recentShows}
                                shows={visibleShows}
                                selectedKey={selectedShow?.key ?? ""}
                                collectionLabels={collectionLabels}
                                activeCollection={selectedCollection}
                                hasMore={visibleShows.length < shows.length}
                                onSelectShow={(show) => setSelectedKey(show.key)}
                                onLoadMore={() => setLimit((value) => value + PAGE_SIZE)}
                                onCollection={setActiveCollection}
                            />
                        ) : (
                            <VideoHome
                                kind="movies"
                                continueMovies={continueMovies}
                                recentMovies={recentMovies}
                                movies={visibleMovies}
                                selectedPath={selectedMovie?.path ?? ""}
                                collectionLabels={collectionLabels}
                                activeCollection={selectedCollection}
                                hasMore={visibleMovies.length < movies.length}
                                onSelectMovie={(item) => setSelectedKey(item.path)}
                                onLoadMore={() => setLimit((value) => value + PAGE_SIZE)}
                                onCollection={setActiveCollection}
                            />
                        )}
                    </>
                )}
            </div>
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
