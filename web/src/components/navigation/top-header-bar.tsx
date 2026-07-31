import { useEffect, useMemo, useRef, useState } from "react"
import { ChevronLeft, FolderInput, LayoutDashboard, Map as MapIcon, SlidersHorizontal, type LucideIcon } from "lucide-react"
import { NavLink, useLocation } from "react-router-dom"
import { FilterMenu } from "@/components/search/filter-menu"
import { SearchField } from "@/components/search/search-field"
import { useHeaderConfig } from "@/components/navigation/header-context"
import { useSearchBarContext } from "@/hooks/use-search-bar-context"
import { cn } from "@/lib/utils"
import { useMediaQueryStore } from "@/stores/media-query"
import { useNavigate } from "react-router-dom"

const pageTitles: Record<string, string> = {
    "/dashboard": "Stats",
    "/map": "Map",
    "/organize": "Organize",
    "/import": "Import",
    "/movies": "Movies",
    "/tv": "TV Series",
    "/music": "Music",
    "/settings": "Settings",
    "/admin/users": "Users",
}

function getHeaderTitle(pathname: string, tabTitle: string) {
    if (pathname === "/" || pathname.startsWith("/albums")) return tabTitle
    return pageTitles[pathname] ?? "LiteMM"
}

export function TopHeaderBar({ isTabRoute }: { isTabRoute: boolean }) {
    const location = useLocation()
    const navigate = useNavigate()
    const registeredHeader = useHeaderConfig()
    const context = useSearchBarContext()
    const setFilter = useMediaQueryStore((s) => s.setFilter)
    const filtersSearch = useMediaQueryStore((s) => s.filters.search)

    const [draftSearch, setDraftSearch] = useState<string | null>(null)
    const locationKey = `${location.pathname}?${location.search}`
    const [menuState, setMenuState] = useState({ key: locationKey, open: false })
    const menuRef = useRef<HTMLDivElement>(null)
    const menuOpen = menuState.key === locationKey && menuState.open
    const routeHeader = !isTabRoute && registeredHeader?.locationKey === locationKey
        ? registeredHeader
        : null
    const searchInput = draftSearch ?? filtersSearch ?? ""

    useEffect(() => {
        if (context.isOnAlbums) {
            const state = useMediaQueryStore.getState()
            if (state.activeLabel) state.resetFilters()
        }
    }, [context.isOnAlbums])

    useEffect(() => {
        const handler = (event: globalThis.MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setMenuState((state) => ({ ...state, open: false }))
            }
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    const submitSearch = () => {
        if (context.albumsRootSearchDisabled) return
        setFilter("search", searchInput || null)
        setDraftSearch(null)
    }
    const clearLibrarySearch = () => {
        setFilter("search", null)
        setDraftSearch(null)
    }

    const tabTitle = useMemo(() => {
        if (context.isInAlbumSection) return context.albumSectionLabel ?? "Albums"
        if (context.isDeletedView) return "Trash"
        if (context.isInAlbumView) return context.activeLabel ?? "Library"
        if (context.isOnAlbums) return "Albums"
        return "Library"
    }, [
        context.activeLabel,
        context.albumSectionLabel,
        context.isDeletedView,
        context.isInAlbumSection,
        context.isInAlbumView,
        context.isOnAlbums,
    ])
    const title = routeHeader?.title ?? getHeaderTitle(location.pathname, tabTitle)
    const back = routeHeader?.back ?? (!isTabRoute ? true : undefined)
    const backLabel = routeHeader?.backLabel
    const showLibraryShortcuts = location.pathname === "/"
    const handleBack = () => {
        if (!back) return
        if (typeof back === "function") back()
        else navigate(-1)
    }

    if (
        location.pathname === "/organize"
        || location.pathname === "/music"
    ) {
        return null
    }

    if (routeHeader?.immersive) {
        return null
    }

    return (
        <header
            className="material-bar hairline-b relative z-30 shrink-0"
            style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
        >
            <div className="flex min-h-16 items-center gap-4 px-3 py-2 sm:px-5">
                {!isTabRoute && back && (
                    <button
                        type="button"
                        onClick={handleBack}
                        aria-label={backLabel ?? "Back"}
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-primary transition-colors hover:bg-primary/10 active:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                        <ChevronLeft className="h-[18px] w-[18px] stroke-[2.4]" />
                    </button>
                )}

                {isTabRoute && (
                    <div className="mr-auto w-[30rem] min-w-72 max-w-[calc(100vw-24rem)]">
                        <SearchField
                            context={context}
                            libraryInput={searchInput}
                            onLibraryInputChange={setDraftSearch}
                            onLibraryClear={clearLibrarySearch}
                            onLibrarySubmit={submitSearch}
                            trailing={context.showFilters && (
                                <div className="relative" ref={menuRef}>
                                <button
                                    type="button"
                                    onClick={() => setMenuState({ key: locationKey, open: !menuOpen })}
                                    aria-label={menuOpen ? "Close filters" : "Open filters"}
                                    aria-expanded={menuOpen}
                                    aria-haspopup="menu"
                                    className={cn(
                                        "flex h-8 w-8 items-center justify-center rounded-full transition-colors duration-200",
                                        menuOpen
                                            ? "bg-primary/12 text-primary"
                                            : "text-foreground/65 hover:bg-secondary hover:text-foreground",
                                    )}
                                >
                                    <SlidersHorizontal className="h-[18px] w-[18px]" strokeWidth={2.1} />
                                </button>

                                {menuOpen && (
                                    <FilterMenu
                                        showFilters={context.showFilters}
                                    />
                                )}
                                </div>
                            )}
                        />
                    </div>
                )}

                {!isTabRoute && routeHeader?.search && (
                    <div className="mr-auto w-[30rem] min-w-72 max-w-[calc(100vw-24rem)]">
                        {routeHeader.search}
                    </div>
                )}

                {!isTabRoute && !routeHeader?.search && (
                    <div className="min-w-0 flex-1">
                        <h1 className="truncate text-[20px] font-semibold tracking-tight">{title}</h1>
                    </div>
                )}

                {!isTabRoute && routeHeader?.actions && (
                    <div className="flex shrink-0 items-center gap-1.5">
                        {routeHeader.actions}
                    </div>
                )}

                {showLibraryShortcuts && (
                    <div className="ml-auto hidden shrink-0 items-center gap-1 md:flex">
                        <HeaderShortcut to="/import" label="Import" icon={FolderInput} />
                        <HeaderShortcut to="/map" label="Map" icon={MapIcon} />
                        <HeaderShortcut to="/dashboard" label="Stats" icon={LayoutDashboard} />
                    </div>
                )}
            </div>
        </header>
    )
}

function HeaderShortcut({
    to,
    label,
    icon: Icon,
}: {
    to: string
    label: string
    icon: LucideIcon
}) {
    return (
        <NavLink
            to={to}
            aria-label={label}
            title={label}
            className={({ isActive }) => cn(
                "inline-flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
                isActive && "bg-secondary text-foreground",
            )}
        >
            <Icon className="h-4 w-4" />
        </NavLink>
    )
}
