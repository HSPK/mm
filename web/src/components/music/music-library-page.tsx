import { useCallback, useDeferredValue, useEffect, useRef, useState } from "react"
import { Music, Search } from "lucide-react"
import { musicRepo, type MusicQuery } from "@/api/music"
import { EmptyState } from "@/components/ui/empty-state"
import { Spinner } from "@/components/ui/spinner"
import { notify } from "@/stores/notifications"
import { usePlayerStore, type PlayerTrack } from "@/stores/player"
import {
    type AlbumGroup,
    type ArtistGroup,
    albumFromSummary,
    buildAlbumGroups,
    buildArtistGroups,
    shuffleTracks,
    trackFromSummary,
} from "./music-library-model"
import {
    AlbumDetail,
    AlbumsView,
    HomeView,
    MusicToolbar,
    ViewTabs,
    type AlbumDisplay,
} from "./music-library-ui"
import { ArtistDetail, ArtistGrid } from "./music-artist-views"
import { InfiniteScrollSentinel } from "./music-infinite-scroll"
import {
    MUSIC_ALBUM_PAGE_SIZE,
    MUSIC_ARTIST_PAGE_SIZE,
    MUSIC_TRACK_PAGE_SIZE,
    loadMusicAlbums,
    loadMusicArtists,
    loadMusicLibrary,
    loadMusicTracks,
} from "./music-library-loader"
import { TrackTable } from "./music-track-table"
import { loadMusicQueue } from "./music-queue-loader"
import { useMusicNavigation } from "./use-music-navigation"

