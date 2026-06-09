import { useMemo } from "react"
import { ImageOff } from "lucide-react"
import { AlbumCard } from "@/components/album-card"
import { EmptyState } from "@/components/ui/empty-state"
import type { SectionDef } from "@/api/types"
import { useAlbumSectionStore } from "@/stores/album-section"

interface SectionDetailViewProps {
    section: SectionDef
}

export function SectionDetailView({ section }: SectionDetailViewProps) {
    const search = useAlbumSectionStore((s) => s.search)
    const setSearch = useAlbumSectionStore((s) => s.setSearch)

    const filtered = useMemo(() => {
        if (!search.trim()) return section.items
        const q = search.toLowerCase()
        return section.items.filter((item) =>
            item.searchText.toLowerCase().includes(q) ||
            item.title.toLowerCase().includes(q),
        )
    }, [section.items, search])

    return (
        <div className="px-2 sm:px-4 pt-2 pb-24">
            {filtered.length === 0 ? (
                <EmptyState
                    icon={ImageOff}
                    title={search ? "No matching albums" : "No albums yet"}
                    description={search ? "Try adjusting your search." : undefined}
                    action={search ? { label: "Clear search", onClick: () => setSearch("") } : undefined}
                />
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
