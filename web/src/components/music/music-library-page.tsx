import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react"
import { Music, Search } from "lucide-react"
import {
    organizerRepo,
    type OrganizerItem,
    type OrganizerMusicAlbum,
} from "@/api/organizer"
import { EmptyState } from "@/components/ui/empty-state"
import { Spinner } from "@/components/ui/spinner"
import { usePlayerStore } from "@/stores/player"
import {
    type AlbumGroup,
    type ArtistGroup,
    albumTrackSort,
    buildAlbumGroups,
    filterAlbums,
    filterTracks,
    groupArtists,
    loadMusicDetailsByAlbum,
    mergeOrganizerItems,
    shuffleTracks,
    trackSort,
} from "./music-library-model"
import {
    AlbumDetail,
    AlbumsView,
    HomeView,
    MusicToolbar,
    ViewTabs,
    type AlbumDisplay,
    type MusicView,
} from "./music-library-ui"
import { primePlayerTrackDetails } from "@/components/player/use-enriched-player-track"
import { ArtistDetail, ArtistGrid } from "./music-artist-views"
import { InfiniteScrollSentinel } from "./music-infinite-scroll"
import { TrackTable } from "./music-track-table"

const INITIAL_ALBUM_LIMIT = 96
const ALBUM_PAGE_SIZE = 96
const INITIAL_TRACK_LIMIT = 200
const TRACK_PAGE_SIZE = 200

