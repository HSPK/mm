import { config } from "./config"

export function resolveAuthImageSrc(apiSrc: string | null) {
    if (!apiSrc || !apiSrc.startsWith("/")) return apiSrc
    if (typeof window === "undefined") return apiSrc
    const apiBase = new URL(config.apiBaseUrl, window.location.href)
    if (apiSrc === "/api" || apiSrc.startsWith("/api/")) {
        return apiBase.origin === window.location.origin
            ? apiSrc
            : `${apiBase.origin}${apiSrc}`
    }
    return `${config.apiBaseUrl.replace(/\/$/, "")}${apiSrc}`
}
