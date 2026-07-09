import { ChevronLeft, Search, X } from "lucide-react"
import type { ReactNode } from "react"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import type { SearchBarContext } from "@/hooks/use-search-bar-context"

interface SearchFieldProps {
    context: SearchBarContext
    libraryInput: string
    onLibraryInputChange: (value: string) => void
    onLibraryClear?: () => void
    onLibrarySubmit: () => void
    trailing?: ReactNode
}

export function SearchField({
    context,
    libraryInput,
    onLibraryInputChange,
    onLibraryClear,
    onLibrarySubmit,
    trailing,
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
    const canClear = value.length > 0 && !albumsRootSearchDisabled

    const clearSearch = () => {
        if (isInAlbumSection) setAlbumSectionSearch("")
        else {
            onLibraryInputChange("")
            onLibraryClear?.()
        }
    }

    return (
        <div className="relative flex min-w-0 flex-1 items-center">
            <button
                onClick={handleBack}
                className={cn(
                    "absolute left-2.5 top-1/2 z-10 flex h-7 w-7 -translate-y-1/2 shrink-0 items-center justify-center rounded-full text-muted-foreground/60 transition-all duration-200 hover:bg-secondary hover:text-foreground",
                    pinned ? "opacity-100 scale-100" : "opacity-0 scale-75 pointer-events-none",
                )}
                aria-label="Back"
                tabIndex={pinned ? 0 : -1}
            >
                <ChevronLeft className="h-4 w-4" />
            </button>

            <Search
                className={cn(
                    "pointer-events-none absolute left-4 top-1/2 z-10 h-[18px] w-[18px] -translate-y-1/2 text-foreground/65 transition-opacity duration-200",
                    pinned ? "opacity-0" : "opacity-100",
                )}
                strokeWidth={2.15}
            />

            <Input
                wrapperClassName="w-full"
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
                    "h-11 w-full rounded-full border border-border/70 bg-card text-[15px] shadow-sm transition-[background,border-color,padding] duration-200 placeholder:text-muted-foreground/45 hover:bg-card/90 focus-visible:border-ring/45 focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-ring/15",
                    pinned ? "pl-10" : "pl-11",
                    trailing ? "pr-20" : "pr-10",
                )}
            />
            <button
                type="button"
                onClick={clearSearch}
                aria-label="Clear search"
                tabIndex={canClear ? 0 : -1}
                className={cn(
                    "absolute top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full bg-secondary text-muted-foreground transition-all hover:bg-muted hover:text-foreground",
                    trailing ? "right-11" : "right-3",
                    canClear ? "scale-100 opacity-100" : "pointer-events-none scale-75 opacity-0",
                )}
            >
                <X className="h-3.5 w-3.5" />
            </button>
            {trailing && (
                <div className="absolute right-2 top-1/2 z-20 -translate-y-1/2">
                    {trailing}
                </div>
            )}
        </div>
    )
}
