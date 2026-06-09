import { useEffect, useRef, useState, type MouseEvent } from "react"
import { Menu, X } from "lucide-react"
import { useMediaQueryStore } from "@/stores/media-query"
import { useSearchBarContext } from "@/hooks/use-search-bar-context"
import { useFilterTagList } from "@/hooks/use-filter-tag-list"
import { useAutoHideOnScroll } from "@/hooks/use-auto-hide-on-scroll"
import { ActiveFilterTags } from "@/components/search/active-filter-tags"
import { FilterMenu } from "@/components/search/filter-menu"
import { SearchField } from "@/components/search/search-field"
import { cn } from "@/lib/utils"

/**
 * Top-level floating search bar. Composes:
 *  - SearchField (input + back button)
 *  - FilterMenu (dropdown with filters / nav / logout)
 *  - ActiveFilterTags (chip row below the input)
 *
 * The bar auto-hides on scroll down (unless pinned by an album/trash/section view).
 */
export function FloatingSearchBar({ scrollContainer }: { scrollContainer?: HTMLElement | null }) {
    const context = useSearchBarContext()
    const setFilter = useMediaQueryStore((s) => s.setFilter)
    const filtersSearch = useMediaQueryStore((s) => s.filters.search)

    const [searchInput, setSearchInput] = useState(filtersSearch ?? "")
    const [menuOpen, setMenuOpen] = useState(false)
    const menuRef = useRef<HTMLDivElement>(null)

    const { visible, setVisible } = useAutoHideOnScroll(
        scrollContainer ?? null,
        context.pinned,
    )

    useEffect(() => {
        if (!visible) setMenuOpen(false)
    }, [visible])

    useEffect(() => {
        if (!context.isInAlbumSection) setSearchInput(filtersSearch ?? "")
    }, [context.isInAlbumSection, filtersSearch])

    useEffect(() => {
        setVisible(true)
        setMenuOpen(false)
    }, [scrollContainer, setVisible])

    useEffect(() => {
        if (context.isOnAlbums) {
            const state = useMediaQueryStore.getState()
            if (state.activeLabel) state.resetFilters()
        }
    }, [context.isOnAlbums])

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false)
            }
        }
        document.addEventListener("mousedown", handler as unknown as EventListener)
        return () => document.removeEventListener("mousedown", handler as unknown as EventListener)
    }, [])

    const tags = useFilterTagList({
        context,
        onSearchCleared: () => setSearchInput(""),
    })

    const submitSearch = () => {
        if (context.albumsRootSearchDisabled) return
        setFilter("search", searchInput || null)
    }

    return (
        <div
            className={cn(
                "fixed top-0 left-0 right-0 z-40 transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                visible ? "translate-y-0" : "-translate-y-full",
            )}
            aria-hidden={!visible}
            inert={visible ? undefined : true}
            style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
        >
            <div className="px-4 pt-2.5 pb-1 mx-auto max-w-2xl">
                <div className="flex items-center gap-2">
                    <SearchField
                        context={context}
                        libraryInput={searchInput}
                        onLibraryInputChange={setSearchInput}
                        onLibrarySubmit={submitSearch}
                    />

                    <div className="relative" ref={menuRef}>
                        <button
                            onClick={() => setMenuOpen((open) => !open)}
                            aria-label={menuOpen ? "Close menu" : "Open menu"}
                            aria-expanded={menuOpen}
                            aria-haspopup="menu"
                            className={cn(
                                "flex h-11 w-11 items-center justify-center rounded-full elevation-2 transition-all duration-200",
                                menuOpen
                                    ? "bg-secondary text-foreground"
                                    : "material-thick text-muted-foreground hover:bg-secondary/60",
                            )}
                        >
                            {menuOpen ? <X className="h-[18px] w-[18px]" /> : <Menu className="h-[18px] w-[18px]" />}
                        </button>

                        {menuOpen && (
                            <FilterMenu
                                showFilters={context.showFilters}
                                onNavigate={() => setMenuOpen(false)}
                            />
                        )}
                    </div>
                </div>

                <ActiveFilterTags tags={tags} />
            </div>
        </div>
    )
}
