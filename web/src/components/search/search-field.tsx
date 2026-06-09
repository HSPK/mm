import { ChevronLeft, Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import type { SearchBarContext } from "@/hooks/use-search-bar-context"

interface SearchFieldProps {
    context: SearchBarContext
    libraryInput: string
    onLibraryInputChange: (value: string) => void
    onLibrarySubmit: () => void
}

export function SearchField({
    context,
    libraryInput,
    onLibraryInputChange,
    onLibrarySubmit,
}: SearchFieldProps) {
    const {
        isInAlbumSection,
        isDeletedView,
        isInAlbumView,
        activeLabel,
        albumSectionLabel,
        albumSectionSearch,
        setAlbumSectionSearch,
        albumsRootSearchDisabled,
        pinned,
        handleBack,
    } = context

    const value = isInAlbumSection
        ? albumSectionSearch
        : albumsRootSearchDisabled
            ? ""
            : libraryInput

    const placeholder = isInAlbumSection
        ? `Search ${albumSectionLabel}…`
        : isDeletedView
            ? "Search deleted…"
            : isInAlbumView
                ? `Search in ${activeLabel}…`
                : albumsRootSearchDisabled
                    ? "Open a section to search…"
                    : "Search photos…"

    return (
        <div className="relative flex-1 flex items-center">
            <button
                onClick={handleBack}
                className={cn(
                    "absolute left-2.5 top-1/2 -translate-y-1/2 z-10 flex items-center justify-center h-6 w-6 rounded-full text-muted-foreground/50 hover:text-foreground hover:bg-secondary/60 transition-all duration-200 shrink-0",
                    pinned ? "opacity-100 scale-100" : "opacity-0 scale-75 pointer-events-none",
                )}
                aria-label="Back"
                tabIndex={pinned ? 0 : -1}
            >
                <ChevronLeft className="h-4 w-4" />
            </button>

            <Search
                className={cn(
                    "absolute left-3.5 top-1/2 -translate-y-1/2 h-[18px] w-[18px] text-muted-foreground/40 transition-opacity duration-200",
                    pinned ? "opacity-0" : "opacity-100",
                )}
            />

            <Input
                value={value}
                onChange={(e) => {
                    if (isInAlbumSection) setAlbumSectionSearch(e.target.value)
                    else if (!albumsRootSearchDisabled) onLibraryInputChange(e.target.value)
                }}
                onKeyDown={(e) => {
                    if (e.key !== "Enter") return
                    if (isInAlbumSection || albumsRootSearchDisabled) return
                    onLibrarySubmit()
                }}
                disabled={albumsRootSearchDisabled}
                aria-label={
                    isInAlbumSection
                        ? `Search ${albumSectionLabel}`
                        : albumsRootSearchDisabled
                            ? "Albums search unavailable"
                            : "Search media"
                }
                placeholder={placeholder}
                className={cn(
                    "w-full h-11 pr-4 text-sm bg-background/80 backdrop-blur-xl border border-border/60 rounded-full placeholder:text-muted-foreground/40 focus-visible:ring-1 focus-visible:ring-ring/30 shadow-lg shadow-black/10 transition-[padding] duration-200",
                    pinned ? "pl-10" : "pl-11",
                )}
            />
        </div>
    )
}
