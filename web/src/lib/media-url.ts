// ─── Media URL helpers ────────────────────────────────────

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api"

/** Extensions browsers can't render natively — use server-converted preview */
export const RAW_EXTENSIONS = new Set([
    ".heic", ".heif",
    ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw",
])

/** Raw uppercase extensions for overlay badge display */
export const RAW_EXTS_UPPER = new Set([
    "CR2", "CR3", "ARW", "NEF", "DNG", "RAF", "ORF", "RW2", "PEF", "SRW", "NRW", "3FR", "IIQ", "ERF", "MEF", "MOS",
])

/** Image extensions that browsers can reliably render from the original file. */
export const NATIVE_IMAGE_EXTENSIONS = new Set([
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif",
])

export function getMediaSrc(id: number) {
    return `${API_BASE}/media/${id}/file`
}

export function getPreviewSrc(id: number) {
    return `${API_BASE}/media/${id}/preview`
}

export function getThumbnailSrc(id: number, size?: "sm" | "md" | "lg" | "xl") {
    return `${API_BASE}/media/${id}/thumbnail${size ? `?size=${size}` : ""}`
}

/** Display images through the cached preview endpoint for fast, consistent opening. */
export function getImageSrc(item: { id: number; extension: string }) {
    return getPreviewSrc(item.id)
}

export function canDisplayOriginalImage(item: { extension: string }) {
    return NATIVE_IMAGE_EXTENSIONS.has(item.extension.toLowerCase())
}
