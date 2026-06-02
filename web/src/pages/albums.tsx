import { useEffect, useState, useMemo, useCallback, useRef } from "react"
import { api } from "@/api/client"
import { useMediaStore, type Filters } from "@/stores/media"
import { useAlbumSectionStore } from "@/stores/album-section"
import { useNavigate, useSearchParams } from "react-router-dom"
import { AlbumCard } from "@/components/album-card"
import { buildAlbumItems } from "@/lib/albums"
import type { SectionDef, SectionId, SmartAlbumsResponse } from "@/api/types"
import {
    Images,
    ImageOff,
    Loader2,
    AlertTriangle,
    ChevronRight,
    type LucideIcon,
} from "lucide-react"

// ─── Section header ───────────────────────────────────────

function SectionHeader({
    icon: Icon,
    title,
    count,
    onSeeAll,
}: {
    icon: LucideIcon
    title: string
    count?: number
    onSeeAll?: () => void
}) {
    return (
        <div className="flex items-center justify-between mb-4 px-1">
            <div className="flex items-center gap-2.5">
                <Icon className="h-5 w-5 text-muted-foreground/50" />
                <h2 className="text-lg font-bold text-foreground/90 tracking-tight">
                    {title}
                </h2>
                {count != null && (
                    <span className="text-xs text-muted-foreground/40 font-medium">
                        {count}
                    </span>
                )}
            </div>
            {onSeeAll && (
                <button
                    onClick={onSeeAll}
                    className="flex items-center gap-0.5 text-sm text-primary/70 hover:text-primary transition-colors font-medium"
                >
                    See All
                    <ChevronRight className="h-4 w-4" />
                </button>
            )}
        </div>
    )
}

// ─── Section detail view (二级页面) ───────────────────────
// No own header / search bar — handled by FloatingSearchBar via album-section store

