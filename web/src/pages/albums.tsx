import { useEffect, useState, useMemo, useCallback, useRef, memo } from "react"
import { api } from "@/api/client"
import { useMediaStore, type Filters } from "@/stores/media"
import { useAlbumSectionStore } from "@/stores/album-section"
import { useNavigate } from "react-router-dom"
import { AuthImage } from "@/components/auth-image"
import {
    Images,
    Camera,
    MapPin,
    Calendar,
    HelpCircle,
    Trash2,
    Star,
    Film,
    Image,
    ImageOff,
    Loader2,
    ChevronRight,
    Tag,
    Sparkles,
    type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"

// ─── Icon registry ────────────────────────────────────────

const ICON_MAP: Record<string, LucideIcon> = {
    images: Images,
    image: Image,
    film: Film,
    star: Star,
    "trash-2": Trash2,
    tag: Tag,
    camera: Camera,
    sparkles: Sparkles,
    calendar: Calendar,
    "help-circle": HelpCircle,
    "map-pin": MapPin,
}

function resolveIcon(name?: string): LucideIcon {
    return (name && ICON_MAP[name]) || Images
}

// ─── Types from backend ───────────────────────────────────

interface SmartAlbum {
    key: string
    title: string
    subtitle?: string
    count?: number
    cover_id?: number | null
    icon?: string
    color?: string
    filters: Record<string, unknown>
    search_text?: string
    festival_id?: string
}

interface SmartAlbumsResponse {
    library: SmartAlbum[]
    tags: SmartAlbum[]
    cameras: SmartAlbum[]
    festivals: SmartAlbum[]
    years: SmartAlbum[]
    places: SmartAlbum[]
}

type SectionId = "tags" | "cameras" | "festivals" | "years" | "places"

// ─── UI item (adds onClick from filters) ──────────────────

interface AlbumItem {
    key: string
    icon: LucideIcon
    title: string
    subtitle?: string
    count?: number
    coverId?: number | null
    onClick: () => void
    color?: string
    searchText: string
}

interface SectionDef {
    id: SectionId
    icon: LucideIcon
    title: string
    items: AlbumItem[]
    previewItems?: AlbumItem[]
    previewCount: number
}

// ─── Album card ───────────────────────────────────────────

interface AlbumCardProps {
    icon: LucideIcon
    title: string
    subtitle?: string
    count?: number
    coverId?: number | null
    onClick: () => void
    color?: string
}

const AlbumCard = memo(function AlbumCard({
    icon: Icon,
    title,
    subtitle,
    count,
    coverId,
    onClick,
    color,
}: AlbumCardProps) {
    return (
        <button
            onClick={onClick}
            className="group relative overflow-hidden rounded-2xl bg-secondary/30 border border-border/60 hover:border-border/80 hover:shadow-lg hover:shadow-black/20 transition-all duration-300 text-left w-full"
        >
            <div className="aspect-[4/3] relative overflow-hidden bg-muted">
                {coverId ? (
                    <AuthImage
                        apiSrc={`/media/${coverId}/thumbnail?size=lg`}
                        alt=""
                        loading="lazy"
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                ) : (
                    <div
                        className={cn(
                            "h-full w-full flex items-center justify-center",
                            color || "bg-secondary/50",
                        )}
                    >
                        <Icon className="h-12 w-12 text-muted-foreground/15" />
                    </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent" />
                {count != null && (
                    <span className="absolute top-2.5 right-2.5 inline-flex items-center rounded-full bg-black/50 backdrop-blur-sm px-2.5 py-0.5 text-xs text-white/90 font-medium border border-white/10">
                        {count.toLocaleString()}
                    </span>
                )}
                <div className="absolute bottom-0 left-0 right-0 p-3.5">
                    <h3 className="text-base font-semibold text-white truncate leading-tight">
                        {title}
                    </h3>
                    {subtitle && (
                        <p className="text-xs text-white/55 mt-1 truncate">
                            {subtitle}
                        </p>
                    )}
                </div>
            </div>
        </button>
    )
})

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

// ─── Convert backend album → UI item ──────────────────────

function toAlbumItem(
    album: SmartAlbum,
    goLibraryWith: (filters: Record<string, unknown>, label?: string) => void,
): AlbumItem {
    return {
        key: album.key,
        icon: resolveIcon(album.icon),
        title: album.title,
        subtitle: album.subtitle,
        count: album.count,
        coverId: album.cover_id,
        onClick: () => goLibraryWith(album.filters, album.title),
        color: album.color,
        searchText: album.search_text || album.title,
    }
}

// ─── Main Albums Page ─────────────────────────────────────

export default function AlbumsPage() {
    const navigate = useNavigate()
    const { setFilters, setActiveLabel } = useMediaStore()
    const { sectionId, enter: enterSection } = useAlbumSectionStore()

    const [loading, setLoading] = useState(true)
    const [data, setData] = useState<SmartAlbumsResponse | null>(null)
    const rootRef = useRef<HTMLDivElement>(null)

    // Track return animation (detail → list)
    const prevSectionRef = useRef<string | null>(null)
    const [returning, setReturning] = useState(false)
    useEffect(() => {
        if (prevSectionRef.current && !sectionId) {
            setReturning(true)
            const t = setTimeout(() => setReturning(false), 250)
            return () => clearTimeout(t)
        }
        prevSectionRef.current = sectionId
    }, [sectionId])

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
                    setLoading(false)
                }
            })
            .catch(() => {
                if (mounted) setLoading(false)
            })
        return () => {
            mounted = false
        }
    }, [])

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

    // Convert backend data → UI items
    const libraryItems = useMemo(
        () => (data?.library ?? []).map((a) => toAlbumItem(a, goLibraryWith)),
        [data?.library, goLibraryWith],
    )

    const tagItems = useMemo(
        () => (data?.tags ?? []).map((a) => toAlbumItem(a, goLibraryWith)),
        [data?.tags, goLibraryWith],
    )

    const cameraItems = useMemo(
        () => (data?.cameras ?? []).map((a) => toAlbumItem(a, goLibraryWith)),
        [data?.cameras, goLibraryWith],
    )

    const festivalItems = useMemo(
        () => (data?.festivals ?? []).map((a) => toAlbumItem(a, goLibraryWith)),
        [data?.festivals, goLibraryWith],
    )

    const yearItems = useMemo(
        () => (data?.years ?? []).map((a) => toAlbumItem(a, goLibraryWith)),
        [data?.years, goLibraryWith],
    )

    const placeItems = useMemo(
        () => (data?.places ?? []).map((a) => toAlbumItem(a, goLibraryWith)),
        [data?.places, goLibraryWith],
    )

    // Section definitions
    const sections: SectionDef[] = useMemo(
        () =>
            [
                { id: "tags" as SectionId, icon: Tag, title: "Tags", items: tagItems, previewCount: 8 },
                { id: "cameras" as SectionId, icon: Camera, title: "Cameras", items: cameraItems, previewCount: 6 },
                { id: "festivals" as SectionId, icon: Sparkles, title: "Festivals", items: festivalItems, previewCount: 8 },
                { id: "years" as SectionId, icon: Calendar, title: "Years", items: yearItems, previewCount: 9 },
                { id: "places" as SectionId, icon: MapPin, title: "Places", items: placeItems, previewCount: 6 },
            ].filter((s) => s.items.length > 0),
        [tagItems, cameraItems, festivalItems, yearItems, placeItems],
    )

    // Detail navigation — via album-section store (must be after sections)
    const openDetail = useCallback((id: SectionId) => {
        const sec = sections.find((s) => s.id === id)
        if (sec) enterSection(id, sec.title)
    }, [sections, enterSection])

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
        <div ref={rootRef} className={cn("pb-24", returning && "animate-[fade-in-up_200ms_ease-out]")}>
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
