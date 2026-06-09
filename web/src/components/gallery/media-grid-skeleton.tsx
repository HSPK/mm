import { Skeleton } from "@/components/ui/skeleton"

/** Renders a row of justified-style placeholder tiles for the initial load. */
export function MediaGridSkeleton({ rows = 3, perRow = 5 }: { rows?: number; perRow?: number }) {
    return (
        <div className="space-y-1.5">
            {Array.from({ length: rows }).map((_, r) => (
                <div key={r} className="flex gap-1.5">
                    {Array.from({ length: perRow }).map((_, c) => (
                        <Skeleton
                            key={c}
                            className="flex-1 aspect-[4/3] rounded-sm"
                            style={{
                                flexGrow: 1 + (c + r) % 3,
                                animationDelay: `${(r * perRow + c) * 40}ms`,
                            }}
                        />
                    ))}
                </div>
            ))}
        </div>
    )
}