export function MusicLibraryPage() {
    const [albums, setAlbums] = useState<AlbumGroup[]>([])
    const [albumTotal, setAlbumTotal] = useState(0)
    const [tracks, setTracks] = useState<PlayerTrack[]>([])
    const [trackTotal, setTrackTotal] = useState(0)
    const [artists, setArtists] = useState<ArtistGroup[]>([])
    const [artistTotal, setArtistTotal] = useState(0)
    const [selectedAlbum, setSelectedAlbum] = useState<AlbumGroup | null>(null)
    const [selectedAlbumTracks, setSelectedAlbumTracks] = useState<PlayerTrack[]>([])
    const [selectedAlbumTrackTotal, setSelectedAlbumTrackTotal] = useState(0)
    const [selectedArtist, setSelectedArtist] = useState<ArtistGroup | null>(null)
    const [selectedArtistAlbums, setSelectedArtistAlbums] = useState<AlbumGroup[]>([])
    const [selectedArtistAlbumTotal, setSelectedArtistAlbumTotal] = useState(0)
    const [selectedArtistTracks, setSelectedArtistTracks] = useState<PlayerTrack[]>([])
    const [selectedArtistTrackTotal, setSelectedArtistTrackTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [albumDisplay, setAlbumDisplay] = useState<AlbumDisplay>("grid")
    const [query, setQuery] = useState("")
    const deferredQuery = useDeferredValue(query.trim())
    const requestVersion = useRef(0)
    const albumDetailVersion = useRef(0)
    const artistDetailVersion = useRef(0)
    const loadingMore = useRef(new Set<string>())
    const {
        view,
        albumKey,
        artistId,
        setView,
        openAlbum: openAlbumKey,
        openArtist: openArtistId,
        backToList,
    } = useMusicNavigation()
    const setQueue = usePlayerStore((state) => state.setQueue)
    const playTrack = usePlayerStore((state) => state.playTrack)
    const playNext = usePlayerStore((state) => state.playNext)

    const load = useCallback(async (search: string) => {
        const version = ++requestVersion.current
        setLoading(true)
        setError(null)
        try {
            const data = await loadMusicLibrary(search)
            if (version !== requestVersion.current) return
            setAlbums(buildAlbumGroups(data.albums.albums))
            setAlbumTotal(data.albums.total)
            setTracks(data.tracks.tracks.map(trackFromSummary))
            setTrackTotal(data.tracks.total)
            setArtists(buildArtistGroups(data.artists.artists))
            setArtistTotal(data.artists.total)
            loadingMore.current.clear()
        } catch (err) {
            if (version === requestVersion.current) {
                setError(err instanceof Error ? err.message : "Could not load music")
            }
        } finally {
            if (version === requestVersion.current) setLoading(false)
        }
    }, [])

    useEffect(() => {
        const id = window.setTimeout(() => {
            void load(deferredQuery)
        }, 80)
        return () => window.clearTimeout(id)
    }, [deferredQuery, load])

    useEffect(() => {
        const reload = () => {
            void load(deferredQuery)
        }
        window.addEventListener("mm:library-changed", reload)
        return () => window.removeEventListener("mm:library-changed", reload)
    }, [deferredQuery, load])

    useEffect(() => {
        const version = ++albumDetailVersion.current
        if (!albumKey) return
        let cancelled = false
        const existing = albums.find((album) => album.id === albumKey)
        void Promise.all([
            existing ? Promise.resolve(existing) : musicRepo.album(albumKey).then(albumFromSummary),
            loadMusicTracks({
                album_id: albumKey,
                query: deferredQuery || undefined,
                offset: 0,
                limit: MUSIC_TRACK_PAGE_SIZE,
            }),
        ]).then(([album, page]) => {
            if (cancelled || version !== albumDetailVersion.current) return
            setSelectedAlbum({ ...album, tracks: page.tracks.map(trackFromSummary) })
            setSelectedAlbumTracks(page.tracks.map(trackFromSummary))
            setSelectedAlbumTrackTotal(page.total)
        }).catch(() => {
            if (!cancelled && version === albumDetailVersion.current) backToList("albums")
        })
        return () => {
            cancelled = true
        }
    }, [albumKey, albums, backToList, deferredQuery])

    useEffect(() => {
        const version = ++artistDetailVersion.current
        if (!artistId) return
        let cancelled = false
        const existing = artists.find((artist) => artist.id === artistId)
        void Promise.all([
            existing ? Promise.resolve(existing) : musicRepo.artist(artistId).then((artist) => (
                buildArtistGroups([artist])[0]
            )),
            loadMusicAlbums({
                artist_id: artistId,
                query: deferredQuery || undefined,
                offset: 0,
                limit: MUSIC_ALBUM_PAGE_SIZE,
            }),
            loadMusicTracks({
                artist_id: artistId,
                query: deferredQuery || undefined,
                offset: 0,
                limit: MUSIC_TRACK_PAGE_SIZE,
            }),
        ]).then(([artist, albumPage, trackPage]) => {
            if (cancelled || version !== artistDetailVersion.current) return
            const artistTracks = trackPage.tracks.map(trackFromSummary)
            setSelectedArtist({ ...artist, tracks: artistTracks })
            setSelectedArtistAlbums(buildAlbumGroups(albumPage.albums))
            setSelectedArtistAlbumTotal(albumPage.total)
            setSelectedArtistTracks(artistTracks)
            setSelectedArtistTrackTotal(trackPage.total)
        }).catch(() => {
            if (!cancelled && version === artistDetailVersion.current) backToList("artists")
        })
        return () => {
            cancelled = true
        }
    }, [artistId, artists, backToList, deferredQuery])

    const loadMoreAlbums = useCallback(async () => {
        const version = requestVersion.current
        const key = `albums:${version}`
        if (albums.length >= albumTotal || loadingMore.current.has(key)) return
        loadingMore.current.add(key)
        try {
            const page = await loadMusicAlbums({
                query: deferredQuery || undefined,
                offset: albums.length,
                limit: MUSIC_ALBUM_PAGE_SIZE,
            })
            if (version !== requestVersion.current) return
            setAlbums((current) => appendUnique(
                current,
                buildAlbumGroups(page.albums),
                (album) => album.id,
            ))
            setAlbumTotal(page.total)
        } catch (error) {
            if (version === requestVersion.current) reportCatalogPageError(error)
        } finally {
            loadingMore.current.delete(key)
        }
    }, [albumTotal, albums.length, deferredQuery])

    const loadMoreTracks = useCallback(async () => {
        const version = requestVersion.current
        const key = `tracks:${version}`
        if (tracks.length >= trackTotal || loadingMore.current.has(key)) return
        loadingMore.current.add(key)
        try {
            const page = await loadMusicTracks({
                query: deferredQuery || undefined,
                offset: tracks.length,
                limit: MUSIC_TRACK_PAGE_SIZE,
            })
            if (version !== requestVersion.current) return
            setTracks((current) => appendUnique(
                current,
                page.tracks.map(trackFromSummary),
                (track) => track.id,
            ))
            setTrackTotal(page.total)
        } catch (error) {
            if (version === requestVersion.current) reportCatalogPageError(error)
        } finally {
            loadingMore.current.delete(key)
        }
    }, [deferredQuery, trackTotal, tracks.length])

    const loadMoreArtists = useCallback(async () => {
        const version = requestVersion.current
        const key = `artists:${version}`
        if (artists.length >= artistTotal || loadingMore.current.has(key)) return
        loadingMore.current.add(key)
        try {
            const page = await loadMusicArtists({
                query: deferredQuery || undefined,
                offset: artists.length,
                limit: MUSIC_ARTIST_PAGE_SIZE,
            })
            if (version !== requestVersion.current) return
            setArtists((current) => appendUnique(
                current,
                buildArtistGroups(page.artists),
                (artist) => artist.id,
            ))
            setArtistTotal(page.total)
        } catch (error) {
            if (version === requestVersion.current) reportCatalogPageError(error)
        } finally {
            loadingMore.current.delete(key)
        }
    }, [artistTotal, artists.length, deferredQuery])

    const loadMoreAlbumTracks = useCallback(async () => {
        const version = albumDetailVersion.current
        const key = `album-tracks:${version}`
        if (
            !albumKey
            || selectedAlbumTracks.length >= selectedAlbumTrackTotal
            || loadingMore.current.has(key)
        ) return
        loadingMore.current.add(key)
        try {
            const page = await loadMusicTracks({
                album_id: albumKey,
                query: deferredQuery || undefined,
                offset: selectedAlbumTracks.length,
                limit: MUSIC_TRACK_PAGE_SIZE,
            })
            if (version !== albumDetailVersion.current) return
            setSelectedAlbumTracks((current) => appendUnique(
                current,
                page.tracks.map(trackFromSummary),
                (track) => track.id,
            ))
            setSelectedAlbumTrackTotal(page.total)
        } catch (error) {
            if (version === albumDetailVersion.current) reportCatalogPageError(error)
        } finally {
            loadingMore.current.delete(key)
        }
    }, [albumKey, deferredQuery, selectedAlbumTrackTotal, selectedAlbumTracks.length])

    const loadMoreArtistAlbums = useCallback(async () => {
        const version = artistDetailVersion.current
        const key = `artist-albums:${version}`
        if (
            !artistId
            || selectedArtistAlbums.length >= selectedArtistAlbumTotal
            || loadingMore.current.has(key)
        ) return
        loadingMore.current.add(key)
        try {
            const page = await loadMusicAlbums({
                artist_id: artistId,
                query: deferredQuery || undefined,
                offset: selectedArtistAlbums.length,
                limit: MUSIC_ALBUM_PAGE_SIZE,
            })
            if (version !== artistDetailVersion.current) return
            setSelectedArtistAlbums((current) => appendUnique(
                current,
                buildAlbumGroups(page.albums),
                (album) => album.id,
            ))
            setSelectedArtistAlbumTotal(page.total)
        } catch (error) {
            if (version === artistDetailVersion.current) reportCatalogPageError(error)
        } finally {
            loadingMore.current.delete(key)
        }
    }, [artistId, deferredQuery, selectedArtistAlbumTotal, selectedArtistAlbums.length])

    const loadMoreArtistTracks = useCallback(async () => {
        const version = artistDetailVersion.current
        const key = `artist-tracks:${version}`
        if (
            !artistId
            || selectedArtistTracks.length >= selectedArtistTrackTotal
            || loadingMore.current.has(key)
        ) return
        loadingMore.current.add(key)
        try {
            const page = await loadMusicTracks({
                artist_id: artistId,
                query: deferredQuery || undefined,
                offset: selectedArtistTracks.length,
                limit: MUSIC_TRACK_PAGE_SIZE,
            })
            if (version !== artistDetailVersion.current) return
            setSelectedArtistTracks((current) => appendUnique(
                current,
                page.tracks.map(trackFromSummary),
                (track) => track.id,
            ))
            setSelectedArtistTrackTotal(page.total)
        } catch (error) {
            if (version === artistDetailVersion.current) reportCatalogPageError(error)
        } finally {
            loadingMore.current.delete(key)
        }
    }, [artistId, deferredQuery, selectedArtistTrackTotal, selectedArtistTracks.length])

    const playAlbum = useCallback((album: AlbumGroup) => {
        void queueAllTracks(
            { album_id: album.id, query: deferredQuery || undefined },
            (items) => setQueue(items, 0, true),
        )
    }, [deferredQuery, setQueue])

    const playNextAlbum = useCallback((album: AlbumGroup) => {
        void queueAllTracks(
            { album_id: album.id, query: deferredQuery || undefined },
            playNext,
        )
    }, [deferredQuery, playNext])

    const playArtist = useCallback((artist: ArtistGroup) => {
        void queueAllTracks(
            { artist_id: artist.id, query: deferredQuery || undefined },
            (items) => setQueue(items, 0, true),
        )
    }, [deferredQuery, setQueue])

    const playNextArtist = useCallback((artist: ArtistGroup) => {
        void queueAllTracks(
            { artist_id: artist.id, query: deferredQuery || undefined },
            playNext,
        )
    }, [deferredQuery, playNext])

    const playFilteredTracks = useCallback(() => {
        void queueAllTracks(
            { query: deferredQuery || undefined },
            (items) => setQueue(items, 0, true),
        )
    }, [deferredQuery, setQueue])

    const shuffleFilteredTracks = useCallback(() => {
        void queueAllTracks(
            { query: deferredQuery || undefined },
            (items) => setQueue(shuffleTracks(items), 0, true),
        )
    }, [deferredQuery, setQueue])

    const hasMusic = albumTotal > 0 || trackTotal > 0 || artistTotal > 0
    const showNoMatches = !loading && Boolean(deferredQuery) && !hasMusic
    const activeAlbum = selectedAlbum?.id === albumKey ? selectedAlbum : null
    const activeArtist = selectedArtist?.id === artistId ? selectedArtist : null

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
                        action={{ label: "Retry", onClick: () => void load(deferredQuery), variant: "primary" }}
                    />
                )}
                {!loading && !error && !hasMusic && !showNoMatches && (
                    <EmptyState icon={Music} title="No music yet" description="Sync music sources in Organize to build the music library." />
                )}
                {showNoMatches && (
                    <EmptyState icon={Search} title="No music matched" description="Try a different song, album, or artist search." />
                )}
                {((view === "album" && !activeAlbum) || (view === "artist" && !activeArtist))
                    && <div className="flex justify-center py-16"><Spinner /></div>}

                {hasMusic && !showNoMatches && view === "home" && (
                    <HomeView
                        albums={albums}
                        tracks={tracks}
                        albumTotal={albumTotal}
                        trackTotal={trackTotal}
                        onViewAlbums={() => setView("albums")}
                        onViewSongs={() => setView("songs")}
                        onOpenAlbum={(album) => openAlbumKey(album.id)}
                        onPlayAlbum={playAlbum}
                        onPlayTrack={(track) => playTrack(track, tracks)}
                        onPlayNextAlbum={playNextAlbum}
                        onPlayNextTrack={playNext}
                    />
                )}
                {hasMusic && !showNoMatches && view === "albums" && (
                    <AlbumsView
                        albums={albums}
                        total={albumTotal}
                        display={albumDisplay}
                        onDisplayChange={setAlbumDisplay}
                        onOpenAlbum={(album) => openAlbumKey(album.id)}
                        onPlayAlbum={playAlbum}
                        onPlayNextAlbum={playNextAlbum}
                        hasMore={albums.length < albumTotal}
                        onLoadMore={() => void loadMoreAlbums()}
                    />
                )}
                {hasMusic && !showNoMatches && view === "artists" && (
                    <div className="space-y-4">
                        <ArtistGrid
                            artists={artists}
                            onOpenArtist={(artist) => openArtistId(artist.id)}
                            onPlay={playArtist}
                            onPlayNext={playNextArtist}
                        />
                        <InfiniteScrollSentinel
                            key={artists.length}
                            hasMore={artists.length < artistTotal}
                            onLoadMore={() => void loadMoreArtists()}
                        />
                    </div>
                )}
                {hasMusic && !showNoMatches && view === "songs" && (
                    <div className="space-y-4">
                        <TrackTable
                            tracks={tracks}
                            onPlay={(track) => playTrack(track, tracks)}
                            onPlayNext={playNext}
                        />
                        <InfiniteScrollSentinel
                            key={tracks.length}
                            hasMore={tracks.length < trackTotal}
                            onLoadMore={() => void loadMoreTracks()}
                        />
                    </div>
                )}
                {view === "album" && activeAlbum && (
                    <AlbumDetail
                        album={activeAlbum}
                        tracks={selectedAlbumTracks}
                        matchedCount={selectedAlbumTrackTotal}
                        query={deferredQuery}
                        onBack={() => backToList("albums")}
                        onPlay={() => playAlbum(activeAlbum)}
                        onShuffle={() => {
                            void queueAllTracks(
                                { album_id: activeAlbum.id, query: deferredQuery || undefined },
                                (items) => setQueue(shuffleTracks(items), 0, true),
                            )
                        }}
                        onPlayNext={() => playNextAlbum(activeAlbum)}
                        onPlayTrack={(track) => playTrack(track, selectedAlbumTracks)}
                        onPlayNextTrack={playNext}
                        hasMore={selectedAlbumTracks.length < selectedAlbumTrackTotal}
                        onLoadMore={() => void loadMoreAlbumTracks()}
                    />
                )}
                {view === "artist" && activeArtist && (
                    <ArtistDetail
                        artist={activeArtist}
                        albums={selectedArtistAlbums}
                        tracks={selectedArtistTracks}
                        matchedTrackCount={selectedArtistTrackTotal}
                        query={deferredQuery}
                        hasMoreAlbums={selectedArtistAlbums.length < selectedArtistAlbumTotal}
                        hasMoreTracks={selectedArtistTracks.length < selectedArtistTrackTotal}
                        onBack={() => backToList("artists")}
                        onOpenAlbum={(album) => openAlbumKey(album.id)}
                        onLoadMoreAlbums={() => void loadMoreArtistAlbums()}
                        onLoadMoreTracks={() => void loadMoreArtistTracks()}
                        onPlay={() => playArtist(activeArtist)}
                        onShuffle={() => {
                            void queueAllTracks(
                                { artist_id: activeArtist.id, query: deferredQuery || undefined },
                                (items) => setQueue(shuffleTracks(items), 0, true),
                            )
                        }}
                        onPlayNext={() => playNextArtist(activeArtist)}
                        onPlayAlbum={playAlbum}
                        onPlayNextAlbum={playNextAlbum}
                        onPlayTrack={(track) => playTrack(track, selectedArtistTracks)}
                        onPlayNextTrack={playNext}
                    />
                )}
            </div>
        </div>
    )
}

async function queueAllTracks(
    params: Omit<MusicQuery, "offset" | "limit">,
    consume: (tracks: PlayerTrack[]) => void,
) {
    try {
        const tracks = await loadMusicQueue(params)
        if (tracks?.length) consume(tracks)
    } catch (error) {
        notify.error(
            "Couldn’t load music",
            error instanceof Error ? error.message : "The music queue could not be created.",
        )
    }
}

function appendUnique<T>(
    current: T[],
    incoming: T[],
    key: (item: T) => string,
) {
    const seen = new Set(current.map(key))
    return [...current, ...incoming.filter((item) => !seen.has(key(item)))]
}

function reportCatalogPageError(error: unknown) {
    notify.error(
        "Couldn’t load more music",
        error instanceof Error ? error.message : "The next page could not be loaded.",
    )
}
