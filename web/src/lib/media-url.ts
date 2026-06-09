import { config } from "./config"

export type ThumbnailSize = "sm" | "md" | "lg" | "xl"

export interface MediaUrlBuilder {
    file(id: number): string
    preview(id: number): string
    thumbnail(id: number, size?: ThumbnailSize): string
    image(id: number): string
}

export function createMediaUrlBuilder(apiBaseUrl: string): MediaUrlBuilder {
    const file = (id: number) => `${apiBaseUrl}/media/${id}/file`
    const preview = (id: number) => `${apiBaseUrl}/media/${id}/preview`
    const thumbnail = (id: number, size?: ThumbnailSize) =>
        `${apiBaseUrl}/media/${id}/thumbnail${size ? `?size=${size}` : ""}`
    return {
        file,
        preview,
        thumbnail,
        // Originals still go through the cached preview endpoint for fast,
        // consistent opening across formats. Callers that need the raw file
        // should use `file(id)` explicitly.
        image: preview,
    }
}

export const mediaUrl = createMediaUrlBuilder(config.apiBaseUrl)
