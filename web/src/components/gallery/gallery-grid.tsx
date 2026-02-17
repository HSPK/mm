import { memo } from "react"
import { SquareTile } from "./media-tile"
import { JustifiedGallery } from "./justified-gallery"
import type { Media } from "@/api/types"

export interface GalleryGridProps {
    items: Media[]
    thumbSize: number
    viewMode: "justified" | "grid"
    onSelect: (id: number) => void
    selectionMode: boolean
    selectedIds: Set<number>
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
}

export const GalleryGrid = memo(function GalleryGrid({
    items, thumbSize, viewMode, onSelect,
    selectionMode, selectedIds, onToggleSelect, onLongPress,
}: GalleryGridProps) {
    if (viewMode === "grid") {
        return (
            <div
                className="grid gap-1 transition-all"
                style={{
                    gridTemplateColumns: `repeat(auto-fill, minmax(${thumbSize}px, 1fr))`,
                }}
            >
                {items.map((item) => (
                    <SquareTile
                        key={item.id} item={item} onSelect={onSelect}
                        selectionMode={selectionMode}
                        selected={selectedIds.has(item.id)}
                        onToggleSelect={onToggleSelect}
                        onLongPress={onLongPress}
                    />
                ))}
            </div>
        )
    }

    return (
        <JustifiedGallery
            items={items}
            targetHeight={thumbSize}
            gap={4}
            onSelect={onSelect}
            selectionMode={selectionMode}
            selectedIds={selectedIds}
            onToggleSelect={onToggleSelect}
            onLongPress={onLongPress}
        />
    )
})
