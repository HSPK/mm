import { useEffect } from "react"
import type { Media } from "@/api/types"
import { mediaUrl } from "@/lib/media-url"

/**
 * Prefetches thumbnails + images for the items immediately around
 * `currentIndex` so left/right navigation feels instant.
 */
export function useMediaPreload(currentIndex: number, items: Media[]): void {
    useEffect(() => {
        const neighbours = [currentIndex - 2, currentIndex - 1, currentIndex + 1, currentIndex + 2]
            .filter((idx) => idx >= 0 && idx < items.length)
            .map((idx) => items[idx])
            .filter((item) => item.media_type !== "video")

        const images = neighbours
            .flatMap((item) => [mediaUrl.thumbnail(item.id), mediaUrl.image(item.id)])
            .map((src) => {
                const img = new Image()
                img.crossOrigin = "use-credentials"
                img.src = src
                return img
            })

        return () => {
            for (const img of images) img.src = ""
        }
    }, [currentIndex, items])
}