export function MusicLibraryPage() {
    const [items, setItems] = useState<OrganizerItem[]>([])
    const [albumSummaries, setAlbumSummaries] = useState<OrganizerMusicAlbum[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [view, setView] = useState<MusicView>("home")
    const [albumDisplay, setAlbumDisplay] = useState<AlbumDisplay>("grid")
    const [selectedAlbumKey, setSelectedAlbumKey] = useState<string | null>(null)
    const [selectedArtistName, setSelectedArtistName] = useState<string | null>(null)
    const [albumLimit, setAlbumLimit] = useState(INITIAL_ALBUM_LIMIT)
    const [trackLimit, setTrackLimit] = useState(INITIAL_TRACK_LIMIT)
    const [albumTrackLimit, setAlbumTrackLimit] = useState(INITIAL_TRACK_LIMIT)
    const [artistAlbumLimit, setArtistAlbumLimit] = useState(INITIAL_ALBUM_LIMIT)
    const [artistTrackLimit, setArtistTrackLimit] = useState(INITIAL_TRACK_LIMIT)
    const [query, setQuery] = useState("")
    const deferredQuery = useDeferredValue(query)
    const setQueue = usePlayerStore((state) => state.setQueue)
    const playTrack = usePlayerStore((state) => state.playTrack)
    const playNext = usePlayerStore((state) => state.playNext)

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const [baseItems, albums] = await Promise.all([
                organizerRepo.items("music"),
                organizerRepo.musicAlbums(),
            ])
            setItems(baseItems)
            setAlbumSummaries(albums)
            void loadMusicDetailsByAlbum(baseItems, (detailItems) => {
                setItems((current) => mergeOrganizerItems(current, detailItems))
            })
        } catch (err) {
            setError(err instanceof Error ? err.message : "Could not load music")
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        const id = window.setTimeout(() => { void load() }, 0)
        return () => window.clearTimeout(id)
    }, [load])

    useEffect(() => {
        const ids = albumSummaries
            .map((album) => album.cover_playback_id)
            .filter((id): id is string => Boolean(id))
            .slice(0, 120)
        if (ids.length > 0) void organizerRepo.artworkBatch(ids, 320).catch(() => undefined)
    }, [albumSummaries])

    useEffect(() => {
        setAlbumLimit(INITIAL_ALBUM_LIMIT)
        setTrackLimit(INITIAL_TRACK_LIMIT)
        setAlbumTrackLimit(INITIAL_TRACK_LIMIT)
        setArtistAlbumLimit(INITIAL_ALBUM_LIMIT)
        setArtistTrackLimit(INITIAL_TRACK_LIMIT)
    }, [albumDisplay, deferredQuery, view])

    useEffect(() => {
        setAlbumTrackLimit(INITIAL_TRACK_LIMIT)
    }, [deferredQuery, selectedAlbumKey])

    useEffect(() => {
        setArtistAlbumLimit(INITIAL_ALBUM_LIMIT)
        setArtistTrackLimit(INITIAL_TRACK_LIMIT)
    }, [deferredQuery, selectedArtistName])

    const baseAlbums = useMemo(
        () => buildAlbumGroups(albumSummaries, items),
        [albumSummaries, items],
    )
    const albums = useMemo(() => filterAlbums(baseAlbums, deferredQuery), [baseAlbums, deferredQuery])
    const allTracks = useMemo(() => baseAlbums.flatMap((album) => album.tracks), [baseAlbums])
    const tracks = useMemo(() => filterTracks(allTracks, deferredQuery).sort(trackSort), [allTracks, deferredQuery])
    const baseArtists = useMemo(() => groupArtists(baseAlbums), [baseAlbums])
    const artists = useMemo(() => groupArtists(albums), [albums])
    const selectedAlbum = useMemo(
        () => baseAlbums.find((album) => album.key === selectedAlbumKey) ?? null,
        [baseAlbums, selectedAlbumKey],
    )
    const selectedAlbumTracks = useMemo(
        () => selectedAlbum
            ? filterTracks(selectedAlbum.tracks, deferredQuery).sort(albumTrackSort)
            : [],
        [deferredQuery, selectedAlbum],
    )
    const visibleSelectedAlbumTracks = useMemo(
        () => selectedAlbumTracks.slice(0, albumTrackLimit),
        [albumTrackLimit, selectedAlbumTracks],
    )
    const selectedArtist = useMemo(
        () => baseArtists.find((artist) => artist.name === selectedArtistName) ?? null,
        [baseArtists, selectedArtistName],
    )
    const selectedArtistAlbums = useMemo(
        () => selectedArtist
            ? filterAlbums(baseAlbums.filter((album) => album.artist === selectedArtist.name), deferredQuery)
            : [],
        [baseAlbums, deferredQuery, selectedArtist],
    )
    const selectedArtistTracks = useMemo(
        () => selectedArtist
            ? filterTracks(selectedArtist.tracks, deferredQuery).sort(trackSort)
            : [],
        [deferredQuery, selectedArtist],
    )
    const visibleSelectedArtistAlbums = useMemo(
        () => selectedArtistAlbums.slice(0, artistAlbumLimit),
        [artistAlbumLimit, selectedArtistAlbums],
    )
    const visibleSelectedArtistTracks = useMemo(
        () => selectedArtistTracks.slice(0, artistTrackLimit),
        [artistTrackLimit, selectedArtistTracks],
    )
    const visibleAlbums = useMemo(() => albums.slice(0, albumLimit), [albumLimit, albums])
    const visibleTracks = useMemo(() => tracks.slice(0, trackLimit), [trackLimit, tracks])
    const hasMusic = albumSummaries.length > 0 || items.length > 0
    const showNoMatches = hasMusic && albums.length === 0 && tracks.length === 0

    useEffect(() => {
        if (view === "album" && selectedAlbumKey && !selectedAlbum) {
            setView("albums")
            setSelectedAlbumKey(null)
        }
        if (view === "artist" && selectedArtistName && !selectedArtist) {
            setView("artists")
            setSelectedArtistName(null)
        }
    }, [selectedAlbum, selectedAlbumKey, selectedArtist, selectedArtistName, view])

    const openAlbum = useCallback((album: AlbumGroup) => {
        setSelectedAlbumKey(album.key)
        setView("album")
    }, [])

    const playAlbum = useCallback((album: AlbumGroup) => {
        primePlayerTrackDetails(album.tracks.slice(0, 8))
        setQueue(album.tracks, 0, true)
    }, [setQueue])

    const openArtist = useCallback((artist: ArtistGroup) => {
        setSelectedArtistName(artist.name)
        setView("artist")
    }, [])

    const playFilteredTracks = useCallback(() => {
        primePlayerTrackDetails(tracks.slice(0, 8))
        setQueue(tracks, 0, true)
    }, [setQueue, tracks])

    const shuffleFilteredTracks = useCallback(() => {
        const shuffled = shuffleTracks(tracks)
        primePlayerTrackDetails(shuffled.slice(0, 8))
        setQueue(shuffled, 0, true)
    }, [setQueue, tracks])

    return (
        <div className="min-h-screen pb-32">
            <div className="space-y-6 px-4 pt-5 sm:px-6 sm:pt-7">
                <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                    <ViewTabs view={view} onChange={setView} />
                    <MusicToolbar
                        tracks={tracks}
                        query={query}
                        onQueryChange={setQuery}
                        onPlayAll={playFilteredTracks}
                        onShuffle={shuffleFilteredTracks}
                    />
                </div>

                {loading && !hasMusic && <div className="flex justify-center py-16"><Spinner /></div>}
                {error && !hasMusic && (
                    <EmptyState
                        icon={Music}
                        title="Couldn’t load music"
                        description={error}
                        action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                    />
                )}
                {!loading && !error && !hasMusic && (
                    <EmptyState icon={Music} title="No music yet" description="Sync music sources in Organize to build the music library." />
                )}
                {showNoMatches && (
                    <EmptyState icon={Search} title="No music matched" description="Try a different song, album, or artist search." />
                )}

                {hasMusic && !showNoMatches && view === "home" && albums.length > 0 && (
                    <HomeView
                        albums={albums}
                        tracks={tracks}
                        onViewAlbums={() => setView("albums")}
                        onViewSongs={() => setView("songs")}
                        onOpenAlbum={openAlbum}
                        onPlayAlbum={playAlbum}
                        onPlayTrack={(track) => playTrack(track, tracks)}
                        onPlayNext={(tracksToInsert) => playNext(tracksToInsert)}
                    />
                )}
                {hasMusic && !showNoMatches && view === "albums" && (
                    <AlbumsView
                        albums={visibleAlbums}
                        total={albums.length}
                        display={albumDisplay}
                        onDisplayChange={setAlbumDisplay}
                        onOpenAlbum={openAlbum}
                        onPlayAlbum={playAlbum}
                        onPlayNext={(tracksToInsert) => playNext(tracksToInsert)}
                        hasMore={visibleAlbums.length < albums.length}
                        onLoadMore={() => setAlbumLimit((value) => value + ALBUM_PAGE_SIZE)}
                    />
                )}
                {hasMusic && !showNoMatches && view === "artists" && (
                    <ArtistGrid
                        artists={artists}
                        onOpenArtist={openArtist}
                        onPlay={(artist) => setQueue(artist.tracks, 0, true)}
                        onPlayNext={(artist) => playNext(artist.tracks)}
                    />
                )}
                {hasMusic && !showNoMatches && view === "songs" && (
                    <div className="space-y-4">
                        <TrackTable
                            tracks={visibleTracks}
                            onPlay={(track) => playTrack(track, tracks)}
                            onPlayNext={(track) => playNext(track)}
                        />
                        <InfiniteScrollSentinel
                            key={visibleTracks.length}
                            hasMore={visibleTracks.length < tracks.length}
                            onLoadMore={() => setTrackLimit((value) => value + TRACK_PAGE_SIZE)}
                        />
                    </div>
                )}
                {hasMusic && !showNoMatches && view === "album" && selectedAlbum && (
                    <AlbumDetail
                        album={selectedAlbum}
                        tracks={visibleSelectedAlbumTracks}
                        matchedCount={selectedAlbumTracks.length}
                        query={deferredQuery}
                        onBack={() => setView("albums")}
                        onPlay={() => setQueue(selectedAlbumTracks, 0, true)}
                        onShuffle={() => setQueue(shuffleTracks(selectedAlbumTracks), 0, true)}
                        onPlayNext={() => playNext(selectedAlbumTracks)}
                        onPlayTrack={(track) => playTrack(track, selectedAlbumTracks)}
                        onPlayNextTrack={(track) => playNext(track)}
                        hasMore={visibleSelectedAlbumTracks.length < selectedAlbumTracks.length}
                        onLoadMore={() => setAlbumTrackLimit((value) => value + TRACK_PAGE_SIZE)}
                    />
                )}
                {hasMusic && !showNoMatches && view === "artist" && selectedArtist && (
                    <ArtistDetail
                        artist={selectedArtist}
                        albums={visibleSelectedArtistAlbums}
                        tracks={visibleSelectedArtistTracks}
                        matchedTrackCount={selectedArtistTracks.length}
                        query={deferredQuery}
                        hasMoreAlbums={visibleSelectedArtistAlbums.length < selectedArtistAlbums.length}
                        hasMoreTracks={visibleSelectedArtistTracks.length < selectedArtistTracks.length}
                        onBack={() => setView("artists")}
                        onOpenAlbum={openAlbum}
                        onLoadMoreAlbums={() => setArtistAlbumLimit((value) => value + ALBUM_PAGE_SIZE)}
                        onLoadMoreTracks={() => setArtistTrackLimit((value) => value + TRACK_PAGE_SIZE)}
                        onPlay={() => setQueue(selectedArtistTracks, 0, true)}
                        onShuffle={() => setQueue(shuffleTracks(selectedArtistTracks), 0, true)}
                        onPlayNext={() => playNext(selectedArtistTracks)}
                        onPlayAlbum={playAlbum}
                        onPlayNextAlbum={(album) => playNext(album.tracks)}
                        onPlayTrack={(track) => playTrack(track, selectedArtistTracks)}
                        onPlayNextTrack={(track) => playNext(track)}
                    />
                )}
            </div>
        </div>
    )
}
