import { lazy, Suspense } from "react"
import type { Media } from "@/api/types"
import { Spinner } from "@/components/ui/spinner"

const LazyVideoStage = lazy(() => import("./video-stage-impl"))

interface VideoStageProps {
    item: Media
    onLoaded: (id: number) => void
    onError: (id: number, message: string) => void
}

/**
 * Lazy wrapper for the vidstack-based VideoStage. Vidstack + its theme adds
 * ~300 kB to the bundle; this keeps it out of the initial chunk so users who
 * only browse photos don't pay the cost.
 */
export function VideoStage(props: VideoStageProps) {
    return (
        <Suspense fallback={
            <div className="absolute inset-0 flex items-center justify-center">
                <Spinner size="md" className="text-white/35" />
            </div>
        }>
            <LazyVideoStage {...props} />
        </Suspense>
    )
}
