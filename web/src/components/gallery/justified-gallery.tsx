import { memo, useRef, useState, useLayoutEffect, useMemo } from "react"
import { MediaTile } from "./media-tile"
import type { Media } from "@/api/types"

/** Justified gallery that fills each row completely */
export const JustifiedGallery = memo(function JustifiedGallery({
    items,
    targetHeight,
    gap,
    onSelect,
    selectionMode,
    selectedIds,
    onToggleSelect,
    onLongPress,
}: {
    items: Media[]
    targetHeight: number
    gap: number
    onSelect: (id: number) => void
    selectionMode: boolean
    selectedIds: Set<number>
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
}) {
    const containerRef = useRef<HTMLDivElement>(null)
    const [containerWidth, setContainerWidth] = useState(0)

    // Measure container width
    useLayoutEffect(() => {
        const el = containerRef.current
        if (!el) return
        const measure = () => setContainerWidth(el.clientWidth)
        measure()
        const obs = new ResizeObserver(measure)
        obs.observe(el)
        return () => obs.disconnect()
    }, [])

    // Build justified rows
    const rows = useMemo(() => {
        if (containerWidth <= 0) return []

        const result: { item: Media; width: number; height: number }[][] = []
        let currentRow: { item: Media; width: number; height: number }[] = []
        let rowWidth = 0

        for (const item of items) {
            const w = item.width && item.width > 0 ? item.width : 4
            const h = item.height && item.height > 0 ? item.height : 3
            const aspect = w / h
            const itemWidth = targetHeight * aspect

            // Check if adding this item would overflow
            const totalGaps = currentRow.length * gap
            if (currentRow.length > 0 && rowWidth + itemWidth + totalGaps > containerWidth) {
                // Finalize current row - scale to fill
                const gapsWidth = (currentRow.length - 1) * gap
                const availableWidth = containerWidth - gapsWidth
                const scale = availableWidth / (rowWidth - gap)
                const scaledRow = currentRow.map(r => ({
                    ...r,
                    width: Math.floor(r.width * scale),
                    height: Math.floor(r.height * scale),
                }))
                result.push(scaledRow)
                currentRow = []
                rowWidth = 0
            }

            currentRow.push({ item, width: itemWidth, height: targetHeight })
            rowWidth += itemWidth
        }

        // Last row - don't scale if less than 60% full (keep natural size)
        if (currentRow.length > 0) {
            const gapsWidth = (currentRow.length - 1) * gap
            const fillRatio = (rowWidth + gapsWidth) / containerWidth
            if (fillRatio > 0.6) {
                const availableWidth = containerWidth - gapsWidth
                const scale = availableWidth / rowWidth
                const scaledRow = currentRow.map(r => ({
                    ...r,
                    width: Math.floor(r.width * scale),
                    height: Math.floor(r.height * scale),
                }))
                result.push(scaledRow)
            } else {
                result.push(currentRow)
            }
        }

        return result
    }, [items, containerWidth, targetHeight, gap])

    return (
        <div ref={containerRef} className="w-full">
            {rows.map((row, rowIdx) => (
                <div
                    key={rowIdx}
                    className="flex"
                    style={{ gap, marginBottom: gap, contentVisibility: 'auto', containIntrinsicSize: `auto ${row[0]?.height ?? targetHeight}px` } as React.CSSProperties}
                >
                    {row.map(({ item, width, height }) => (
                        <MediaTile
                            key={item.id}
                            item={item}
                            style={{ width, height }}
                            className="rounded-sm flex-shrink-0"
                            onSelect={onSelect}
                            selectionMode={selectionMode}
                            selected={selectedIds.has(item.id)}
                            onToggleSelect={onToggleSelect}
                            onLongPress={onLongPress}
                        />
                    ))}
                </div>
            ))}
        </div>
    )
})
