import { useEffect } from "react"
import type { Media } from "@/api/types"
import { mediaUrl } from "@/lib/media-url"

/**
 * Prefetches thumbnails + decoded previews around `currentIndex` so left/right
 * navigation can reveal cached images without a black flash.
 */
export function useMediaPreload(
    currentIndex: number,
    items: Media[],
    onImageReady?: (id: number) => void,
): void {
    useEffect(() => {
        let alive = true
        const indices = [
            currentIndex,
            currentIndex - 3,
            currentIndex - 2,
            currentIndex - 1,
            currentIndex + 1,
            currentIndex + 2,
            currentIndex + 3,
        ].filter((idx, pos, all) => idx >= 0 && idx < items.length && all.indexOf(idx) === pos)

        const targets = indices
            .map((idx) => items[idx])
            .filter((item) => item.media_type !== "video")

        const images = targets
            .flatMap((item) => [
                { id: item.id, src: mediaUrl.thumbnail(item.id), preview: false },
                { id: item.id, src: mediaUrl.image(item.id), preview: true },
            ])
            .map((src) => {
                const img = new Image()
                img.crossOrigin = "use-credentials"
                img.decoding = "async"
                const markReady = () => {
                    if (alive && src.preview) onImageReady?.(src.id)
                }
                img.onload = markReady
                img.src = src.src
                void img.decode?.().then(markReady).catch(() => undefined)
                return img
            })

        return () => {
            alive = false
            for (const img of images) {
                img.onload = null
                img.onerror = null
                img.src = ""
            }
        }
    }, [currentIndex, items, onImageReady])
}
