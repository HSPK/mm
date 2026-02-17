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
