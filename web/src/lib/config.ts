// Central runtime configuration. Reads from import.meta.env exactly once so
// the rest of the app never touches Vite env directly.

export interface AppConfig {
    apiBaseUrl: string
    tokenStorageKey: string
    tokenCookieName: string
    viewPrefs: {
        viewModeKey: string
        dateGroupModeKey: string
        thumbSizeKey: string
        themeKey: string
    }
    thumbSize: {
        min: number
        max: number
        default: number
    }
}

function readEnv(key: string, fallback: string): string {
    const value = import.meta.env?.[key]
    return typeof value === "string" && value.length > 0 ? value : fallback
}

export const config: AppConfig = {
    apiBaseUrl: readEnv("VITE_API_BASE_URL", "/api"),
    tokenStorageKey: "mm_token",
    tokenCookieName: "mm_token",
    viewPrefs: {
        viewModeKey: "mm-view-mode",
        dateGroupModeKey: "mm-date-group-mode",
        thumbSizeKey: "mm-thumb-size",
        themeKey: "mm-theme",
    },
    thumbSize: {
        min: 80,
        max: 400,
        default: 220,
    },
}

export function clampThumbSize(value: number): number {
    return Math.min(config.thumbSize.max, Math.max(config.thumbSize.min, value))
}
