import { useCallback } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { useAlbumSectionStore } from "@/stores/album-section"
import { useMediaQueryStore } from "@/stores/media-query"

export interface SearchBarContext {
    isOnLibrary: boolean
    isOnAlbums: boolean
    isInAlbumSection: boolean
    isInAlbumView: boolean
    isDeletedView: boolean
    showFilters: boolean
    albumsRootSearchDisabled: boolean
    activeLabel: string | null
    albumSectionLabel: string | null
    albumSectionSearch: string
    setAlbumSectionSearch: (value: string) => void
    exitAlbumSection: () => void
    handleBack: () => void
    pinned: boolean
}

/**
 * Derives all the boolean flags + back-button behaviour the search bar UI
 * needs. Reads from the router + media/album stores; never mutates them
 * (other than the explicit user actions exposed as callbacks).
 */
export function useSearchBarContext(): SearchBarContext {
    const navigate = useNavigate()
    const location = useLocation()

    const activeLabel = useMediaQueryStore((s) => s.activeLabel)
    const deleted = useMediaQueryStore((s) => s.filters.deleted)
    const resetFilters = useMediaQueryStore((s) => s.resetFilters)

    const {
        label: albumSectionLabel,
        search: albumSectionSearch,
        setSearch: setAlbumSectionSearch,
        exit: exitAlbumSectionState,
    } = useAlbumSectionStore()

    const isOnLibrary = location.pathname === "/"
    const isOnAlbums = location.pathname === "/albums"
    const isInAlbumView = isOnLibrary && !!activeLabel
    const isInAlbumSection = isOnAlbums && !!albumSectionLabel
    const isDeletedView = deleted
    const showFilters = isOnLibrary && !isDeletedView
    const albumsRootSearchDisabled = isOnAlbums && !isInAlbumSection

    const exitAlbumSection = useCallback(() => {
        const next = new URLSearchParams(location.search)
        next.delete("section")
        exitAlbumSectionState()
        navigate(
            { pathname: "/albums", search: next.toString() ? `?${next.toString()}` : "" },
            { replace: true },
        )
    }, [exitAlbumSectionState, location.search, navigate])

    const handleBack = useCallback(() => {
        if (isInAlbumSection) {
            exitAlbumSection()
        } else if (isDeletedView || activeLabel) {
            resetFilters()
            navigate("/albums")
        }
    }, [activeLabel, exitAlbumSection, isDeletedView, isInAlbumSection, navigate, resetFilters])

    return {
        isOnLibrary,
        isOnAlbums,
        isInAlbumSection,
        isInAlbumView,
        isDeletedView,
        showFilters,
        albumsRootSearchDisabled,
        activeLabel,
        albumSectionLabel,
        albumSectionSearch,
        setAlbumSectionSearch,
        exitAlbumSection,
        handleBack,
        pinned: !!activeLabel || isDeletedView || isInAlbumSection,
    }
}
