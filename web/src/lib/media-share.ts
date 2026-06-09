import { config } from "@/lib/config"
import { mediaUrl } from "@/lib/media-url"
import { toast } from "@/stores/toast"

interface ShareableMedia {
    id: number
    filename: string
}

/**
 * Share the absolute URL of a media file using the Web Share API. Falls back
 * to copying the URL to the clipboard if Share is unavailable or fails.
 */
export async function shareMedia(item: ShareableMedia): Promise<void> {
    const url = absoluteMediaUrl(item.id)
    const payload = { title: item.filename, url }

    if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
        try {
            await navigator.share(payload)
            return
        } catch (err) {
            // AbortError = user cancelled; don't surface a notification for that.
            if ((err as { name?: string }).name === "AbortError") return
            // Fall through to clipboard fallback.
        }
    }

    await copyToClipboard(url)
    toast.success("Link copied to clipboard")
}

/** Opens the original (full-quality) file in a new browser tab. */
export function openOriginal(item: ShareableMedia): void {
    if (typeof window === "undefined") return
    window.open(absoluteMediaUrl(item.id), "_blank", "noopener,noreferrer")
}

function absoluteMediaUrl(id: number): string {
    const path = mediaUrl.file(id)
    if (/^https?:\/\//.test(path)) return path
    if (typeof window === "undefined") return path
    if (path.startsWith("/")) return `${window.location.origin}${path}`
    if (config.apiBaseUrl.startsWith("http")) return `${config.apiBaseUrl}${path}`
    return `${window.location.origin}/${path}`
}

async function copyToClipboard(text: string): Promise<void> {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        try {
            await navigator.clipboard.writeText(text)
            return
        } catch {
            // fall through
        }
    }
    // Last-ditch fallback for non-secure contexts.
    if (typeof document === "undefined") return
    const textarea = document.createElement("textarea")
    textarea.value = text
    textarea.style.position = "fixed"
    textarea.style.opacity = "0"
    document.body.appendChild(textarea)
    textarea.select()
    try { document.execCommand("copy") } catch { /* noop */ }
    document.body.removeChild(textarea)
}
