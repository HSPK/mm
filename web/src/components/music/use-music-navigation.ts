import { useCallback } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"
import type { MusicView } from "./music-library-ui"

interface MusicNavState {
    musicDetail?: boolean
}

const BASE_VIEWS = new Set<MusicView>(["home", "albums", "artists", "songs"])

/**
 * Mirrors the music library's navigation (tab view + album/artist detail) into
 * URL search params so refresh and browser back/forward work:
 *   - `?view=albums|artists|songs`  the active tab (home is the bare route)
 *   - `?album=<album id>`           an open album detail (secondary level)
 *   - `?artist=<artist id>`         an open artist detail (secondary level)
 * Tab switches replace in place; opening a detail pushes a history entry.
 */
export function useMusicNavigation() {
    const location = useLocation()
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const albumKey = searchParams.get("album")
    const artistId = searchParams.get("artist")
    const viewParam = searchParams.get("view") as MusicView | null

    const view: MusicView = albumKey
        ? "album"
        : artistId
            ? "artist"
            : viewParam && BASE_VIEWS.has(viewParam)
                ? viewParam
                : "home"

    const setView = useCallback((next: MusicView) => {
        const params = new URLSearchParams(searchParams)
        params.delete("album")
        params.delete("artist")
        if (next === "home" || !BASE_VIEWS.has(next)) params.delete("view")
        else params.set("view", next)
        setSearchParams(params, { replace: true, state: null })
    }, [searchParams, setSearchParams])

    const openAlbum = useCallback((key: string) => {
        const params = new URLSearchParams(searchParams)
        params.set("album", key)
        params.delete("artist")
        setSearchParams(params, { replace: Boolean(albumKey), state: { musicDetail: true } satisfies MusicNavState })
    }, [albumKey, searchParams, setSearchParams])

    const openArtist = useCallback((id: string) => {
        const params = new URLSearchParams(searchParams)
        params.set("artist", id)
        params.delete("album")
        setSearchParams(params, { replace: Boolean(artistId), state: { musicDetail: true } satisfies MusicNavState })
    }, [artistId, searchParams, setSearchParams])

    const backToList = useCallback((fallback: MusicView) => {
        const openedFromList = Boolean((location.state as MusicNavState | null)?.musicDetail)
        if (openedFromList) {
            navigate(-1)
            return
        }
        const params = new URLSearchParams(searchParams)
        params.delete("album")
        params.delete("artist")
        if (fallback === "home") params.delete("view")
        else params.set("view", fallback)
        setSearchParams(params, { replace: true, state: null })
    }, [location.state, navigate, searchParams, setSearchParams])

    return { view, albumKey, artistId, setView, openAlbum, openArtist, backToList }
}
