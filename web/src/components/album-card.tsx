import { memo } from "react"
import { AuthImage } from "@/components/auth-image"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface AlbumCardProps {
    icon: LucideIcon
    title: string
    subtitle?: string
    count?: number
    coverId?: number | null
    onClick: () => void
    color?: string
}

/**
 * Apple Photos-style album card.
 *  - Square thumbnail with subtle elevation (no border)
 *  - Title + count rendered BELOW the image (not overlaid) so it reads cleanly
 *    in both light and dark themes
 *  - Press affordance: thumbnail darkens + scales down 2%
 */
export const AlbumCard = memo(function AlbumCard({
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
            type="button"
            onClick={onClick}
            aria-label={count != null ? `${title}, ${count.toLocaleString()} items` : title}
            className={cn(
                "group block w-full text-left",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-2xl",
            )}
        >
            <div
                className={cn(
                    "aspect-square relative overflow-hidden rounded-2xl bg-secondary/40 elevation-1",
                    "transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
                    "group-hover:elevation-2 group-active:scale-[0.98]",
                )}
            >
                {coverId ? (
                    <AuthImage
                        apiSrc={`/media/${coverId}/thumbnail?size=lg`}
                        alt=""
                        loading="lazy"
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                        fallback={<IconFallback Icon={Icon} color={color} />}
                    />
                ) : (
                    <IconFallback Icon={Icon} color={color} />
                )}
            </div>
            <div className="mt-2 px-1">
                <h3 className="text-[15px] font-semibold text-foreground truncate leading-tight">
                    {title}
                </h3>
                <div className="flex items-baseline gap-1.5 mt-0.5">
                    {count != null && (
                        <span className="text-[13px] text-muted-foreground/80 tabular-nums">
                            {count.toLocaleString()}
                        </span>
                    )}
                    {subtitle && count == null && (
                        <span className="text-[13px] text-muted-foreground/80 truncate">
                            {subtitle}
                        </span>
                    )}
                </div>
            </div>
        </button>
    )
})

function IconFallback({ Icon, color }: { Icon: LucideIcon; color?: string }) {
    return (
        <div className={cn("h-full w-full flex items-center justify-center", color || "bg-secondary/50")}>
            <Icon className="h-12 w-12 text-muted-foreground/30" strokeWidth={1.5} aria-hidden />
        </div>
    )
}
