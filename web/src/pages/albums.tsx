import { useCallback, useEffect, useMemo, useRef } from "react"
import { AlertTriangle, ChevronRight, Images, type LucideIcon } from "lucide-react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { AlbumCard } from "@/components/album-card"
import { SectionDetailView } from "@/components/album/section-detail-view"
import { EmptyState } from "@/components/ui/empty-state"
import { Spinner } from "@/components/ui/spinner"
import { useSmartAlbums } from "@/hooks/use-smart-albums"
import { useAlbumSectionStore } from "@/stores/album-section"
import { useMediaQueryStore } from "@/stores/media-query"
import { buildAlbumItems } from "@/lib/albums"
import { defaultFilters, type Filters } from "@/lib/filter-types"
import type { SectionId } from "@/api/types"

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
        <div className="flex items-end justify-between mb-3 px-1">
            <div className="flex items-baseline gap-2.5">
                <Icon className="h-[18px] w-[18px] text-muted-foreground/60 self-center" strokeWidth={2} />
                <h2 className="text-[22px] font-bold tracking-tight text-foreground">
                    {title}
                </h2>
                {count != null && (
                    <span className="text-[15px] text-muted-foreground/60 font-normal tabular-nums">
                        {count.toLocaleString()}
                    </span>
                )}
            </div>
            {onSeeAll && (
                <button
                    onClick={onSeeAll}
                    className="flex items-center gap-0.5 text-[15px] text-primary hover:opacity-80 transition-opacity font-normal"
                >
                    See All
                    <ChevronRight className="h-[18px] w-[18px] stroke-[2.3]" />
                </button>
            )}
        </div>
    )
}

export default function AlbumsPage() {
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const { setFilters, setActiveLabel } = useMediaQueryStore()
    const { sectionId, enter: enterSection, exit: exitSection } = useAlbumSectionStore()

    const { data, loading, error, retry } = useSmartAlbums()
    const rootRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const scrollParent = rootRef.current?.parentElement
        if (scrollParent) {
            scrollParent.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior })
        }
    }, [sectionId])

    const goLibraryWith = useCallback(
        (updates: Record<string, unknown>, label?: string) => {
            setFilters({ ...defaultFilters, ...updates } as Partial<Filters>)
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

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full pb-24">
                <Spinner size="md" className="text-muted-foreground/40" />
            </div>
        )
    }

    if (error) {
        return (
            <div ref={rootRef} className="h-full">
                <EmptyState
                    icon={AlertTriangle}
                    title={error}
                    description="Check the server connection and try loading the album sections again."
                    action={{ label: "Retry", onClick: retry }}
                />
            </div>
        )
    }

    if (activeDetail) {
        return (
            <div ref={rootRef} className="animate-[slide-in-right_250ms_ease-out]">
                <SectionDetailView section={activeDetail} />
            </div>
        )
    }

    return (
        <div ref={rootRef} className="pb-24">
            <div className="px-4 pt-1 space-y-10">
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
