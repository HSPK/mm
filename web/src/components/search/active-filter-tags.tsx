import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import type { FilterTag, FilterTagColor } from "@/hooks/use-filter-tag-list"

const colorClasses: Record<FilterTagColor, string> = {
    primary: "bg-primary/20 text-primary border-primary/30",
    destructive: "bg-destructive/20 text-destructive border-destructive/30",
    amber: "bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/30",
    emerald: "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
}

function colorFor(color?: FilterTagColor): string {
    return color ? colorClasses[color] : "bg-secondary text-foreground/70 border-border/60"
}

export function ActiveFilterTags({ tags }: { tags: FilterTag[] }) {
    if (tags.length === 0) return null
    return (
        <div className="flex flex-wrap items-center gap-1.5 mt-1.5 px-0.5">
            {tags.map((tag) => (
                <span
                    key={tag.key}
                    className={cn(
                        "inline-flex items-center gap-1 py-[3px] rounded-full text-[10px] font-medium border backdrop-blur-md shadow-sm transition-colors",
                        tag.removable ? "pl-2 pr-1" : "px-2",
                        colorFor(tag.color),
                    )}
                >
                    <span className="max-w-[8rem] truncate">{tag.label}</span>
                    {tag.removable && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation()
                                tag.onRemove()
                            }}
                            className="flex items-center justify-center h-3.5 w-3.5 rounded-full hover:bg-black/15 dark:hover:bg-white/15 transition-colors"
                        >
                            <X className="h-2.5 w-2.5" />
                        </button>
                    )}
                </span>
            ))}
        </div>
    )
}