function SectionDetailView({ section }: { section: SectionDef }) {
    const search = useAlbumSectionStore((s) => s.search)
    const setSearch = useAlbumSectionStore((s) => s.setSearch)

    const filtered = useMemo(() => {
        if (!search.trim()) return section.items
        const q = search.toLowerCase()
        return section.items.filter(
            (item) =>
                item.searchText.toLowerCase().includes(q) ||
                item.title.toLowerCase().includes(q),
        )
    }, [section.items, search])

    return (
        <div className="px-2 sm:px-4 pt-2 pb-24">
            {filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
                    <ImageOff className="h-10 w-10 mb-3 opacity-40" />
                    <p className="text-base font-medium mb-1">
                        {search ? "No matching albums" : "No albums yet"}
                    </p>
                    <p className="text-sm text-muted-foreground/60 mb-5">
                        {search ? "Try adjusting your search" : ""}
                    </p>
                    {search && (
                        <button
                            onClick={() => setSearch("")}
                            className="h-8 px-4 rounded-xl bg-secondary/50 text-xs font-medium text-foreground/80 hover:bg-secondary transition-colors"
                        >
                            Clear search
                        </button>
                    )}
                </div>
            ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                    {filtered.map((item) => (
                        <AlbumCard
                            key={item.key}
                            icon={item.icon}
                            title={item.title}
                            subtitle={item.subtitle}
                            count={item.count}
                            coverId={item.coverId}
                            onClick={item.onClick}
                            color={item.color}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}

// ─── Main Albums Page ─────────────────────────────────────

export default function AlbumsPage() {
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const { setFilters, setActiveLabel } = useMediaStore()
    const { sectionId, enter: enterSection, exit: exitSection } = useAlbumSectionStore()

    const [loading, setLoading] = useState(true)
    const [loadError, setLoadError] = useState<string | null>(null)
    const [retryTick, setRetryTick] = useState(0)
    const [data, setData] = useState<SmartAlbumsResponse | null>(null)
    const rootRef = useRef<HTMLDivElement>(null)

    // Scroll parent container to top when switching views
    useEffect(() => {
        const scrollParent = rootRef.current?.parentElement
        if (scrollParent) {
            scrollParent.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior })
        }
    }, [sectionId])

    // Single API call to load everything
    useEffect(() => {
        let mounted = true
        api.get<SmartAlbumsResponse>("/smart-albums")
            .then((res) => {
                if (mounted) {
                    setData(res.data)
                    setLoadError(null)
                    setLoading(false)
                }
            })
            .catch(() => {
                if (mounted) {
                    setData(null)
                    setLoadError("Could not load albums")
                    setLoading(false)
                }
            })
        return () => {
            mounted = false
        }
    }, [retryTick])

    // Navigation helper — apply filters and switch to library tab
    const goLibraryWith = useCallback(
        (updates: Record<string, unknown>, label?: string) => {
            setFilters({
                type: null,
                tag: null,
                camera: null,
                date_from: null,
                date_to: null,
                date_ranges: null,
                sort: "date_taken",
                order: "desc",
                search: null,
                min_rating: null,
                favorites_only: false,
                lat: null,
                lon: null,
                radius: null,
                no_date: false,
                deleted: false,
                ...updates,
            } as Partial<Filters>)
            const lockedKeys = Object.entries(updates)
                .filter(([, v]) => v != null && v !== false && v !== "")
                .map(([k]) => k)
            setActiveLabel(label ?? null, lockedKeys)
            navigate("/")
        },
        [navigate, setFilters, setActiveLabel],
    )

    const { libraryItems, sections } = useMemo(
        () => buildAlbumItems(data, goLibraryWith),
        [data, goLibraryWith],
    )

    useEffect(() => {
        if (!data) return
        const sectionParam = searchParams.get("section")
        if (!sectionParam) {
            if (sectionId) exitSection()
            return
        }

        const sec = sections.find((s) => s.id === sectionParam)
        if (!sec) {
            const next = new URLSearchParams(searchParams)
            next.delete("section")
            setSearchParams(next, { replace: true })
            return
        }
        if (sectionId !== sec.id) enterSection(sec.id, sec.title)
    }, [data, enterSection, exitSection, searchParams, sectionId, sections, setSearchParams])

    // Detail navigation — route search params are the source of truth
    const openDetail = useCallback((id: SectionId) => {
        const sec = sections.find((s) => s.id === id)
        if (!sec) return
        const next = new URLSearchParams(searchParams)
        next.set("section", id)
        setSearchParams(next)
        enterSection(id, sec.title)
    }, [searchParams, sections, enterSection, setSearchParams])

    const activeDetail = useMemo(
        () => (sectionId ? sections.find((s) => s.id === sectionId) ?? null : null),
        [sectionId, sections],
    )

    // ── Loading ───────────────────────────────────────────
    if (loading) {
        return (
            <div className="flex items-center justify-center h-full pb-24">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/40" />
            </div>
        )
    }

    if (loadError) {
        return (
            <div ref={rootRef} className="flex h-full flex-col items-center justify-center px-8 pb-24 text-center text-muted-foreground">
                <AlertTriangle className="mb-3 h-8 w-8 text-destructive/60" />
                <p className="mb-1 text-sm font-semibold text-foreground/80">{loadError}</p>
                <p className="mb-5 max-w-xs text-xs text-muted-foreground/60">
                    Check the server connection and try loading the album sections again.
                </p>
                <button
                    type="button"
                    onClick={() => {
                        setLoading(true)
                        setLoadError(null)
                        setRetryTick((tick) => tick + 1)
                    }}
                    className="rounded-full bg-secondary px-4 py-2 text-xs font-semibold text-foreground/80 transition-colors hover:bg-secondary/80"
                >
                    Retry
                </button>
            </div>
        )
    }

    // ── Detail view ───────────────────────────────────────
    if (activeDetail) {
        return (
            <div ref={rootRef} className="animate-[slide-in-right_250ms_ease-out]">
                <SectionDetailView section={activeDetail} />
            </div>
        )
    }

    // ── Main album list ───────────────────────────────────
    return (
        <div ref={rootRef} className="pb-24">
            <div className="px-4 pt-1 space-y-10">
                {/* ── Library ── */}
                {libraryItems.length > 0 && (
                    <section>
                        <SectionHeader icon={Images} title="Library" />
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                            {libraryItems.map((item) => (
                                <AlbumCard
                                    key={item.key}
                                    icon={item.icon}
                                    title={item.title}
                                    subtitle={item.subtitle}
                                    count={item.count}
                                    coverId={item.coverId}
                                    onClick={item.onClick}
                                    color={item.color}
                                />
                            ))}
                        </div>
                    </section>
                )}

                {/* ── Dynamic sections ── */}
                {sections.map((section) => {
                    const preview = section.previewItems ?? section.items
                    const showSeeAll = section.previewItems
                        ? section.items.length > 0
                        : section.items.length > section.previewCount
                    return (
                        <section key={section.id}>
                            <SectionHeader
                                icon={section.icon}
                                title={section.title}
                                count={section.items.length}
                                onSeeAll={showSeeAll ? () => openDetail(section.id) : undefined}
                            />
                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                                {preview.slice(0, section.previewCount).map((item) => (
                                    <AlbumCard
                                        key={item.key}
                                        icon={item.icon}
                                        title={item.title}
                                        subtitle={item.subtitle}
                                        count={item.count}
                                        coverId={item.coverId}
                                        onClick={item.onClick}
                                        color={item.color}
                                    />
                                ))}
                            </div>
                        </section>
                    )
                })}
            </div>
        </div>
    )
}
