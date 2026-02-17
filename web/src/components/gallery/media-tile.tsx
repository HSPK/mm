import { memo, useRef, useCallback } from "react"
import { AuthImage } from "@/components/auth-image"
import { cn } from "@/lib/utils"
import type { Media } from "@/api/types"

// ─── Shared media tile with long-press selection ──────────

const LONG_PRESS_MS = 400

export const MediaTile = memo(function MediaTile({
    item,
    onSelect,
    selectionMode,
    selected,
    onToggleSelect,
    onLongPress,
    className,
    style,
}: {
    item: Media
    onSelect: (id: number) => void
    selectionMode: boolean
    selected: boolean
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
    className?: string
    style?: React.CSSProperties
}) {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const didLongPress = useRef(false)

    const startPress = useCallback(() => {
        didLongPress.current = false
        timerRef.current = setTimeout(() => {
            didLongPress.current = true
            navigator?.vibrate?.(30)
            onLongPress(item.id)
        }, LONG_PRESS_MS)
    }, [item.id, onLongPress])

    const cancelPress = useCallback(() => {
        if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null }
    }, [])

    const handleClick = useCallback(() => {
        if (didLongPress.current) return
        if (selectionMode) {
            onToggleSelect(item.id)
        } else {
            onSelect(item.id)
        }
    }, [selectionMode, item.id, onSelect, onToggleSelect])

    return (
        <div
            className={cn("group relative overflow-hidden bg-muted cursor-pointer", className)}
            style={style}
            onClick={handleClick}
            onPointerDown={startPress}
            onPointerUp={cancelPress}
            onPointerLeave={cancelPress}
            onContextMenu={(e) => { e.preventDefault(); onLongPress(item.id) }}
        >
            <AuthImage
                apiSrc={`/media/${item.id}/thumbnail`}
                alt=""
                loading="lazy"
                className={cn(
                    "h-full w-full object-cover transition-all duration-200 will-change-transform",
                    selectionMode && selected && "scale-[0.95] rounded-lg",
                    selectionMode && !selected && "scale-100",
                    !selectionMode && "group-hover:scale-[1.03]",
                )}
            />
            {!selectionMode && <Overlay item={item} />}

            {/* Selection indicator */}
            {selectionMode && (
                <div className={cn(
                    "absolute top-[6%] left-[6%] z-10 h-5 w-5 rounded-full flex items-center justify-center transition-all duration-150",
                    selected
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "border-2 border-white/60 bg-black/20"
                )}>
                    {selected && (
                        <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                        </svg>
                    )}
                </div>
            )}
        </div>
    )
})

// ─── Overlay (hover info + badges) ────────────────────────

import { Film } from "lucide-react"
import { StarRating } from "@/components/ui/star-rating"
import { fmtDateShort, fmtDuration } from "@/lib/format"
import { RAW_EXTS_UPPER } from "@/lib/media-url"

const Overlay = memo(function Overlay({ item }: { item: Media }) {
    const ext = item.extension?.replace(/^\./, "").toUpperCase() || ""
    const isRaw = RAW_EXTS_UPPER.has(ext)
    return (
        <>
            {/* Single hover overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none will-change-[opacity]">
                <div className="absolute bottom-0 left-0 right-0 p-2 flex items-end justify-between gap-2">
                    <div className="flex flex-col gap-0.5 min-w-0">
                        {item.date_taken && (
                            <span className="text-[11px] text-white/90 font-medium">
                                {fmtDateShort(item.date_taken)}
                            </span>
                        )}
                        {item.camera_model && (
                            <span className="text-[10px] text-white/50 truncate">
                                {item.camera_model}
                            </span>
                        )}
                    </div>
                    {(item.rating ?? 0) > 0 && (
                        <StarRating value={item.rating} size={10} />
                    )}
                </div>
            </div>

            {/* Always-visible badges */}
            {isRaw && (
                <div className="absolute top-1.5 right-1.5">
                    <span className="inline-flex items-center rounded bg-black/50 px-1.5 py-0.5 text-[9px] text-white/70 font-bold tracking-wider">
                        RAW
                    </span>
                </div>
            )}
            {item.media_type === "video" && (
                <div className="absolute top-1.5 left-1.5">
                    <span className="inline-flex items-center gap-0.5 rounded bg-black/50 px-1.5 py-0.5 text-[10px] text-white font-medium">
                        <Film className="h-2.5 w-2.5" />
                        {fmtDuration(item.duration) ?? "Video"}
                    </span>
                </div>
            )}
        </>
    )
})

// ─── Square tile wrapper ──────────────────────────────────

export const SquareTile = memo(function SquareTile({
    item,
    onSelect,
    selectionMode,
    selected,
    onToggleSelect,
    onLongPress,
}: {
    item: Media
    onSelect: (id: number) => void
    selectionMode: boolean
    selected: boolean
    onToggleSelect: (id: number) => void
    onLongPress: (id: number) => void
}) {
    return (
        <MediaTile
            item={item}
            className="aspect-square rounded-md"
            onSelect={onSelect}
            selectionMode={selectionMode}
            selected={selected}
            onToggleSelect={onToggleSelect}
            onLongPress={onLongPress}
        />
    )
})
